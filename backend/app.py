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
from flask_cors import CORS
from threading import Lock
import uuid
import github_checks_helper as ghChecks
from models import database, Execution

app = Flask(__name__)
CORS(app, origins=["*"], supports_credentials=True)
app.config["SQLALCHEMY_DATABASE_URI"] = "postgresql://postgres@localhost:5432/postgres"
database.init_app(app)
socketio = SocketIO(app, cors_allowed_origins="*")
REPO_DIRECTORY = "/tmp/repos"

breakpoints = {
    "setup": {"before": False, "after": False},
    "build": {"before": False, "after": False},
    "test": {"before": False, "after": False},
}
bash_sessions = {}
collected_logs = {}
is_paused = False

DEBUG_ASCII_ART = """
-------------------------------------\n
Live Debugging Session\n
-------------------------------------\n
"""



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
            # log(event) # debugging purposes
            action = event.get("action")
            if action != "opened" and action != "synchronize":
                return json.dumps({"message": f"Ignored PR action: {action}"}), 200
        
        repo = event.get("repository", {})
        repo_title = repo.get("full_name")
        repo_url = repo.get("clone_url")
        local_repo_path = os.path.join(REPO_DIRECTORY, repo_title.replace("/", "_"))
        pr_title = event.get("title")

        # Skip builds for internal system repository
        if repo_title == "AadamYB/final-year-project":
            log(f"⚙️ Internal repo push detected for {repo_title} — skipping.")
            return json.dumps({"status": "ignored"}), 200
        
        build_id = generate_build_id(repo_title) # KEY AS THIS IS PASSED TO EVERYTHING

        ci_config = load_ci_config(local_repo_path, build_id)
        configure_breakpoints_from_ci(ci_config, build_id)

        log(f"🔧 Build session started with ID: {build_id}", tag="debug", build_id=build_id)

        if event_type == "pull_request":
            pr = event["pull_request"]
            pr_branch = pr.get("head", {}).get("ref")
            pr_number = pr.get("number")

            # Start by emitting to socket so the frontend can pick up correct details
            socketio.emit("build-started", {
                "build_id": build_id,
                "repo_title": repo_title,
                "pr_name": pr_title or f"PR#{pr_number}",
                "status": "Pending",
                "timestamp": datetime.now(timezone.utc).isoformat()
            })
            execution = Execution(
                id=build_id,
                repo_title=repo_title,
                pr_name=pr_title or f"PR#{pr_number}",
                timestamp=datetime.utcnow(),
                status="Pending"
            )
            database.session.add(execution)
            database.session.commit()

            log(f"Received PR#{pr_number} for branch {pr_branch} in {repo_title}.", build_id=build_id)

            commit_sha = pr.get("head", {}).get("sha")
            check_run_id = send_github_check(repo_title, commit_sha, build_id=build_id)

            try:
                # First we clone the repository if it does not already exist, if so then pull changes
                clone_or_pull(repo_url, local_repo_path, repo_title, build_id, pr_branch)

                # Then checkout the PR branch
                checkout_branch(local_repo_path, pr_branch, build_id)

                # Load .ci.yml if it exists
                ci_config = load_ci_config(local_repo_path, build_id)

                # Conditionally execute steps

                # We want to make sure that the code passes the formatting before building the project
                if ci_config.get("lint", True):
                    lint_project(local_repo_path, build_id)

                if ci_config.get("format", True):
                    format_project(local_repo_path, build_id)

                # Trigger the buiild and testing of the project
                if ci_config.get("build", True):
                    build_project(local_repo_path, repo_title, build_id)

                if ci_config.get("test", True):
                    run_tests(local_repo_path, repo_title, build_id)

                # If users add their own custom commands
                for cmd in ci_config.get("run_commands", []):
                    if isinstance(cmd, str):
                        log(f"🏃 Running custom command: {cmd}", build_id=build_id)
                        run_command_with_stream_output(cmd, build_id, cwd=local_repo_path, tag="custom")

                # All passed
                if check_run_id:
                    update_github_check(repo_title, check_run_id, "success", "All stages passed ✅", build_id=build_id)

                execution = Execution.query.get(build_id)
                if execution:
                    execution.status = "Passed"
                if execution and build_id in collected_logs:
                    execution.logs = "\n".join(collected_logs[build_id])
                    database.session.commit()

            except Exception as e:
                log(f"❌ ERROR! Pipeline failed mid-execution: {e}", build_id=build_id)
                finalize_failed_build(
                    build_id=build_id,
                    repo_title=repo_title,
                    check_run_id=check_run_id,
                    exception=e
                )

                return json.dumps({"status": "Pipeline failed"}), 500

            socketio.emit("build-finished", {
                "build_id": build_id,
                "status": "Passed"
            })
            
            return json.dumps({"status": "PR processed"}), 200


    except Exception as e:
        finalize_failed_build(
            build_id=locals().get("build_id"),
            repo_title=locals().get("repo_title"),
            check_run_id=locals().get("check_run_id"),
            exception=e
        )

        return json.dumps({"error": str(e)}), 500


@app.route("/executions/<build_id>", methods=["GET"])
def get_execution(build_id):
    execution = Execution.query.get(build_id)
    if not execution:
        return {"error": "Not found"}, 404

    return {
        "id": execution.id,
        "repo_title": execution.repo_title,
        "pr_name": execution.pr_name,
        "timestamp": execution.timestamp.isoformat(),
        "status": execution.status,
        "logs": execution.logs or "",
    }

@socketio.on('connect')
def handle_connect():
    log("🛜 WebSocket client connected ✅")


@socketio.on('start-debug')
def start_debug_session(data):
    repo = data.get("repo")
    build_id = data.get("build_id")

    # New check
    if build_id in bash_sessions and bash_sessions[build_id]["process"].poll() is None:
        log(f"🔁 Debug session already active for {build_id}", tag="debug", build_id=build_id)
        return
    
    log(f"🐞STARTING LIVE DEBUGGING SESSION🪲 for {repo}", tag="debug", build_id=build_id)

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
            log(f"🛑 Terminating debug session for {build_id}", tag="debug", build_id=build_id)
            session["process"].terminate()
        except Exception as e:
            log(f"⚠️ Warning! Could not terminate session: {e}", tag="debug", build_id=build_id)
        bash_sessions.pop(build_id, None)

@socketio.on('update-breakpoints')
def handle_update_breakpoints(data):
    global breakpoints

    expected_stages = {"setup", "build", "test"}
    expected_keys = {"before", "after"}

    build_id = data.get('build_id')

    if not isinstance(data, dict):
        log("❌ ERROR! Invalid breakpoint update: not a dict!", build_id=build_id)
        return

    # Validate structure of the breakpoint dict & its types
    for stage, points in data.items():
        if stage not in expected_stages:
            log(f"❌ ERROR! Invalid stage: {stage}", build_id=build_id)
            return
        if not isinstance(points, dict):
            log(f"❌ ERROR! {stage} should be a dict", build_id=build_id)
            return
        for key in expected_keys:
            if key not in points or not isinstance(points[key], bool):
                log(f"❌ ERROR! Invalid breakpoint type for {stage}.{key}", build_id=build_id)
                return

    # Save updated breakpoints
    breakpoints = data
    log(f"✅ Breakpoints updated to: {breakpoints}", tag="debug", build_id=build_id)
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

    # Track `cd` commands - well when we fix the debug console
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
def handle_pause(data):
    global is_paused
    is_paused = True
    build_id = data.get('build_id')
    log("⏸️ Pause signal received from frontend! Pausing pipeline...", tag="debug", build_id=build_id)

@socketio.on('resume')
def handle_resume(data):
    global is_paused
    is_paused = False
    build_id = data.get('build_id')
    log(f"🟢 Resume signal received! Continuing pipeline...", tag="debug", build_id=build_id)

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

def log(message, tag=None, build_id=None):
    """ Utility function that prints and emits the string message with a timestamp """
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    formatted_msg = f"[{timestamp}] [{'{}] '.format(tag.upper()) if tag else ''}{message}"

    print(formatted_msg)
    socketio.emit('log', {'log': formatted_msg})

    if build_id:
        if build_id not in collected_logs:
            collected_logs[build_id] = []
        collected_logs[build_id].append(formatted_msg)


def clone_or_pull(repo_url, local_repo_path, repo_title, build_id, branch):
    """ Clones a GitHub repository to a local directory or
        Pulls latest changes from the repository """
    
    socketio.emit('active-stage-update', {'stage': 'setup'})
    pause_execution('setup', 'before', build_id, repo_title)   # Can optionally pause a pileline before executing command

    if not os.path.exists(local_repo_path):
        log(f"🔄 Cloning {repo_url}")
        cmd = f"git clone {repo_url} {local_repo_path}"
        run_command_with_stream_output(cmd, build_id, tag="clone")
    else:
        log(f"🔁 Pulling latest changes in {local_repo_path}")
        cmd = f"git -C {local_repo_path} pull origin {branch}"
        run_command_with_stream_output(cmd, build_id, tag="pull")
    
    pause_execution('setup', 'after', build_id, repo_title)



def checkout_branch(local_repo_path, branch_name, build_id):
    """ Checkouts the correct branch for the Pull Request """
    log(f"🌿 Checking out branch: {branch_name}", build_id=build_id)
    # fetch latest branches
    cmd_fetch = f"git -C {local_repo_path} fetch origin"
    run_command_with_stream_output(cmd_fetch, build_id, tag="checkout")

    # checkout to the correct branch
    cmd_checkout = f"git -C {local_repo_path} checkout {branch_name}"
    run_command_with_stream_output(cmd_checkout, build_id, tag="checkout")


def lint_project(local_repo_path, build_id):
    """ Runs pylint inside Docker to ensure code quality, streaming output and checking scores. """
    log("🔍 Running pylint checks...", tag="lint", build_id=build_id)

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

    log(f"🚀 Running command: {cmd}", tag="lint", build_id=build_id)

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
            log(line, tag="lint", build_id=build_id)

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
            log(f"📊 Pylint score: {score}/10", tag="lint", build_id=build_id)
            if score < 8.0:
                raise Exception(f"❌ ERROR - Lint failed! Score: {score}/10")
    else:
        log("⚠️ WARNING! Pylint score not found in output.", tag="lint", build_id=build_id)

    if process.returncode != 0:
        raise Exception(f"❌ ERROR! Linting failed.\n\n{full_output}")


def format_project(local_repo_path, build_id):
    """ Formats code using Black formatter inside the Docker container ~SWAG """
    log("💅 Running black formatter...", tag="format", build_id=build_id)

    cmd = (
        f"docker run --rm -v {local_repo_path}:/app project-image "
        "black --check app tests"
    )
    run_command_with_stream_output(cmd, build_id, tag="format")


def build_project(local_repo_path, repo_title, build_id):
    """ Builds the project inside a Docker container """

    socketio.emit('active-stage-update', {'stage': 'build'})
    pause_execution('build', 'before', build_id, repo_title)   # Can choose to pause pipeline if we want - according to user

    log(f"🏗️ Building project in {local_repo_path}", tag="build", build_id=build_id)

    dockerfile_path = os.path.join(local_repo_path, "Dockerfile")
    if not os.path.exists(dockerfile_path):
        raise Exception(f"❌ ERROR! No Dockerfile found at {dockerfile_path}")

    # Create docker-(image and/or container) name based on repo
    repo_title = os.path.basename(local_repo_path)
    image_name = f"{build_id.lower()}-image"
    container_name = f"{build_id.lower()}-container"

    # Build docker image
    run_command_with_stream_output(f"docker build -t {image_name} {local_repo_path}", build_id, tag="build")

    # SKIP THIS ENTIRELY - as the container doesn't exist yet - we can build on this later [TODO]
    # Stop and remove old container if exists
    # run_command_with_stream_output(f"docker rm -f {container_name} || true", build_id, tag="build")

    # Start container in background
    run_command_with_stream_output(
        f"docker run -d --name {container_name} -v {local_repo_path}:/app {image_name} tail -f /dev/null",
        build_id,
        tag="build"
    )

    log(f"🚀 Container {container_name} running for debugging!", tag="build", build_id=build_id)

    pause_execution('build', 'after', build_id, repo_title)


def run_tests(local_repo_path, repo_title, build_id):
    """ Runs the test scripts for the user project also stream output """

    socketio.emit('active-stage-update', {'stage': 'test'})
    pause_execution('test', 'before', build_id, repo_title) 

    log(f"🧪 Running tests in {local_repo_path}", tag="test", build_id=build_id)

    image_name = f"{build_id.lower()}-image"
    cmd = (
        f"docker run --rm -v {local_repo_path}:/app "
        f"-w /app {image_name} pytest tests --tb=short"
    )

    log(f"🚀 Running command: {cmd}", tag="test", build_id=build_id)

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
            log(line, tag="test", build_id=build_id)

    process.wait()

    full_output = "\n".join(output_lines)

    # Post-test checks
    if "collected 0 items" in full_output:
        # Check if __init__.py exists in tests directory
        test_init = os.path.join(local_repo_path, "tests", "__init__.py")
        if not os.path.exists(test_init):
            log("⚠️ WARNING: No tests were discovered.", tag="test", build_id=build_id)
            log("📂 Make sure your `tests/` directory has an `__init__.py` file.", tag="test", build_id=build_id)
        else:
            log(
                "⚠️ CAUTION! No tests discovered, but `__init__.py` exists. "
                "Check that your test files start with `test_` and contain test functions.",
                tag="test",
                build_id=build_id
            )
        raise Exception("❌ ERROR! No tests discovered.")

    if process.returncode != 0:
        raise Exception(f"❌ Tests failed!\n{full_output}")

    log("✅ All tests passed!", tag="test", build_id=build_id)

    pause_execution('test', 'after', build_id, repo_title) 

def load_ci_config(local_repo_path, build_id):
    """ This is for the  configuration page where users can update their ci pipline steps """
    ci_config_path = os.path.join(local_repo_path, ".ci.yml")

    if not os.path.exists(ci_config_path):
        log("⚠️ CAUTION! No .ci.yml found, using default config.", build_id=build_id)
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
            log(f"🚀 Loaded CI config: {config}", build_id=build_id)
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
        log(f"❌ ERROR! Failed to load .ci.yml: {e}", build_id=build_id)
        raise

def configure_breakpoints_from_ci(ci_config, build_id):
    global breakpoints
    breakpoints = {
        "setup": {"before": ci_config.get("pause_before_clone", False), "after": ci_config.get("pause_after_clone", False)},
        "build": {"before": ci_config.get("pause_before_build", False), "after": ci_config.get("pause_after_build", False)},
        "test": {"before": ci_config.get("pause_before_test", False), "after": ci_config.get("pause_after_test", False)},
    }
    log(f"Breakpoints configured: {breakpoints}", tag="debug", build_id=build_id)
    socketio.emit("pause-configured", {"breakpoints": breakpoints})


def run_command_with_stream_output(cmd, build_id, cwd=None, tag=None):
    """ Runs a shell command and streams output over WebSocket """
    # This statement is for when we have a tag - [LINT] or [TEST]
    if tag:
        log(f"🚀 Running command: {cmd}", tag=tag, build_id=build_id)
    else:
        log(f"🚀 Running command: {cmd}", build_id=build_id)

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
            log(line, tag=tag, build_id=build_id)

    process.wait()

    if process.returncode != 0:
        error_message = f"⛔️ ERROR during [{tag}] stage. ❌\nExit Code: {process.returncode}\n\nOutput:\n" + "\n".join(output_lines)
        log(error_message, tag=tag or "error", build_id=build_id)
        raise Exception(error_message)
    

def pause_execution(stage, when, build_id, repo_title):
    """ helper function that pauses an execution """
    global is_paused

    # Check if the current stage needs to be paused and also when it needs to be paused
    if not breakpoints.get(stage, {}).get(when, False):
        return
    
    log(f"🚨 Pausing at {stage.upper()} ({when.upper()}) ... Waiting for resume command!", tag="debug", build_id=build_id)
    is_paused = True

    ensure_debug_session_started(build_id, repo_title)

    socketio.emit('allow-breakpoint-edit', {"stage": stage.upper(), "when": when.upper()})
    log("🔓 User can now edit future breakpoints during pause!", tag="debug", build_id=build_id)

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

def send_github_check(repo_title, commit_sha, check_name="CI Pipeline", build_id=None):
    """ Creates a new GitHub check run and returns the check_run_id """
    try:
        check = ghChecks.create_check(
            repo_title,
            commit_sha,
            check_name,
            status="in_progress",
            output={
                "title": "CI Pipeline Running...",
                "summary": f"View real-time logs at [Debug UI](http://localhost:3000/debug/{build_id})",
            },
        )
        return check["id"]
    except Exception as e:
        log(f"❌ Failed to create GitHub Check Run: {e}", build_id=build_id)
        return None


def update_github_check(repo_title, check_run_id, conclusion="success", summary="", build_id=None):
    """ Updates an existing GitHub check run with final status """
    if not check_run_id:
        return

    try:
        full_summary = summary
        if build_id:
            full_summary += f"\n\n🔗 [View debug logs](http://localhost:3000/debug/{build_id})"

        ghChecks.update_check(
            repo_title,
            check_run_id,
            status="completed",
            conclusion=conclusion,
            output={
                "title": f"Build {'Passed ✅' if conclusion == 'success' else 'Failed ❌'}",
                "summary": full_summary
            }
        )
        log(f"📬 Check run updated: {conclusion.upper()}", build_id=build_id)
    except Exception as e:
        log(f"⚠️ Failed to update check run: {e}", build_id=build_id)

def finalize_failed_build(build_id, repo_title, check_run_id, exception):
    """ Helper that updates the execution in the database when the pipeline execution fails """
    log(f"❌ ERROR! Pipeline failed: {exception}", build_id=build_id)

    if check_run_id:
        update_github_check(repo_title, check_run_id, "failure", str(exception), build_id=build_id)

    if build_id:
        execution = Execution.query.get(build_id)
        if execution:
            execution.status = "Failed"
        if execution and build_id in collected_logs:
            execution.logs = "\n".join(collected_logs[build_id])
            database.session.commit()

        socketio.emit("build-finished", {
            "build_id": build_id,
            "status": "Failed"
        })

# ------------------------------------------------------------

if __name__ == "__main__":
    # This is for a broken duplicate repo that is causing referencing 
    # errors everytime we pull to the new repo(with the same name...)
    # we can leave this in for any similar future issues  <---
    # Ran "python app.py"

    # broken_repo = "/tmp/repos/AadamYB_noughts-N-crosses"
    # if os.path.exists(broken_repo):
    #     import shutil
    #     print(f"🧹 Deleting stale repo at {broken_repo}...")
    #     shutil.rmtree(broken_repo)
    #     print("✅ Repo removed. You can now comment out this block.")


    os.makedirs(REPO_DIRECTORY, exist_ok=True)
    socketio.run(app, debug=False, host="0.0.0.0", port=5000)
