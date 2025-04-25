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
        log(f"📥 Event type received: {event_type}")
        event = request.json

        if not event:
            return json.dumps({"message": "No event data received"}), 400

        repo = event.get("repository", {})
        repo_title = repo.get("full_name")
        repo_url = repo.get("clone_url")
        local_repo_path = os.path.join(REPO_DIRECTORY, repo_title.replace("/", "_"))

        # Skip builds for internal system repository
        if repo_title == "AadamYB/final-year-project":
            log(f"⚙️ Internal repo push detected for {repo_title} — skipping.")
            return json.dumps({"status": "ignored"}), 200

        if event_type == "pull_request":
            pr = event["pull_request"]
            pr_branch = pr.get("head", {}).get("ref")
            pr_number = pr.get("number")
            log(f"Received PR#{pr_number} for branch {pr_branch} in {repo_title}.")

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
                    log(f"🏃 Running custom command: {cmd}")
                    subprocess.run(cmd, shell=True, check=True, cwd=local_repo_path)

            return json.dumps({"status": "PR processed"}), 200

        elif event_type == "push":
            push_branch = event.get("ref", "").split("/")[-1]
            log(f"Received push to {push_branch} in {repo_title}.")

            # First we clone the repository if it does not already exist, if so then pull changes
            clone_or_pull(repo_url, local_repo_path)

            # Then checkout the PR branch
            checkout_branch(local_repo_path, push_branch)

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
                    log(f"🏃 Running custom command: {cmd}")
                    subprocess.run(cmd, shell=True, check=True, cwd=local_repo_path)

            return json.dumps({"status": "Push processed"}), 200

        log("⚠️ Ignoring unsupported event type.")
        return json.dumps({"message": f"Ignored event type: {event_type}"}), 200

    except Exception as e:
        log(f"❌ Pipeline failed: {e}")
        return json.dumps({"error": str(e)}), 500


@socketio.on('connect')
def handle_connect():
    log("🛜 WebSocket client connected ✅")


@socketio.on('start-debug')
def start_debug_session(data):
    repo = data.get("repo")
    log(f"[DEBUG] 🐞STARTING LIVE DEBUGGING SESSION🪲 for {repo}")
    log("[DEBUG] LOGS PAUSED ⏸️")


@socketio.on('disconnect')
def handle_disconnect():
    log("🛜 WebSocket client disconnected ❌")

# ---------------------------------------------------------------------------------------------
# ------------------------------------ Utility Functions --------------------------------------
# ---------------------------------------------------------------------------------------------

def log(message, tag=None):
    """ Utility function that prints and emits the string message """
    if tag:
        message = f"[{tag.upper()}] {message}"
    print(message)
    socketio.emit('log', {'log': message})


def clone_or_pull(repo_url, local_repo_path):
    """ Clones a GitHub repository to a local directory or
        Pulls latest changes from the repository """
    if not os.path.exists(local_repo_path):
        log(f"🔄 Cloning {repo_url}")
        cmd = f"git clone {repo_url} {local_repo_path}"
        run_command_with_stream_output(cmd, tag="clone")
    else:
        log(f"🔁 Pulling latest changes in {local_repo_path}")
        cmd = f"git -C {local_repo_path} pull"
        run_command_with_stream_output(cmd, tag="pull")


def checkout_branch(local_repo_path, branch_name):
    """Checkouts the correct branch for the Pull Request"""
    log(f"🌿 Checking out branch: {branch_name}")
    # fetch latest branches
    cmd_fetch = f"git -C {local_repo_path} fetch origin"
    run_command_with_stream_output(cmd_fetch, tag="checkout")

    # checkout to the correct branch
    cmd_checkout = f"git -C {local_repo_path} checkout {branch_name}"
    run_command_with_stream_output(cmd_checkout, tag="checkout")


def lint_project(local_repo_path):
    """Runs pylint inside Docker to ensure code quality, streaming output and checking scores."""
    log("🔍 Running pylint checks...", tag="lint")

    pylint_config_path = "/app/.pylintrc"
    target_file = "/app/app/main.py"

    # Ensure the files exist inside the local repo (host side - Ec2 instance side where we clone the target repo)
    if not os.path.exists(os.path.join(local_repo_path, "app", "main.py")):
        raise Exception("❌ ERROR! Target file app/main.py does not exist!")

    if not os.path.exists(os.path.join(local_repo_path, ".pylintrc")):
        raise Exception("❌ ERROR! .pylintrc config file not found in the project root!")

    cmd = (
        f"docker run --rm -v {local_repo_path}:/app "
        f"project-image pylint --rcfile {pylint_config_path} {target_file}"
    )

    log(f"🚀 Running command: {cmd}", tag="lint")

    process = subprocess.Popen(
        cmd,
        shell=True,
        cwd=local_repo_path,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )

    output_lines = []

    # Stream the linting output line-by-line
    for line in process.stdout:
        line = line.strip()
        if line:
            output_lines.append(line)
            log(line, tag="lint")

    process.wait()

    full_output = "\n".join(output_lines)

    # After running, check for "Your code has been rated at" - Can update this later to choose passing score - maybe 10?
    if "Your code has been rated at" in full_output:
        score_line = next(
            (line for line in full_output.splitlines() if "Your code has been rated at" in line),
            None
        )
        if score_line:
            score = float(score_line.split(" ")[6].split("/")[0])
            log(f"📊 Pylint score: {score}/10", tag="lint")
            if score < 8.0:
                raise Exception(f"❌ ERROR - Lint failed! Score: {score}/10")
    else:
        log("⚠️ WARNING! Pylint score not found in output.", tag="lint")

    if process.returncode != 0:
        raise Exception(f"❌ ERROR! Linting failed.\n\n{full_output}")


def format_project(local_repo_path):
    """Formats code using Black formatter inside the Docker container ~SWAG"""
    log("💅 Running black formatter...", tag="format")

    cmd = (
        f"docker run --rm -v {local_repo_path}:/app project-image "
        "black --check app tests"
    )
    run_command_with_stream_output(cmd, tag="format")


def build_project(local_repo_path):
    """Builds the project inside a Docker container"""
    log(f"🏗️ Building project in {local_repo_path}", tag="build")

    dockerfile_path = os.path.join(local_repo_path, "Dockerfile")
    if not os.path.exists(dockerfile_path):
        raise Exception(f"❌ ERROR! No Dockerfile found at {dockerfile_path}")

    cmd = f"docker build -t project-image {local_repo_path}"
    run_command_with_stream_output(cmd, tag="build")


def run_tests(local_repo_path):
    """ Runs the test scripts for the user project also stream output """
    log(f"🧪 Running tests in {local_repo_path}", tag="test")

    cmd = (
        f"docker run --rm -v {local_repo_path}:/app "
        f"-w /app project-image pytest tests --tb=short"
    )

    log(f"🚀 Running command: {cmd}", tag="test")

    process = subprocess.Popen(
        cmd,
        shell=True,
        cwd=local_repo_path,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )

    output_lines = []

    # Stream output line-by-line
    for line in process.stdout:
        line = line.strip()
        if line:
            output_lines.append(line)
            log(line, tag="test")

    process.wait()

    full_output = "\n".join(output_lines)

    # Post-test checks
    if "collected 0 items" in full_output:
        # Check if __init__.py exists in tests directory
        test_init = os.path.join(local_repo_path, "tests", "__init__.py")
        if not os.path.exists(test_init):
            log("⚠️ WARNING: No tests were discovered.", tag="test")
            log("📂 Make sure your `tests/` directory has an `__init__.py` file.", tag="test")
        else:
            log(
                "⚠️ CAUTION! No tests discovered, but `__init__.py` exists. "
                "Check that your test files start with `test_` and contain test functions.",
                tag="test"
            )
        raise Exception("❌ ERROR! No tests discovered.")

    if process.returncode != 0:
        raise Exception(f"❌ Tests failed!\n{full_output}")

    log("✅ All tests passed!", tag="test")

def load_ci_config(local_repo_path):
    """ This is for the  configuration page where users can update their ci pipline steps """
    ci_config_path = os.path.join(local_repo_path, ".ci.yml")

    if not os.path.exists(ci_config_path):
        log("⚠️ CAUTION! No .ci.yml found, using default config.")
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
            log(f"🛠️ Loaded CI config: {config}")
            return {
                "lint": config.get("lint", True),
                "format": config.get("format", True),
                "build": config.get("build", True),
                "test": config.get("test", True),
                "run_commands": config.get("run_commands", [])
            }
    except Exception as e:
        log(f"❌ ERROR! Failed to load .ci.yml: {e}")
        raise

def run_command_with_stream_output(cmd, cwd=None, tag=None):
    """ Runs a shell command and streams output over WebSocket """
    # This statement is for when we have a tag - [LINT] or [TEST]
    if tag:
        log(f"🚀 Running command: {cmd}", tag=tag)
    else:
        log(f"🚀 Running command: {cmd}")

    process = subprocess.Popen(
        cmd,
        shell=True,
        cwd=cwd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )

    output_lines = []

    # Read output for each line
    for line in process.stdout:
        line = line.strip()
        if line:
            output_lines.append(line)
            log(line, tag=tag)

    process.wait()

    if process.returncode != 0:
        error_message = f"⛔️ ERROR during [{tag}] stage.\nExit Code: {process.returncode}\n\nOutput:\n" + "\n".join(output_lines)
        log(error_message, tag=tag or "error")
        raise Exception(error_message)
    
# ------------------------------------------------------------

if __name__ == "__main__":
    os.makedirs(REPO_DIRECTORY, exist_ok=True)
    socketio.run(app, debug=False, host="0.0.0.0", port=5000)
