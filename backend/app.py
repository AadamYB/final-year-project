from flask import Flask, request, json
import os
import subprocess

app = Flask(__name__)
REPO_DIRECTORY = "/tmp/repos"


@app.route("/")
def api_root():
    return "Server is running and receiving events!"


@app.route("/events", methods=["POST"])
def api_events():
    try:
        event = request.json
        if not event:
            return json.dumps({"message": "No event data received"}), 400

        repo = event.get("repository", {})
        repo_title = repo.get("full_name")
        repo_url = repo.get("clone_url")
        local_repo_path = os.path.join(REPO_DIRECTORY, repo_title.replace("/", "_"))

        # Handles Pull Request Events
        if "pull_request" in event:
            pr = event["pull_request"]
            pr_branch = pr.get("head", {}).get("ref")
            pr_number = pr.get("number")
            print(f"Received PR#{pr_number} for branch {pr_branch} in {repo_title}.")

            # First we clone the repository if it does not already exist, if so then pull changes
            clone_or_pull(repo_url, local_repo_path)

            # Then checkout the PR branch
            checkout_branch(local_repo_path, pr_branch)

            # We want to make sure that the code passes the formatting before building the project
            lint_project(local_repo_path)
            format_project(local_repo_path)

            # Trigger the buiild and testing of the project
            build_project(local_repo_path)
            run_tests(local_repo_path)

            return json.dumps({"status": "PR processed"}), 200

        # Handles Push Events
        elif "pusher" in event and "ref" in event:
            push_branch = event.get("ref").split("/")[-1]
            print(f"Received push to {push_branch} in {repo_title}.")

            # First we clone the repository if it does not already exist, if so then pull changes
            clone_or_pull(repo_url, local_repo_path)

            # Then checkout the PR branch
            checkout_branch(local_repo_path, push_branch)

            # We want to make sure that the code passes the formatting before building the project
            lint_project(local_repo_path)
            format_project(local_repo_path)

            # Trigger the buiild and testing of the project
            build_project(local_repo_path)
            run_tests(local_repo_path)

            return json.dumps({"status": "Push processed"}), 200

        print("Unsupported or unknown event.")
        return json.dumps({"message": "Unsupported or unknown event type"}), 400

    except Exception as e:
        print(f"❌ Pipeline failed: {e}")
        return json.dumps({"error": str(e)}), 500

# ---------------------------------------------------------------------------------------------
# ------------------------------------ Utility Functions --------------------------------------
# ---------------------------------------------------------------------------------------------

def clone_or_pull(repo_url, local_repo_path):
    """ Clones a GitHub repository to a local directory and/or
        Pulls latest changes from the repository """
    if not os.path.exists(local_repo_path):
        print(f"🔄 Cloning {repo_url}")
        subprocess.run(["git", "clone", repo_url, local_repo_path], check=True)
    else:
        print(f"🔁 Pulling latest changes in {local_repo_path}")
        subprocess.run(["git", "-C", local_repo_path, "pull"], check=True)


def checkout_branch(local_repo_path, branch_name):
    """ Checkouts the correct branch for the Pull Request """
    print(f"🌿 Checking out branch: {branch_name}")
    subprocess.run(["git", "-C", local_repo_path, "fetch", "origin"], check=True)
    subprocess.run(["git", "-C", local_repo_path, "checkout", branch_name], check=True)


def lint_project(local_repo_path):
    """ Runs pylint inside Docker to ensure code quality ~ SWAG """
    print("🔍 Running pylint checks...")

    pylint_config_path = "/app/.pylintrc"
    target_file = "/app/app/main.py"

    # Ensure the file exists inside the local repo (host side) before Docker call
    if not os.path.exists(os.path.join(local_repo_path, "app", "main.py")):
        raise Exception("❌ Target file app/main.py does not exist!")

    if not os.path.exists(os.path.join(local_repo_path, ".pylintrc")):
        raise Exception("❌ .pylintrc config file not found in the project root!")

    try:
        result = subprocess.run(
            [
                "docker", "run", "--rm",
                "-v", f"{local_repo_path}:/app",
                "project-image", "pylint",
                "--rcfile", pylint_config_path,
                target_file
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=True
        )
        print(result.stdout)

        # Check score
        if "Your code has been rated at" in result.stdout:
            score_line = next(
                line for line in result.stdout.splitlines()
                if "Your code has been rated at" in line
            )
            score = float(score_line.split(" ")[6].split("/")[0])
            print(f"📊 Pylint score: {score}/10")
            if score < 8.0:
                raise Exception(f"❌ Lint failed! Score: {score}/10")

    except subprocess.CalledProcessError as e:
        print("❌ Pylint returned an error.")
        print("STDOUT:\n", e.stdout)
        print("STDERR:\n", e.stderr)

        if "No module named" in e.stderr or "load-plugins" in e.stderr:
            print("💡 HINT: Check if all plugins in `.pylintrc` are installed.")
            print("🔧 You can fix this by adding:")
            print("    pylint[docparams,typing,code_style]")
            print("  to your `requirements.txt` and rebuilding the Docker image.")

        raise Exception("❌ Linting failed due to error above.")


def format_project(local_repo_path):
    """ Formats code using Black formatter inside the Docker container ~SWAG """
    print("💅 Running black formatter...")

    try:
        subprocess.run(
            [
                "docker", "run", "--rm",
                "-v", f"{local_repo_path}:/app",
                "project-image",
                "black", "--check", "app", "tests"
            ],
            check=True
        )
        print("✅ Code is already formatted.")
    
    except subprocess.CalledProcessError as e:
        raise Exception("Black formatting required!")


def build_project(local_repo_path):
    """Builds the project inside a Docker container"""
    print(f"🏗️ Building project in {local_repo_path}")
    dockerfile_path = os.path.join(local_repo_path, "Dockerfile")
    if not os.path.exists(dockerfile_path):
        raise Exception(f"❌ No Dockerfile found at {dockerfile_path}")

    subprocess.run(["docker", "build", "-t", "project-image", local_repo_path], check=True)
    print("✅ Build completed.")


def run_tests(local_repo_path):
    """Runs the test scripts for the user project"""
    print(f"🧪 Running tests in {local_repo_path}")

    result = subprocess.run(
        [
            "docker", "run", "--rm",
            "-v", f"{local_repo_path}:/app",
            "project-image",
            "python3", "-m", "unittest", "discover", "-s", "tests"
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )

    print("STDOUT:\n", result.stdout or "[no output]")
    print("STDERR:\n", result.stderr or "[no errors]")

    if result.returncode != 0:
        if "Ran 0 tests" in result.stdout:
            print("⚠️ WARNING: No tests were discovered.")
            print("📂 Make sure your `tests/` directory has an `__init__.py` file.")
            print("🧪 Also check that your test files start with `test_` and contain functions starting with `test_`.")
        raise Exception("❌ Test run failed or no tests discovered.")

    print("✅ All tests passed!")


# ------------------------------------------------------------

if __name__ == "__main__":
    os.makedirs(REPO_DIRECTORY, exist_ok=True)
    app.run(debug=True, host="0.0.0.0", port=5000)