from flask import Flask, request, json
import os
import subprocess
from flask_socketio import SocketIO, emit
import yaml
from datetime import datetime, timezone
import time
import re
import threading
import pty
from threading import Lock
import uuid
import github_checks_helper as ghChecks

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*")
REPO_DIRECTORY = "/tmp/repos"

breakpoints = {
    "setup": {"before": False, "after": False},
    "build": {"before": False, "after": False},
    "test": {"before": False, "after": False},
}

bash_sessions = {}

DEBUG_ASCII_ART = """
-------------------------------------
Live Debugging Session
-------------------------------------
"""

is_paused = False


@app.route("/")
def api_root():
    return "Server is running and receiving events!"


@app.route("/events", methods=["POST"])
def api_events():
    try:
        event_type = request.headers.get("X-GitHub-Event", "unknown")
        event = request.json

        if not event:
            return json.dumps({"message": "No event data received"}), 400
        
        # We only want push and pull request events to get processed - otherwise ignore
        # if event_type not in {"pull_request", "push"}:
        if event_type != "pull_request":
            return json.dumps({"message": f"Ignored event type: {event_type}"}), 200
        
        # is the PR closed? if so skip
        if event_type == "pull_request":
            log(event) # debugging purposes
            action = event.get("action")
            if action != "opened" and action != "synchronize":
                return json.dumps({"message": f"Ignored PR action: {action}"}), 200
        
        repo = event.get("repository", {})
        repo_title = repo.get("full_name")
        repo_url = repo.get("clone_url")
        local_repo_path = os.path.join(REPO_DIRECTORY, repo_title.replace("/", "_"))

        # Skip builds for internal system repository
        if repo_title == "AadamYB/final-year-project":
            log(f"⚙️ Internal repo push detected for {repo_title} — skipping.")
            return json.dumps({"status": "ignored"}), 200
        
        ci_config = load_ci_config(local_repo_path)
        configure_breakpoints_from_ci(ci_config)

        build_id = generate_build_id(repo_title)
        log(f"🔧 Build session started with ID: {build_id}", tag="debug")

        if event_type == "pull_request":
            pr = event["pull_request"]
            pr_branch = pr.get("head", {}).get("ref")
            pr_number = pr.get("number")
            log(f"Received PR#{pr_number} for branch {pr_branch} in {repo_title}.")

            commit_sha = pr.get("head", {}).get("sha")
            check_run_id = send_github_check(repo_title, commit_sha)

            try:
                # First we clone the repository if it does not already exist, if so then pull changes
                clone_or_pull(repo_url, local_repo_path, repo_title, build_id, pr_branch)

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
                    build_project(local_repo_path, repo_title, build_id)

                if ci_config.get("test", True):
                    run_tests(local_repo_path, repo_title, build_id)

                # If users add their own custom commands
                for cmd in ci_config.get("run_commands", []):
                    if isinstance(cmd, str):
                        log(f"🏃 Running custom command: {cmd}")
                        run_command_with_stream_output(cmd, cwd=local_repo_path, tag="custom")

                # All passed
                if check_run_id:
                    update_github_check(repo_title, check_run_id, "success", "All stages passed ✅")

            except Exception as e:
                log(f"❌ ERROR! Pipeline failed mid-execution: {e}")
                if check_run_id:
                    update_github_check(repo_title, check_run_id, "failure", str(e))
                return json.dumps({"status": "Pipeline failed"}), 500

            return json.dumps({"status": "PR processed"}), 200

        # We remove this entirely?
        # elif event_type == "push":
        #     push_branch = event.get("ref", "").split("/")[-1]
        #     commit_sha = event.get("after")
        #     log(f"📦 Received push to `{push_branch}` in {repo_title}.")

        #     check_run_id = send_github_check(repo_title, commit_sha)

        #     try:
        #         # Clone or pull latest changes
        #         clone_or_pull(repo_url, local_repo_path, repo_title, build_id, push_branch)

        #         # Checkout the push branch
        #         checkout_branch(local_repo_path, push_branch)

        #         # Reload CI config after checkout
        #         ci_config = load_ci_config(local_repo_path)

        #         # Run CI stages conditionally - based on the breakpoint-dictionary/.ci.yml file
        #         if ci_config.get("lint", True):
        #             lint_project(local_repo_path)

        #         if ci_config.get("format", True):
        #             format_project(local_repo_path)

        #         if ci_config.get("build", True):
        #             build_project(local_repo_path, repo_title, build_id)

        #         if ci_config.get("test", True):
        #             run_tests(local_repo_path, repo_title, build_id)

        #         for cmd in ci_config.get("run_commands", []):
        #             if isinstance(cmd, str):
        #                 log(f"🏃 Running custom command: {cmd}")
        #                 run_command_with_stream_output(cmd, cwd=local_repo_path, tag="custom")

        #         if check_run_id:
        #             update_github_check(
        #                 repo_title,
        #                 check_run_id,
        #                 "success",
        #                 f"All stages passed ✅\nBuild ID: `{build_id}`"
        #             )

        #     except Exception as e:
        #         log(f"❌ ERROR! Push pipeline failed: {e}")
        #         if check_run_id:
        #             update_github_check(
        #                 repo_title,
        #                 check_run_id,
        #                 "failure",
        #                 f"Push pipeline failed ❌\nBuild ID: `{build_id}`\n\nError: {str(e)}"
        #             )
        #         return json.dumps({"status": "Push failed"}), 500
            
        #     return json.dumps({"status": "Push processed"}), 200

    except Exception as e:
        log(f"❌ ERROR! Pipeline failed: {e}")
        return json.dumps({"error": str(e)}), 500


@socketio.on('connect')
def handle_connect():
    log("🛜 WebSocket client connected ✅")


@socketio.on('start-debug')
def start_debug_session(data):
    repo = data.get("repo")
    build_id = data.get("build_id")

    # New check
    if build_id in bash_sessions and bash_sessions[build_id]["process"].poll() is None:
        log(f"🔁 Debug session already active for {build_id}", tag="debug")
        return
    
    log(f"🐞STARTING LIVE DEBUGGING SESSION🪲 for {repo}", tag="debug")

    # Create interactive bash
    build_id = re.sub(r'[^a-zA-Z0-9_\-]', '', repo)
    container_name = f"{build_id.lower()}-container"

    master_fd, slave_fd = pty.openpty()
    process = subprocess.Popen(
        ["docker", "exec", "-i", container_name, "bash"],
        stdin=slave_fd,
        stdout=slave_fd,
        stderr=slave_fd,
        universal_newlines=True
    )

    # to track the current working directory for each session
    bash_sessions[build_id] = {
        "process": process,
        "master_fd": master_fd,
        "cwd": "~",
        "lock": Lock()  # this should fix the race conditions issue
    }
    socketio.emit("debug-session-started", {"build_id": build_id})

    def listen_to_bash():
        ascii_shown = False
        while True:
            try:
                with bash_sessions[build_id]["lock"]:
                    output = os.read(master_fd, 1024).decode()

                 # Custom prompt - should be like this: " repo-name@13.40.55.105 ~$ "
                if output:
                    user = repo.split("/")[-1]
                    ip = "13.40.55.105"
                    cwd = bash_sessions[build_id]["cwd"]
                    prompt = f"\n{user}@{ip} {cwd} ~$ "
                    
                    if not ascii_shown:
                        output = DEBUG_ASCII_ART + "\n" + output
                        ascii_shown = True

                    socketio.emit('console-output', {'output': output + prompt})
            except Exception:
                break
    
    threading.Thread(target=listen_to_bash, daemon=True).start()

@socketio.on("stop-debug")
def stop_debug(data):
    build_id = data.get("build_id")
    session = bash_sessions.get(build_id)
    if session:
        try:
            log(f"🛑 Terminating debug session for {build_id}", tag="debug")
            session["process"].terminate()
        except Exception as e:
            log(f"⚠️ Warning! Could not terminate session: {e}", tag="debug")
        bash_sessions.pop(build_id, None)

@socketio.on('update-breakpoints')
def handle_update_breakpoints(data):
    global breakpoints

    expected_stages = {"setup", "build", "test"}
    expected_keys = {"before", "after"}

    if not isinstance(data, dict):
        log("❌ ERROR! Invalid breakpoint update: not a dict!")
        return

    # Validate structure of the breakpoint dict & its types
    for stage, points in data.items():
        if stage not in expected_stages:
            log(f"❌ ERROR! Invalid stage: {stage}")
            return
        if not isinstance(points, dict):
            log(f"❌ ERROR! {stage} should be a dict")
            return
        for key in expected_keys:
            if key not in points or not isinstance(points[key], bool):
                log(f"❌ ERROR! Invalid breakpoint type for {stage}.{key}")
                return

    # Save updated breakpoints
    breakpoints = data
    log(f"✅ Breakpoints updated to: {breakpoints}", tag="debug")
    socketio.emit("breakpoints-updated", {"breakpoints": breakpoints})

@socketio.on('console-command')
def handle_console_command(data):
    char = data.get('command')
    repo_title = data.get('repoTitle')
    build_id = data.get('build_id') 

    if not char or not build_id:
        emit('console-output', {'output': '❌ ERROR! Missing command or repoTitle'})
        return

    session = bash_sessions.get(build_id)
    if not session:
        emit('console-output', {'output': '❌ ERROR! Debug session not active.'})
        return

    master_fd = session["master_fd"]
    process = session["process"]

    # Track `cd` commands
    if char.startswith("cd "):
        new_dir = char.strip().split("cd ")[-1].strip()
        if new_dir == "..":
            session["cwd"] = os.path.dirname(session["cwd"])
        elif new_dir.startswith("/"):
            session["cwd"] = new_dir
        else:
            session["cwd"] = os.path.normpath(os.path.join(session["cwd"], new_dir))


    try:
        with session["lock"]:
            os.write(master_fd, char.encode())
    except Exception as e:
        emit('console-output', {'output': f"❌ ERROR! Exception: {str(e)}"})

@socketio.on('pause')
def handle_pause():
    global is_paused
    is_paused = True
    log("⏸️ Pause signal received from frontend! Pausing pipeline...", tag="debug")

@socketio.on('resume')
def handle_resume():
    global is_paused
    is_paused = False
    log(f"🟢 Resume signal received! Continuing pipeline...", tag="debug")

@socketio.on('disconnect')
def handle_disconnect():
    log("🛜 WebSocket client disconnected ❌")
    for build_id, session in bash_sessions.items():
        try:
            session["process"].terminate()
        except Exception:
            pass
    bash_sessions.clear()

# ---------------------------------------------------------------------------------------------
# ------------------------------------ Utility Functions --------------------------------------
# ---------------------------------------------------------------------------------------------

def log(message, tag=None):
    """ Utility function that prints and emits the string message with a timestamp """
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")

    if tag:
        formatted_msg = f"[{timestamp}] [{tag.upper()}] {message}"
    else:
        formatted_msg = f"[{timestamp}] {message}"

    print(formatted_msg)
    socketio.emit('log', {'log': formatted_msg})


def clone_or_pull(repo_url, local_repo_path, repo_title, build_id, branch):
    """ Clones a GitHub repository to a local directory or
        Pulls latest changes from the repository """
    
    socketio.emit('active-stage-update', {'stage': 'setup'})
    pause_execution('setup', 'before', build_id, repo_title)   # Can optionally pause a pileline before executing command

    if not os.path.exists(local_repo_path):
        log(f"🔄 Cloning {repo_url}")
        cmd = f"git clone {repo_url} {local_repo_path}"
        run_command_with_stream_output(cmd, tag="clone")
    else:
        log(f"🔁 Pulling latest changes in {local_repo_path}")
        cmd = f"git -C {local_repo_path} pull origin {branch}"
        run_command_with_stream_output(cmd, tag="pull")
    
    pause_execution('setup', 'after', build_id, repo_title)



def checkout_branch(local_repo_path, branch_name):
    """ Checkouts the correct branch for the Pull Request """
    log(f"🌿 Checking out branch: {branch_name}")
    # fetch latest branches
    cmd_fetch = f"git -C {local_repo_path} fetch origin"
    run_command_with_stream_output(cmd_fetch, tag="checkout")

    # checkout to the correct branch
    cmd_checkout = f"git -C {local_repo_path} checkout {branch_name}"
    run_command_with_stream_output(cmd_checkout, tag="checkout")


def lint_project(local_repo_path):
    """ Runs pylint inside Docker to ensure code quality, streaming output and checking scores. """
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
    """ Formats code using Black formatter inside the Docker container ~SWAG """
    log("💅 Running black formatter...", tag="format")

    cmd = (
        f"docker run --rm -v {local_repo_path}:/app project-image "
        "black --check app tests"
    )
    run_command_with_stream_output(cmd, tag="format")


def build_project(local_repo_path, repo_title, build_id):
    """ Builds the project inside a Docker container """

    socketio.emit('active-stage-update', {'stage': 'build'})
    pause_execution('build', 'before', build_id, repo_title)   # Can choose to pause pipeline if we want - according to user

    log(f"🏗️ Building project in {local_repo_path}", tag="build")

    dockerfile_path = os.path.join(local_repo_path, "Dockerfile")
    if not os.path.exists(dockerfile_path):
        raise Exception(f"❌ ERROR! No Dockerfile found at {dockerfile_path}")

    # Create docker-(image and/or container) name based on repo
    repo_title = os.path.basename(local_repo_path)
    image_name = f"{build_id.lower()}-image"
    container_name = f"{build_id.lower()}-container"

    # Build docker image
    run_command_with_stream_output(f"docker build -t {image_name} {local_repo_path}", tag="build")

    # Stop and remove old container if exists
    run_command_with_stream_output(f"docker rm -f {container_name} || true", tag="build")

    # Start container in background
    run_command_with_stream_output(
        f"docker run -d --name {container_name} -v {local_repo_path}:/app {image_name} tail -f /dev/null",
        tag="build"
    )

    log(f"🚀 Container {container_name} running for debugging!", tag="build")

    pause_execution('build', 'after', build_id, repo_title)


def run_tests(local_repo_path, repo_title, build_id):
    """ Runs the test scripts for the user project also stream output """

    socketio.emit('active-stage-update', {'stage': 'test'})
    pause_execution('test', 'before', build_id, repo_title) 

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

    pause_execution('test', 'after', build_id, repo_title) 

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
            "run_commands": [],
            "pause_before_clone": False,
            "pause_after_clone": False,
            "pause_before_build": False,
            "pause_after_build": False,
            "pause_before_test": False,
            "pause_after_test": False,
            "pause_increment": False,
        }

    try:
        with open(ci_config_path, "r") as f:
            config = yaml.safe_load(f)
            log(f"🚀 Loaded CI config: {config}")
            return {
                "lint": config.get("lint", True),
                "format": config.get("format", True),
                "build": config.get("build", True),
                "test": config.get("test", True),
                "run_commands": config.get("run_commands", []),
                "pause_before_clone": config.get("pause_before_clone", False),
                "pause_after_clone": config.get("pause_after_clone", False),
                "pause_before_build": config.get("pause_before_build", False),
                "pause_after_build": config.get("pause_after_build", False),
                "pause_before_test": config.get("pause_before_test", False),
                "pause_after_test": config.get("pause_after_test", False),
                "pause_increment": config.get("pause_increment", False),
            }
    except Exception as e:
        log(f"❌ ERROR! Failed to load .ci.yml: {e}")
        raise

def configure_breakpoints_from_ci(ci_config):
    global breakpoints
    breakpoints = {
        "setup": {"before": ci_config.get("pause_before_clone", False), "after": ci_config.get("pause_after_clone", False)},
        "build": {"before": ci_config.get("pause_before_build", False), "after": ci_config.get("pause_after_build", False)},
        "test": {"before": ci_config.get("pause_before_test", False), "after": ci_config.get("pause_after_test", False)},
    }
    log(f"Breakpoints configured: {breakpoints}", tag="debug")
    socketio.emit("pause-configured", {"breakpoints": breakpoints})


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
        error_message = f"⛔️ ERROR during [{tag}] stage. ❌\nExit Code: {process.returncode}\n\nOutput:\n" + "\n".join(output_lines)
        log(error_message, tag=tag or "error")
        raise Exception(error_message)
    

def pause_execution(stage, when, build_id, repo_title):
    """ helper function that pauses an execution """
    global is_paused

    # Check if the current stage needs to be paused and also when it needs to be paused
    if breakpoints.get(stage, {}).get(when, False):
        log(f"🚨 Pausing at {stage.upper()} ({when.upper()}) ... Waiting for resume command!", tag="debug")
        is_paused = True

        ensure_debug_session_started(build_id, repo_title)

        # start_debug_session({"repo": repo_title, "build_id": build_id})

        socketio.emit('allow-breakpoint-edit', {"stage": stage.upper(), "when": when.upper()})
        log("🔓 User can now edit future breakpoints during pause!", tag="debug")

        # Loop until resume is received
        while is_paused:
            time.sleep(0.5)  # check every half second

def ensure_debug_session_started(build_id, repo):
    session = bash_sessions.get(build_id)
    if session is None or session["process"].poll() is not None:
        start_debug_session({"repo": repo, "build_id": build_id})

def generate_build_id(repo_title: str) -> str:
    timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
    unique_id = uuid.uuid4().hex[:8]
    safe_repo = repo_title.replace("/", "_")
    return f"{safe_repo}-{timestamp}-{unique_id}"

def send_github_check(repo_title, commit_sha, check_name="CI Pipeline"):
    """ Creates a new GitHub check run and returns the check_run_id """
    try:
        check = ghChecks.create_check(repo_title, commit_sha, check_name, status="in_progress")
        return check["id"]
    except Exception as e:
        log(f"❌ Failed to create GitHub Check Run: {e}")
        return None


def update_github_check(repo_title, check_run_id, conclusion="success", summary=""):
    """ Updates an existing GitHub check run with final status """
    if not check_run_id:
        return

    try:
        ghChecks.update_check(
            repo_title,
            check_run_id,
            status="completed",
            conclusion=conclusion,
            output={
                "title": f"Build {'Passed ✅' if conclusion == 'success' else 'Failed ❌'}",
                "summary": summary
            }
        )
        log(f"📬 Check run updated: {conclusion.upper()}")
    except Exception as e:
        log(f"⚠️ Failed to update check run: {e}")

# ------------------------------------------------------------

if __name__ == "__main__":
    # broken_repo = "/tmp/repos/AadamYB_noughts-N-crosses"
    # if os.path.exists(broken_repo):
    #     import shutil
    #     print(f"🧹 Deleting stale repo at {broken_repo}...")
    #     shutil.rmtree(broken_repo)
    #     print("✅ Repo removed. You can now comment out this block.")


    os.makedirs(REPO_DIRECTORY, exist_ok=True)
    socketio.run(app, debug=False, host="0.0.0.0", port=5000)
