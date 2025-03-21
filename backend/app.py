from flask import Flask, request, json
import requests
import os
import subprocess

app = Flask(__name__)

REPO_DIRECTORY = '/tmp/repos'

@app.route('/')
def api_root():
    return "Server is running and receiving events!"

@app.route('/events', methods = ['POST'])
def api_events():
    event = request.json

    if event:
        pr = event.get('pull_request', {})
        repo_title = event.get('repository', {}).get('full_name')
        pr_branch = pr.get('head', {}).get('ref')
        pr_number = pr.get('number')
        repo_url = event.get('repository', {}).get('clone_url')

        print(f"Received PR event for PR#{pr_number} in {repo_title} for branch {pr_branch}.")

        # First we clone the repository if it does not already exist, if so then pull changes
        local_repo_path = os.path.join(REPO_DIRECTORY, repo_title.replace("/", "_"))
        
        if not os.path.exists(local_repo_path):
            clone_repo(repo_url, local_repo_path)
        else:
            pull_changes(local_repo_path)

        # Then checkout the PR branch
        checkout_pr_branch(local_repo_path, pr_branch)

        # # Step 3: Trigger Build & Test
        build_project(local_repo_path)
        # run_tests(local_repo_path)

        return json.dumps({"status": "PR processed"}), 200

    return json.dumps({"message": "No event data received"}), 400


def clone_repo(repo_url, local_repo_path):
    """ Clones a GitHub repository to a local directory """
    print(f"Cloning {repo_url} into {local_repo_path}")
    subprocess.run(["git", "clone", repo_url, local_repo_path], check=True)

def pull_changes(local_repo_path):
    """ Pulls latest changes from the repository """
    print(f"Pulling latest changes in {local_repo_path}")
    subprocess.run(["git", "-C", local_repo_path, "pull"], check=True)

def checkout_pr_branch(local_repo_path, pr_branch):
    """ Checkouts the correct branch for the Pull Request"""
    print(f"Checking out PR branch: {pr_branch}")
    subprocess.run(["git", "-C", local_repo_path, "fetch", "origin"], check=True)
    subprocess.run(["git", "-C", local_repo_path, "checkout", pr_branch], check=True)

def build_project(local_repo_path):
    """ Builds the project inside a Docker container """
    print(f"Building project in {local_repo_path}")

    if not os.path.exists("Dockerfile"):
        print("❌ ERROR! No Dockerfile found in the repository.")
        print("⚠️ Please add a Dockerfile to the root of the repository to build the project.")
        return
    
    try:
        subprocess.run(["docker", "build", "-t", "project-image", local_repo_path], check=True)
        print("✅ Hooray! Build Successful!")
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to build the project. Error: {e}")

def run_tests(local_repo_path):
    """ Runs tests inside the Docker container """
    print(f"Running tests for {local_repo_path}")
    subprocess.run(["docker", "run", "--rm", "project-image", "pytest"], check=True)


if __name__ == '__main__':
    if not os.path.exists(REPO_DIRECTORY):
        os.makedirs(REPO_DIRECTORY)

    app.run(debug=True, host='0.0.0.0', port=5000)
