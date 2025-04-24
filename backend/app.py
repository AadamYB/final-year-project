from flask import Flask, request, json
import os
import subprocess

app = Flask(__name__)
REPO_DIRECTORY = '/tmp/repos'

@app.route('/')
def api_root():
    return "Server is running and receiving events!"

@app.route('/events', methods=['POST'])
def api_events():
    event = request.json

    if not event:
        return json.dumps({"message": "No event data received"}), 400

    repo = event.get('repository', {})
    repo_title = repo.get('full_name')
    repo_url = repo.get('clone_url')
    local_repo_path = os.path.join(REPO_DIRECTORY, repo_title.replace("/", "_"))

    if 'pull_request' in event:
        pr = event['pull_request']
        pr_branch = pr.get('head', {}).get('ref')
        pr_number = pr.get('number')

        print(f"Received PR event for PR#{pr_number} in {repo_title} for branch {pr_branch}.")

        if pr_branch and repo_url:

            # First we clone the repository if it does not already exist, if so then pull changes
            clone_or_pull(repo_url, local_repo_path)

            # Then checkout the PR branch
            checkout_branch(local_repo_path, pr_branch)

            # # Trigger Build & Test
            build_project(local_repo_path)
            return json.dumps({"status": "PR processed"}), 200

    elif 'pusher' in event and 'ref' in event:
        push_branch = event.get('ref').split("/")[-1]

        print(f"Received push to {push_branch} in {repo_title}.")

        if repo_url and push_branch:

            clone_or_pull(repo_url, local_repo_path)


            checkout_branch(local_repo_path, push_branch)
            build_project(local_repo_path)
            return json.dumps({"status": "Push processed"}), 200

    print("Unsupported or unknown event.")
    return json.dumps({"message": "Unsupported or unknown event type"}), 400

def clone_or_pull(repo_url, local_repo_path):
    """ Clones a GitHub repository to a local directory and/or 
        Pulls latest changes from the repository"""
    if not os.path.exists(local_repo_path):
        print(f"Cloning {repo_url} into {local_repo_path}")
        subprocess.run(["git", "clone", repo_url, local_repo_path], check=True)
    else:
        print(f"Pulling latest changes in {local_repo_path}")
        subprocess.run(["git", "-C", local_repo_path, "pull"], check=True)

def checkout_branch(local_repo_path, branch_name):
    """ Checkouts the correct branch for the Pull Request"""
    print(f"Checking out branch: {branch_name}")
    subprocess.run(["git", "-C", local_repo_path, "fetch", "origin"], check=True)
    subprocess.run(["git", "-C", local_repo_path, "checkout", branch_name], check=True)

def build_project(local_repo_path):
    """ Builds the project inside a Docker container """
    print(f"Building project in {local_repo_path}")
    dockerfile_path = os.path.join(local_repo_path, "Dockerfile")

    if not os.path.exists(dockerfile_path):
        print(f"❌ ERROR! No Dockerfile found at {dockerfile_path}")
        return

    try:
        subprocess.run(["docker", "build", "-t", "project-image", local_repo_path], check=True)
        print("✅ Hooray! Build Successful!")
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to build the project. Error: {e}")

if __name__ == '__main__':
    os.makedirs(REPO_DIRECTORY, exist_ok=True)
    app.run(debug=True, host='0.0.0.0', port=5000)