from flask import Flask, request, json, has_app_context
import os
import subprocess
from flask_socketio import SocketIO, emit
import yaml
from datetime import datetime, timezone, timedelta
import time
import re
import threading
import pty
from flask_cors import CORS
from threading import Lock
import uuid
import github_checks_helper as ghChecks
from models import database, Execution
import matplotlib.pyplot as plt
import io
import base64
import re
from collections import Counter

app = Flask(__name__)
CORS(app, origins=["*"], supports_credentials=True)
app.config["SQLALCHEMY_DATABASE_URI"] = "postgresql://postgres@localhost:5432/postgres"
database.init_app(app)
socketio = SocketIO(app, cors_allowed_origins="*")
REPO_DIRECTORY = "/tmp/repos"

breakpoints_map = {}
bash_sessions = {}
debug_started_flags = {}
collected_logs = {}
flush_threads_started = set()
paused_flags = {} 
resume_locks = {}


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
        
        # We only want pull request events to get processed - otherwise ignore
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

        # Skip builds for internal system repository
        if repo_title == "AadamYB/final-year-project":
            log(f"⚙️ Internal repo push detected for {repo_title} — skipping.")
            return json.dumps({"status": "ignored"}), 200
        
        build_id = generate_build_id(repo_title) # KEY AS THIS IS PASSED TO EVERYTHING


        log(f"🔧 Build session started with ID: {build_id}", tag="debug", build_id=build_id)

        if event_type == "pull_request":
            pr = event["pull_request"]
            pr_branch = pr.get("head", {}).get("ref")
            pr_number = pr.get("number")
            pr_title = pr.get("title")

            # Start by emitting to socket so the frontend can pick up correct details
            socketio.emit("build-started", {
                "build_id": build_id,
                "repo_title": repo_title,
                "pr_name": pr_title or f"PR#{pr_number}",
                "status": "Pending",
                "timestamp": datetime.now(timezone.utc).astimezone().isoformat()
            })
            execution = Execution(
                id=build_id,
                repo_title=repo_title,
                pr_name=pr_title or f"PR#{pr_number}",
                branch=pr_branch,
                timestamp=datetime.now(timezone.utc).astimezone(),
                status="Pending",
                breakpoints={}
            )
            database.session.add(execution)
            database.session.commit()

            if build_id not in flush_threads_started: #TODO: should we get rid of the other one in get execution? - will try removing this...
                flush_threads_started.add(build_id)
                threading.Thread(target=periodically_flush_logs, args=(build_id,), daemon=True).start()

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
                configure_breakpoints_from_ci(ci_config, build_id)

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
                    end_time = datetime.now(timezone.utc).astimezone()
                    execution.duration = end_time - execution.timestamp
                    # execution.active_stage = None - does this get rid of the last active stage causing the default to be setup?
                if execution and build_id in collected_logs:
                    execution.logs = "\n".join(collected_logs[build_id])
                    database.session.commit()

            except Exception as e:
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
    
    if build_id in collected_logs:
        execution.logs = "\n".join(collected_logs[build_id])
        database.session.commit()

    return {
        "id": execution.id,
        "repo_title": execution.repo_title,
        "pr_name": execution.pr_name,
        "branch": execution.branch,
        "timestamp": execution.timestamp.isoformat(),
        "status": execution.status,
        "logs": execution.logs or "",
        "active_stage": execution.active_stage or "",
        "is_paused": execution.is_paused or False,
        "pause_stage": execution.pause_stage,
        "pause_type": execution.pause_type,
        "breakpoints": execution.breakpoints or {} ,
        **({"duration": str(execution.duration)} if execution.duration else {}) 
    }

@app.route("/executions", methods=["GET"])
def get_all_executions():
    range_val = request.args.get("range")
    query = Execution.query.order_by(Execution.timestamp.desc())
    if range_val:
        query = filter_by_range(query, range_val)
    executions = query.all()

    data = []
    for e in executions:
        duration_str = str(e.duration) if e.duration else None
        data.append({
            "id": e.id,
            "status": e.status,
            "repo_title": e.repo_title,
            "pr_name": e.pr_name,
            "date": e.timestamp.strftime("%d/%m/%y"),
            "time": e.timestamp.strftime("%H:%M"),
            "duration": duration_str 
        })
    return json.dumps(data)

@app.route("/executions-with-stages", methods=["GET"])
def get_all_executions_with_stage_status():
    range_val = request.args.get("range")
    query = Execution.query.order_by(Execution.timestamp.desc())
    if range_val:
        query = filter_by_range(query, range_val)
    executions = query.all()

    STAGES = ["setup", "build", "test"]
    data = []

    for e in executions:
        duration_str = str(e.duration) if e.duration else None
        stage_status = []

        logs = (e.logs or "").lower()
        status = e.status.lower()
        active_stage = (e.active_stage or "").lower()

        current_index = STAGES.index(active_stage) if active_stage in STAGES else -1

        for i, stage in enumerate(STAGES):
            name = stage.capitalize()
            state = "pending"

            if i < current_index:
                state = "success"
            elif i == current_index:
                if status == "pending":
                    state = "active"
                elif status == "failed":
                    state = "failed"
                else:
                    state = "success"
            elif status == "failed" and active_stage == stage:
                state = "failed"
            elif status == "passed":
                state = "success"

            # Only add stages that were reached or relevant
            if state != "pending":
                stage_status.append({"name": name, "status": state})

        data.append({
            "id": e.id,
            "status": e.status,
            "pr_name": e.pr_name,
            "date": e.timestamp.strftime("%d/%m/%y"),
            "time": e.timestamp.strftime("%H:%M"),
            "duration": duration_str,
            "stage_status": stage_status
        })

    return json.dumps(data)

@app.route("/dashboard-metrics", methods=["GET"])
def get_dashboard_metrics():
    range_val = request.args.get("range")
    query = Execution.query
    if range_val:
        query = filter_by_range(query, range_val)
    executions = query.all()

    total_builds = len(executions)
    failed_builds = [e for e in executions if e.status.lower() == "failed"]
    passed_builds = [e for e in executions if e.status.lower() == "passed"]
    pending_builds = [e for e in executions if e.status.lower() == "pending"]

    num_failed = len(failed_builds)
    num_passed = len(passed_builds)
    num_pending = len(pending_builds)

    failure_rate = (num_failed / total_builds) * 100 if total_builds else 0

    avg_duration_seconds = sum(
        e.duration.total_seconds() for e in executions if e.duration
    ) / len([e for e in executions if e.duration]) if executions else 0

    avg_duration_minutes = round(avg_duration_seconds / 60)

    pull_requests = len(set(e.pr_name for e in executions if e.pr_name))
    releases = 0   # TODO: dynamically compute this when we have logic that works on the deploymemt - post submission work

    return {
        "total_builds": total_builds,
        "passed_builds": num_passed,
        "failed_builds": num_failed,
        "active_builds": num_pending,
        "failure_rate": round(failure_rate, 1),
        "avg_build_time": avg_duration_minutes,
        "pull_requests": pull_requests,
        "releases": releases
    }

@app.route("/dashboard-error-chart", methods=["GET"])
def error_type_chart():
    range_val = request.args.get("range")
    query = Execution.query.filter(Execution.status == "Failed")
    if range_val:
        query = filter_by_range(query, range_val)
    executions = query.all()
    error_counter = Counter()

    for e in executions:
        logs = e.logs or ""
        lines = logs.splitlines()

        found_error = None

        for line in lines:
            if "❌" not in line and "ERROR" not in line.upper():
                continue

            lower = line.lower()

            if "undefined-variable" in lower or "undefined variable" in lower:
                found_error = "Undefined Variable"
            elif "pylint" in lower or "your code has been rated at" in lower:
                found_error = "Lint Error"
            elif "would reformat" in lower or "black" in lower:
                found_error = "Format Error"
            elif "assert" in lower and "==" in lower:
                found_error = "Assertion Error"
            elif "traceback" in lower or "exception:" in lower:
                found_error = "Runtime Error"
            elif "exit code" in lower or re.search(r"exit code \d+", lower):
                found_error = "Subprocess Error"
            elif "syntaxerror" in lower:
                found_error = "Syntax Error"
            elif "test" in lower and ("failed" in lower or "failure" in lower):
                found_error = "Test Failure"

            if found_error:
                break  # stop after first match

        if not found_error:
            found_error = "Unknown Error"

        error_counter[found_error] += 1

    if not error_counter:
        error_counter["No Errors Detected"] = 0

    fig, ax = plt.subplots()
    ax.bar(error_counter.keys(), error_counter.values())
    ax.set_title("Common Pipeline Errors")
    ax.set_ylabel("Occurrences")
    ax.set_xlabel("Error Type")

    buf = io.BytesIO()
    plt.tight_layout()
    plt.savefig(buf, format="png")
    plt.close(fig)
    buf.seek(0)

    img_base64 = base64.b64encode(buf.read()).decode("utf-8")
    buf.close()

    return {"image": img_base64}

@app.route("/pipeline-config/<repo_name>", methods=["GET"])
def get_pipeline_config(repo_name):
    branch = request.args.get("branch", "main")  # fallback to 'main' if not provided - but it should always be provided as we save it to the db?
    repo_path = os.path.join(REPO_DIRECTORY, repo_name)

    # Make sure the repo exists
    if not os.path.exists(repo_path):
        return {"error": "Repo not found"}, 404

    try:
        # Checkout the correct branch
        subprocess.run(["git", "-C", repo_path, "fetch", "origin"], check=True)
        subprocess.run(["git", "-C", repo_path, "checkout", branch], check=True)
        subprocess.run(["git", "-C", repo_path, "reset", "--hard", f"origin/{branch}"], check=True)
    except subprocess.CalledProcessError as e:
        return {"error": f"Failed to checkout branch: {branch}"}, 500

    # Now check if .ci.yml exists
    ci_path = os.path.join(repo_path, ".ci.yml")
    if not os.path.exists(ci_path):
        return {"error": ".ci.yml not found"}, 404

    with open(ci_path, "r") as f:
        content = f.read()
    return {"content": content}

@app.route("/pipeline-config/<repo_name>", methods=["POST"])
def save_pipeline_config(repo_name):
    data = request.json
    yaml_content = data.get("content")

    if not yaml_content:
        return {"error": "No content provided"}, 400

    local_repo_path = os.path.join(REPO_DIRECTORY, repo_name)
    ci_file_path = os.path.join(local_repo_path, ".ci.yml")

    os.makedirs(local_repo_path, exist_ok=True)

    with open(ci_file_path, "w") as file:
        file.write(yaml_content)

    try:
        current_branch = subprocess.check_output(["git", "-C", local_repo_path, "rev-parse", "--abbrev-ref", "HEAD"],text=True).strip()

        subprocess.check_output(["git", "-C", local_repo_path, "add", ".ci.yml"])
        
        status = subprocess.check_output(["git", "-C", local_repo_path, "status", "--porcelain"], text=True).strip()
        if not status:
            return {"status": "no changes"}  # No changes to commit

        subprocess.check_output(["git", "-C", local_repo_path, "commit", "-m", "🔧 Update .ci.yml via pipeline configurator"])
        subprocess.check_output(["git", "-C", local_repo_path, "push", "origin", current_branch])
    except subprocess.CalledProcessError as e:
        return {"error": f"Git push failed: {e.output.decode()}"}, 500

    return {"status": "success"}

@socketio.on('connect')
def handle_connect():
    log("🛜 WebSocket client connected ✅")

    executions = Execution.query.all()
    for execution in executions:
        if execution.breakpoints:
            breakpoints_map[execution.id] = execution.breakpoints
            socketio.emit("pause-configured", {"breakpoints": execution.breakpoints, "build_id": execution.id}, to=request.sid)
    
        if execution.is_paused and execution.pause_stage and execution.pause_type:
            if not paused_flags.get(execution.id):
                paused_flags[execution.id] = True
                log(f"🔁 Detected paused state for {execution.id} - resuming...", tag="debug", build_id=execution.id)
                threading.Thread(target=lambda: resume_pipeline_with_context(execution.id), daemon=True).start()

@socketio.on('start-debug')
def start_debug_session(data):
    repo = data.get("repo")
    build_id = data.get("build_id")

    session = bash_sessions.get(build_id)
    if session and session["process"].poll() is not None:
        log(f"♻️ Cleaning up dead session for {build_id}", tag="debug", build_id=build_id)
        bash_sessions.pop(build_id, None)
        debug_started_flags.pop(build_id, None)

    if debug_started_flags.get(build_id):
        log(f"🔁 Re-attaching debug session for {build_id}", tag="debug", build_id=build_id)
        threading.Thread(target=listen_to_bash, args=(build_id, repo), daemon=True).start()
        return

    debug_started_flags[build_id] = True

    execution = Execution.query.get(build_id)
    if execution and execution.status in {"Passed", "Failed"}:
        log(f"🕰 Replaying debug session for old build: {build_id}", tag="debug", build_id=build_id)
    elif not paused_flags.get(build_id, False):
        log("⛔️ Ignoring debug start: not paused, not replay, and no active session", tag="debug", build_id=build_id)
        return

    log(f"🐞 STARTING LIVE DEBUGGING SESSION 🪲 for {repo}", tag="debug", build_id=build_id)

    container_name = f"{build_id.lower()}-container"
    log(f"🪛 Using container: {container_name}", tag="debug", build_id=build_id)

    process = subprocess.Popen(
        ["docker", "exec", "-i", container_name, "bash"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1
    )

    bash_sessions[build_id] = {
        "process": process,
        "stdin": process.stdin,
        "stdout": process.stdout,
        "cwd": "~",
        "lock": Lock()
    }

    socketio.emit("debug-session-started", {"build_id": build_id})
    threading.Thread(target=listen_to_bash, args=(build_id, repo), daemon=True).start()

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
    build_id = data.get('build_id')
    breakpoints = data.get('breakpoints')

    expected_stages = {"setup", "build", "test"}
    expected_keys = {"before", "after"}

    if not isinstance(breakpoints, dict):
        log("❌ ERROR! Invalid breakpoint update: not a dict!", build_id=build_id)
        return

    for stage, points in breakpoints.items():
        if stage not in expected_stages or not isinstance(points, dict):
            log(f"❌ ERROR! Invalid structure in breakpoint: {stage}", build_id=build_id)
            return
        for key in expected_keys:
            if key not in points or not isinstance(points[key], bool):
                log(f"❌ ERROR! Invalid breakpoint type for {stage}.{key}", build_id=build_id)
                return

    # Save updated breakpoints
    breakpoints_map[build_id] = breakpoints
    log(f"✅ Breakpoints updated to: {breakpoints}", tag="debug", build_id=build_id)

    execution = Execution.query.get(build_id)
    if execution:
        execution.breakpoints = breakpoints
        database.session.commit()
    socketio.emit("breakpoints-updated", {"breakpoints": breakpoints})

@socketio.on('console-command')
def handle_console_command(data):
    command = data.get('command')
    repo_title = data.get('repoTitle')
    build_id = data.get('buildId')

    execution = Execution.query.get(build_id)
    if not paused_flags.get(build_id, False) and execution and execution.status in {"Passed", "Failed"}:
        emit('console-output', {'output': '⛔️ Debug console is only available during a paused or active debug session.'})
        return

    if not command or not repo_title:
        emit('console-output', {'output': '❌ ERROR: Missing command or repo title'})
        return

    container_name = re.sub(r'[^a-zA-Z0-9_\-]', '', build_id).lower() + "-container"
    docker_command = f'docker exec -i {container_name} /bin/bash -c "{command}"'

    socketio.emit('console-output', {'output': f"📟 Executing: {command}"})

    try:
        process = subprocess.Popen(
            docker_command,
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )

        # Emit standard output
        for line in iter(process.stdout.readline, ''):
            if line.strip():
                socketio.emit('console-output', {'output': line.strip()})

        # Emit standard error
        for err_line in iter(process.stderr.readline, ''):
            if err_line.strip():
                socketio.emit('console-output', {'output': f"❌ {err_line.strip()}"})

        process.stdout.close()
        process.stderr.close()
        process.wait()

        if process.returncode == 0:
            socketio.emit('console-output', {'output': '✅ Command finished successfully'})
        else:
            socketio.emit('console-output', {'output': f"❌ Command exited with code {process.returncode}"})
    except Exception as e:
        socketio.emit('console-output', {'output': f"❌ Exception: {str(e)}"})

@socketio.on('pause')
def handle_pause(data):
    build_id = data.get('build_id')
    paused_flags[build_id] = True
    log("⏸️ Pause signal received from frontend! Pausing pipeline...", tag="debug", build_id=build_id)

    execution = Execution.query.get(build_id)
    if execution:
        execution.is_paused = True
        database.session.commit()

@socketio.on('resume')
def handle_resume(data=None):
    build_id = None
    if data and isinstance(data, dict):
        build_id = data.get('build_id')

    if not build_id:
        log("❌ ERROR! Resume called with no build_id!", tag="resume")
        return

    paused_flags.pop(build_id, None)
    log(f"🟢 Resume signal received! Continuing pipeline...", tag="debug", build_id=build_id)
    threading.Thread(target=lambda: resume_pipeline_with_context(build_id), daemon=True).start()

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
    timestamp = datetime.now(timezone.utc).astimezone().strftime("%Y-%m-%d %H:%M:%S")
    formatted_msg = f"[{timestamp}] {'[{}] '.format(tag.upper()) if tag else ''}{message}"

    print(formatted_msg)
    socketio.emit('log', {'log': formatted_msg, 'build_id': build_id})

    if not build_id or not has_app_context():
        return

    # Don't log to DB for replayed or finalized builds
    execution = Execution.query.get(build_id)
    if execution and execution.status != "Pending":
        return  # Skip logging for passed/failed builds to avoid overwriting

    if build_id not in collected_logs:
        collected_logs[build_id] = []

    collected_logs[build_id].append(formatted_msg)

    if build_id not in flush_threads_started:
        flush_threads_started.add(build_id)
        threading.Thread(target=periodically_flush_logs, args=(build_id,), daemon=True).start()


def clone_or_pull(repo_url, local_repo_path, repo_title, build_id, branch):
    """ Clones a GitHub repository to a local directory or
        Pulls latest changes from the repository """
    
    socketio.emit('active-stage-update', {'stage': 'setup'})
    update_active_stage(build_id, "setup")
    pause_execution('setup', 'before', build_id, repo_title)   # Can optionally pause a pileline before executing command

    if not os.path.exists(local_repo_path):
        log(f"🔄 Cloning {repo_url}")
        cmd = f"git clone {repo_url} {local_repo_path}"
        run_command_with_stream_output(cmd, build_id, tag="clone")
    else:
        log(f"🔁 Pulling latest changes in {local_repo_path}")
        cmd = (
            f"git -C {local_repo_path} fetch origin {branch} && "
            f"git -C {local_repo_path} reset --hard origin/{branch}"
        )
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
    update_active_stage(build_id, "build")
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
    update_active_stage(build_id, "test")
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

    if process.returncode != 0:
        raise Exception(f"❌ Test stage failed failed!\n{full_output}")

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
    """ Reads the data from the ci_config variable and maps that to the breakpoint dictionary """
    breakpoints = {
        "setup": {"before": ci_config.get("pause_before_clone", False), "after": ci_config.get("pause_after_clone", False)},
        "build": {"before": ci_config.get("pause_before_build", False), "after": ci_config.get("pause_after_build", False)},
        "test": {"before": ci_config.get("pause_before_test", False), "after": ci_config.get("pause_after_test", False)},
    }
    breakpoints_map[build_id] = breakpoints

    execution = Execution.query.get(build_id)
    if execution:
        execution.breakpoints = breakpoints
        database.session.commit()

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
        log(f"⛔️ ERROR during [{tag}] stage. ❌ Exit Code: {process.returncode}", tag="error", build_id=build_id)
        raise Exception(f"Stage [{tag}] failed with exit code {process.returncode}")
    
def update_active_stage(build_id, stage):
    """ Updates the active stage of a pipeline execution in the database - better 
        tracking in case page refreshes and components re-mount and lose current state """

    execution = Execution.query.get(build_id)
    if execution:
        execution.active_stage = stage
        database.session.commit()

def get_resume_lock(build_id):
    """ Retrieves or creates a thread-safe lock object for a given build_id """

    if build_id not in resume_locks:
        resume_locks[build_id] = Lock()
    return resume_locks[build_id]

def resume_pipeline_with_context(build_id):
    """ Resumes the pipeline within an application context for a 
        specific build - prevents Run-time error(not catastrophic) """

    with get_resume_lock(build_id):
        with app.app_context():
            resume_pipeline(build_id)

def resume_pipeline(build_id):
    """ Handles resuming a pipeline execution from paused state based on the stage and timing(when-[bef/aft]) """

    execution = Execution.query.get(build_id)
    if not execution:
        log(f"❌ Cannot resume: build {build_id} not found.")
        return

    local_repo_path = os.path.join(REPO_DIRECTORY, execution.repo_title.replace("/", "_"))
    stage = execution.pause_stage
    when = execution.pause_type
    repo_title = execution.repo_title

    if not stage or not when:
        log("⚠️ Cannot resume: pause_stage or pause_type is None", tag="resume", build_id=build_id)
        return

    log(f"▶️ Resuming pipeline from {stage.upper()} ({when.upper()})...", tag="resume", build_id=build_id)

    try:
        ci_config = load_ci_config(local_repo_path, build_id)

        if stage == "setup":
            if when == "before":
                # TODO: May want to store pr_branch in Execution if needed here - for now the placeholder will do though
                clone_or_pull(repo_title, local_repo_path, repo_title, build_id, "<branch>")
                checkout_branch(local_repo_path, "<branch>", build_id)
                if ci_config.get("lint", True):
                    lint_project(local_repo_path, build_id)
                if ci_config.get("format", True):
                    format_project(local_repo_path, build_id)
                build_project(local_repo_path, repo_title, build_id)
                run_tests(local_repo_path, repo_title, build_id)
            elif when == "after":
                if ci_config.get("lint", True):
                    lint_project(local_repo_path, build_id)
                if ci_config.get("format", True):
                    format_project(local_repo_path, build_id)
                build_project(local_repo_path, repo_title, build_id)
                run_tests(local_repo_path, repo_title, build_id)

        elif stage == "build":
            if when == "before":
                build_project(local_repo_path, repo_title, build_id)
                run_tests(local_repo_path, repo_title, build_id)
            elif when == "after":
                run_tests(local_repo_path, repo_title, build_id)

        elif stage == "test":
            if when == "before":
                run_tests(local_repo_path, repo_title, build_id)
            elif when == "after":
                log("✅ All pipeline stages already completed.", tag="resume", build_id=build_id)
                return
            
        else:
            log(f"⚠️ Cannot resume from unknown stage '{stage}'", tag="resume", build_id=build_id)
            return

        execution.is_paused = False
        execution.pause_stage = None
        execution.pause_type = None
        execution.status = "Passed"
        database.session.commit()

        socketio.emit("build-finished", {
            "build_id": build_id,
            "status": "Passed"
        })

    except Exception as e:
        finalize_failed_build(build_id, repo_title, None, e)

def pause_execution(stage, when, build_id, repo_title):
    """ Pauses the pipeline at the specified stage and time ('before' or 'after'), 
        allowing users to modify their breakpoints or to use the debug console.      """

    breakpoints = breakpoints_map.get(build_id, {})
    if not breakpoints.get(stage, {}).get(when, False):
        return

    log(f"🚨 Pausing at {stage.upper()} ({when.upper()}) ... Waiting for resume command!", tag="debug", build_id=build_id)
    paused_flags[build_id] = True

    execution = Execution.query.get(build_id)
    if execution:
        execution.is_paused = True
        execution.pause_stage = stage
        execution.pause_type = when
        database.session.commit()

    ensure_debug_session_started(build_id, repo_title)
    socketio.emit('allow-breakpoint-edit', {"stage": stage.upper(), "when": when.upper()})
    log("🔓 User can now edit future breakpoints during pause!", tag="debug", build_id=build_id)

    while paused_flags.get(build_id, False):
        time.sleep(0.5)


def ensure_debug_session_started(build_id, repo):
    """ Ensures a live debug session is running during a paused pipeline; starts one if not. """

    if not paused_flags.get(build_id, False):
        return
    
    session = bash_sessions.get(build_id)
    if session is None or session["process"].poll() is not None:
        start_debug_session({"repo": repo, "build_id": build_id})

def generate_build_id(repo_title: str) -> str:
    """ Generates a unique build uuid using timestamp and a shortened UUID based on the repository title. """

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
        log(f"📬 Check run updated: {conclusion.upper()}", tag="FINISHED", build_id=build_id)
    except Exception as e:
        log(f"⚠️ Failed to update check run: {e}", build_id=build_id)

def finalize_failed_build(build_id, repo_title, check_run_id, exception):
    """ Helper that updates the execution in the database when the pipeline execution fails """
    log(f"❌ ERROR! Pipeline failed mid-execution: {exception}", build_id=build_id)

    if check_run_id:
        update_github_check(repo_title, check_run_id, "failure", str(exception), build_id=build_id)

    if build_id:
        execution = Execution.query.get(build_id)
        if execution:
            execution.status = "Failed"
            end_time = datetime.now(timezone.utc).astimezone()
            execution.duration = end_time - execution.timestamp
        if execution and build_id in collected_logs:
            execution.logs = "\n".join(collected_logs[build_id])
            database.session.commit()

        socketio.emit("build-finished", {
            "build_id": build_id,
            "status": "Failed"
        })

def listen_to_bash(build_id, repo):
    """ Streams real-time output from the container's bash session during a debug session.
        and formats each line with a mock shell prompt and emits it via WebSocket. """
    
    session = bash_sessions.get(build_id)
    if not session:
        return

    process = session["process"]
    stdout = session["stdout"]
    ascii_shown = False

    # TODO: Current Working Directory needs to be shown in the prompt - not working!!!!!
    for line in stdout:
        if line:
            user = repo.split("/")[-1]
            ip = "35.177.242.182"
            cwd = session["cwd"]
            prompt = f"\n{user}@{ip} {cwd} ~$ "

            output = (DEBUG_ASCII_ART + "\n" + line) if not ascii_shown else line
            ascii_shown = True

            socketio.emit("console-output", {"output": output + prompt})

    log(f"‼️ Debug session exited for {build_id}", tag="debug", build_id=build_id)

def periodically_flush_logs(build_id):
    """ Flushes collected logs to the database if new lines are added. Ensures 
        logs are persisted and saved to database during live execution """
    
    with app.app_context():
        previous_log_len = 0
        while build_id in collected_logs:
            time.sleep(0.1)
            current_logs = collected_logs.get(build_id, [])
            if len(current_logs) > previous_log_len:
                execution = Execution.query.get(build_id)
                if execution:
                    execution.logs = "\n".join(current_logs)
                    try:
                        database.session.commit()
                        previous_log_len = len(current_logs)
                    except Exception as e:
                        log(f"⚠️ Could not flush logs: {e}", tag="debug", build_id=build_id)

def filter_by_range(query, range_val):
    now = datetime.utcnow()
    ranges = {
        "15m": now - timedelta(minutes=15),
        "1h": now - timedelta(hours=1),
        "3h": now - timedelta(hours=3),
        "12h": now - timedelta(hours=12),
        "1d": now - timedelta(days=1),
        "7d": now - timedelta(days=7),
    }
    if range_val in ranges:
        return query.filter(Execution.timestamp >= ranges[range_val])
    return query

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
