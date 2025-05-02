""" Connect the GitHub App so that we can send build status using REST API """
import jwt
import time
import requests
from pathlib import Path

APP_ID = "1237035"
GITHUB_API_URL = "https://api.github.com"
PRIVATE_KEY_PATH = Path.home() / ".ssh/github-app.pem"

def generate_jwt(app_id, private_key_path):
    with open(private_key_path, "r") as f:
        private_key = f.read()

    payload = {
        "iat": int(time.time()),
        "exp": int(time.time()) + (10 * 60),
        "iss": app_id
    }

    return jwt.encode(payload, private_key, algorithm="RS256")

def get_installation_id(repo_full_name, jwt_token):
    headers = {
        "Authorization": f"Bearer {jwt_token}",
        "Accept": "application/vnd.github+json"
    }

    res = requests.get(f"{GITHUB_API_URL}/repos/{repo_full_name}/installation", headers=headers)
    res.raise_for_status()
    return res.json()["id"]

def get_installation_token(installation_id, jwt_token):
    headers = {
        "Authorization": f"Bearer {jwt_token}",
        "Accept": "application/vnd.github+json"
    }

    res = requests.post(
        f"{GITHUB_API_URL}/app/installations/{installation_id}/access_tokens",
        headers=headers
    )
    res.raise_for_status()
    return res.json()["token"]

def create_check(repo_full_name, commit_sha, name, status, conclusion=None, output=None):
    jwt_token = generate_jwt(APP_ID, PRIVATE_KEY_PATH)
    installation_id = get_installation_id(repo_full_name, jwt_token)
    access_token = get_installation_token(installation_id, jwt_token)

    headers = {
        "Authorization": f"token {access_token}",
        "Accept": "application/vnd.github+json"
    }

    body = {
        "name": name,
        "head_sha": commit_sha,
        "status": status
    }

    if status == "completed":
        body["conclusion"] = conclusion or "success"
        body["completed_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    elif status == "in_progress":
        body["started_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

    if output:
        body["output"] = output

    url = f"{GITHUB_API_URL}/repos/{repo_full_name}/check-runs"
    res = requests.post(url, json=body, headers=headers)
    res.raise_for_status()
    return res.json()

def update_check(repo_full_name, check_run_id, status, conclusion=None, output=None):
    jwt_token = generate_jwt(APP_ID, PRIVATE_KEY_PATH)
    installation_id = get_installation_id(repo_full_name, jwt_token)
    access_token = get_installation_token(installation_id, jwt_token)

    headers = {
        "Authorization": f"token {access_token}",
        "Accept": "application/vnd.github+json"
    }

    body = {
        "status": status
    }

    if status == "completed":
        body["conclusion"] = conclusion or "success"
        body["completed_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

    if output:
        body["output"] = output

    url = f"{GITHUB_API_URL}/repos/{repo_full_name}/check-runs/{check_run_id}"
    res = requests.patch(url, json=body, headers=headers)
    res.raise_for_status()
    return res.json()