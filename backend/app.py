from flask import Flask, request, json
import os
import subprocess
from flask_socketio import SocketIO, emit
import yaml

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*")
REPO_DIRECTORY = "/tmp/repos"


@app.route("/")
def api_root():
    return "Server is running and receiving events!"


@app.route("/events", methods=["POST"])
def api_events():
    try:
        event_type = request.headers.get("X-GitHub-Event", "unknown")
        print(f"📥 Event type received: {event_type}")
        event = request.json

        if not event:
            return json.dumps({"message": "No event data received"}), 400

        repo = event.get("repository", {})
        repo_title = repo.get("full_name")
        repo_url = repo.get("clone_url")
        local_repo_path = os.path.join(REPO_DIRECTORY, repo_title.replace("/", "_"))

        # Skip builds for internal system repository
        if repo_title == "AadamYB/final-year-project":
            print(f"⚙️ Internal repo push detected for {repo_title} — skipping.")
            return json.dumps({"status": "ignored"}), 200

        if event_type == "pull_request":
            pr = event["pull_request"]
            pr_branch = pr.get("head", {}).get("ref")
            pr_number = pr.get("number")
            print(f"Received PR#{pr_number} for branch {pr_branch} in {repo_title}.")

            # First we clone the repository if it does not already exist, if so then pull changes
            clone_or_pull(repo_url, local_repo_path)

            # Then checkout the PR branch
            checkout_branch(local_repo_path, pr_branch)

            # Load .ci.yml if it exists
            ci_config = load_ci_config(local_repo_path)

            # Conditionally execute steps

            # We want to make sure that the code passes the formatting before building the project
            if ci_config.get("lint", True):
                lint_project(local_repo_path)

            if ci_config.get("format", True):
                format_project(local_repo_path)

            # Trigger the buiild and testing of the project
            if ci_config.get("build", True):
                build_project(local_repo_path)

            if ci_config.get("test", True):
                run_tests(local_repo_path)

            # If users add their own custom commands
            for cmd in ci_config.get("run_commands", []):
                if isinstance(cmd, str):
                    print(f"🏃 Running custom command: {cmd}")
                    subprocess.run(cmd, shell=True, check=True, cwd=local_repo_path)

            return json.dumps({"status": "PR processed"}), 200

        elif event_type == "push":
            push_branch = event.get("ref", "").split("/")[-1]
            print(f"Received push to {push_branch} in {repo_title}.")

            # First we clone the repository if it does not already exist, if so then pull changes
            clone_or_pull(repo_url, local_repo_path)

            # Then checkout the PR branch
            checkout_branch(local_repo_path, pr_branch)

            # Load .ci.yml if it exists
            ci_config = load_ci_config(local_repo_path)

            # Conditionally execute steps

            # We want to make sure that the code passes the formatting before building the project
            if ci_config.get("lint", True):
                lint_project(local_repo_path)

            if ci_config.get("format", True):
                format_project(local_repo_path)

            # Trigger the buiild and testing of the project
            if ci_config.get("build", True):
                build_project(local_repo_path)

            if ci_config.get("test", True):
                run_tests(local_repo_path)

            # If users add their own custom commands
            for cmd in ci_config.get("run_commands", []):
                if isinstance(cmd, str):
                    print(f"🏃 Running custom command: {cmd}")
                    subprocess.run(cmd, shell=True, check=True, cwd=local_repo_path)

            return json.dumps({"status": "Push processed"}), 200

        print("⚠️ Ignoring unsupported event type.")
        return json.dumps({"message": f"Ignored event type: {event_type}"}), 200

    except Exception as e:
        print(f"❌ Pipeline failed: {e}")
        return json.dumps({"error": str(e)}), 500


@socketio.on('connect')
def handle_connect():
    print("🛜 WebSocket client connected ✅")


@socketio.on('start-debug')
def start_debug_session(data):
    repo = data.get("repo")
    print(f"> [DEBUG] 🐞STARTING LIVE DEBUGGING SESSION🪲 for {repo}")
    emit("log", {"log": f"> [DEBUG] 🐞STARTING LIVE DEBUGGING SESSION🪲 for {repo}"})
    emit("log", {"log": f"> [DEBUG] LOGS PAUSED ⏸️"})


@socketio.on('disconnect')
def handle_disconnect():
    print("🛜 WebSocket client disconnected ❌")

# ---------------------------------------------------------------------------------------------
# ------------------------------------ Utility Functions --------------------------------------
# ---------------------------------------------------------------------------------------------


def clone_or_pull(repo_url, local_repo_path):
    """Clones a GitHub repository to a local directory and/or
    Pulls latest changes from the repository"""
    if not os.path.exists(local_repo_path):
        print(f"🔄 Cloning {repo_url}")
        subprocess.run(["git", "clone", repo_url, local_repo_path], check=True)
    else:
        print(f"🔁 Pulling latest changes in {local_repo_path}")
        subprocess.run(["git", "-C", local_repo_path, "pull"], check=True)


def checkout_branch(local_repo_path, branch_name):
    """Checkouts the correct branch for the Pull Request"""
    print(f"🌿 Checking out branch: {branch_name}")
    subprocess.run(["git", "-C", local_repo_path, "fetch", "origin"], check=True)
    subprocess.run(["git", "-C", local_repo_path, "checkout", branch_name], check=True)


def lint_project(local_repo_path):
    """Runs pylint inside Docker to ensure code quality ~ SWAG"""
    print("🔍 Running pylint checks...")

    pylint_config_path = "/app/.pylintrc"
    target_file = "/app/app/main.py"

    # Ensure the file exists inside the local repo (host side) before Docker call
    if not os.path.exists(os.path.join(local_repo_path, "app", "main.py")):
        raise Exception("❌ ERROR! Target file app/main.py does not exist!")

    if not os.path.exists(os.path.join(local_repo_path, ".pylintrc")):
        raise Exception("❌ ERROR! .pylintrc config file not found in the project root!")

    try:
        result = subprocess.run(
            [
                "docker",
                "run",
                "--rm",
                "-v",
                f"{local_repo_path}:/app",
                "project-image",
                "pylint",
                "--rcfile",
                pylint_config_path,
                target_file,
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=True,
        )
        print(result.stdout)

        # Check score
        if "Your code has been rated at" in result.stdout:
            score_line = next(
                line
                for line in result.stdout.splitlines()
                if "Your code has been rated at" in line
            )
            score = float(score_line.split(" ")[6].split("/")[0])
            print(f"📊 Pylint score: {score}/10")
            if score < 8.0:
                raise Exception(f"❌ ERROR - Lint failed! Score: {score}/10")

    except subprocess.CalledProcessError as e:
        print("❌ ERROR - Pylint returned an error.")
        print("STDOUT:\n", e.stdout)
        print("STDERR:\n", e.stderr)

        if "No module named" in e.stderr or "load-plugins" in e.stderr:
            print("💡 HINT: Check if all plugins in `.pylintrc` are installed.")
            print("🔧 You can fix this by adding:")
            print("    pylint[docparams,typing,code_style]")
            print("  to your `requirements.txt` and rebuilding the Docker image.")

        raise Exception("❌ ERROR! Linting failed due to error above.")


def format_project(local_repo_path):
    """Formats code using Black formatter inside the Docker container ~SWAG"""
    print("💅 Running black formatter...")

    try:
        subprocess.run(
            [
                "docker",
                "run",
                "--rm",
                "-v",
                f"{local_repo_path}:/app",
                "project-image",
                "black",
                "--check",
                "app",
                "tests",
            ],
            check=True,
        )
        print("✅ Code is already formatted.")

    except subprocess.CalledProcessError as e:
        raise Exception("ERROR! Black formatting required!")


def build_project(local_repo_path):
    """Builds the project inside a Docker container"""
    print(f"🏗️ Building project in {local_repo_path}")
    dockerfile_path = os.path.join(local_repo_path, "Dockerfile")
    if not os.path.exists(dockerfile_path):
        raise Exception(f"❌ ERROR! No Dockerfile found at {dockerfile_path}")

    subprocess.run(
        ["docker", "build", "-t", "project-image", local_repo_path], check=True
    )
    print("✅ Build completed.")


def run_tests(local_repo_path):
    """Runs the test scripts for the user project"""
    print(f"🧪 Running tests in {local_repo_path}")

    result = subprocess.run(
        [
            "docker",
            "run",
            "--rm",
            "-v",
            f"{local_repo_path}:/app",
            "-w",
            "/app",
            "project-image",
            "pytest",
            "tests",
            "--tb=short",
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )

    print("STDOUT:\n", result.stdout or "[no output]")
    print("STDERR:\n", result.stderr or "[no errors]")

    concat_output = (result.stdout or "") + (result.stderr or "")
    if "collected 0 items" in concat_output:
        # Check if __init__.py exists in tests directory
        test_init = os.path.join(local_repo_path, "tests", "__init__.py")
        if not os.path.exists(test_init):
            print("⚠️ WARNING: No tests were discovered.")
            print("📂 Make sure your `tests/` directory has an `__init__.py` file.")
        else:
            print(
                "⚠️ CAUTION! No tests discovered, but `__init__.py` exists. Check that your test files start with `test_` and contain functions starting with `test_`."
            )
        raise Exception("❌ ERROR! No tests discovered.")

    if result.returncode != 0:
        raise Exception(f"❌ Tests failed!\n{result.stdout or result.stderr}")

    print("✅ All tests passed!")

def load_ci_config(local_repo_path):
    """ This is for the  configuration page where users can update their ci pipline steps """
    ci_config_path = os.path.join(local_repo_path, ".ci.yml")

    if not os.path.exists(ci_config_path):
        print("⚠️ CAUTION! No .ci.yml found, using default config.")
        return {
            "lint": True,
            "format": True,
            "build": True,
            "test": True,
            "run_commands": []
        }

    try:
        with open(ci_config_path, "r") as f:
            config = yaml.safe_load(f)
            print(f"🛠️ Loaded CI config: {config}")
            return {
                "lint": config.get("lint", True),
                "format": config.get("format", True),
                "build": config.get("build", True),
                "test": config.get("test", True),
                "run_commands": config.get("run_commands", [])
            }
    except Exception as e:
        print(f"❌ ERROR! Failed to load .ci.yml: {e}")
        raise

# ------------------------------------------------------------

if __name__ == "__main__":
    os.makedirs(REPO_DIRECTORY, exist_ok=True)
    socketio.run(app, debug=True, host="0.0.0.0", port=5000)
