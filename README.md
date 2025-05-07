# Final-Year-Project

## CI/CD System with Live Debugging Capabilities

This project is a custom Continuous Integration / Continuous Deployment (CI/CD) system built for real-time development workflows. It supports code linting, formatting, building, and testing — and uniquely, it provides **live debugging sessions via a web interface**.  

Developers can pause pipelines at defined breakpoints and access an interactive shell directly inside the running Docker container to inspect and debug builds live.

---

## Features

- Automatic builds triggered by GitHub push or pull request events
- Steps include:
  - Cloning into Repo and checking out feature branch
  - Linting (via `pylint`)
  - Formatting (via `black`)
  - Docker-based build & containerization
  - Pytest-driven testing
  - Custom post-build commands
- 🐞 **Live debugging** interface with a full Bash shell in running containers
- 🔗 GitHub Check Run status updates (success/failure per commit)
- ⚙️ Configurable `.ci.yml` to define pipeline behavior per repository

---

## Technologies Used

- **Flask** + **Flask-SocketIO** (Python backend + WebSockets)
- **Docker** for isolated build environments
- **Black / Pylint / Pytest** for code formatting, static analysis and testing
- **Gunicorn + Eventlet** for production server
- **GitHub Webhooks** for CI triggers

---

## Getting Started

### 1. Connect Your Repository

Set up a webhook in your GitHub repository:

**URL:**  http://35.177.242.182:5000/events

In your repo settings:
  • Go to Settings → Webhooks → Add webhook
  • Payload URL: http://35.177.242.182:5000/events
  • Content type: application/json
  • Events: Select push and pull_request

**Content type:**  
`application/json`

**Events to trigger:**  
- `push`
- `pull_request`

---

### 2. Add a `.ci.yml` File (Optional)

Place a `.ci.yml` in the root of your repository to customize pipeline stages.

Here’s an example of the template to use:

```yaml
lint: true
format: true
build: true
test: true
run_commands:
  - echo "Congratulations! Custom command ran!"
pause_before_clone: false
pause_after_clone: false
pause_before_build: false
pause_after_build: false
pause_before_test: false
pause_after_test: false
```

---

### 3. Add a .pylintrc File

Add a .pylintrc configuration to your repo to define linting behavior. Here’s a recommended template »  
https://github.com/saminarp/rwar/blob/main/.pylintrc

---

## 🐞 Live Debugging

If the CI pipeline hits a pause breakpoint, a WebSocket connection opens, and the user can:
  • View live logs  
  • Start an interactive shell inside the container  
  • Run shell commands and inspect files  
  • Resume pipeline execution at any time

---

## Architecture Overview

```
GitHub Repo
   ↓ Push / PR Event
Webhook Trigger → Flask Backend
   → Clone / Pull Repo
   → Run CI Stages (lint, build, test...)
   → Docker Container for Build/Test
   → GitHub Check API (status updates)
   → WebSocket for Live Debug Shell
```

---

## Deployment Notes

This system is hosted on an EC2 instance (Ubuntu), running:

  • Python 3.13  
  • Docker  
  • Gunicorn with Eventlet worker  
  • Port 5000 exposed for HTTP & WebSocket traffic

---

## About

**Author:** AadamYB  
**Contact:** aadam.y.boakye@gmail.com
