# 🤖 ACR_AGENT — AI-Powered Autonomous Code Repair Agent

ACR_AGENT is an AI-powered autonomous DevOps and code-repair platform that analyzes GitHub repositories, detects software issues, uses Gemini AI to generate and apply fixes, validates the changes, and creates a Pull Request with the repaired code.

The system combines a **Next.js web interface**, **FastAPI backend**, **Socket.IO real-time communication**, **Docker-based isolated execution**, **Gemini AI**, and **GitHub API integration** into a single automated workflow.

---

## 📌 Table of Contents

* [Overview](#-overview)
* [Key Features](#-key-features)
* [How ACR_AGENT Works](#-how-acr_agent-works)
* [System Architecture](#-system-architecture)
* [Project Structure](#-project-structure)
* [Technology Stack](#-technology-stack)
* [Core Workflow](#-core-workflow)
* [Frontend](#-frontend)
* [Backend](#-backend)
* [AI Code Repair](#-ai-code-repair)
* [GitHub Integration](#-github-integration)
* [Docker Execution](#-docker-execution)
* [Authentication](#-authentication)
* [Environment Variables](#-environment-variables)
* [Installation](#-installation)
* [Running the Application](#-running-the-application)
* [Using ACR_AGENT](#-using-acr_agent)
* [API](#-api)
* [Real-Time Events](#-real-time-events)
* [Output](#-output)
* [Security](#-security)
* [Troubleshooting](#-troubleshooting)
* [Future Enhancements](#-future-enhancements)

---

# 🎯 Overview

Modern software projects can contain syntax errors, build failures, type issues, logical bugs, and other problems that require developers to manually investigate and repair.

ACR_AGENT automates this process.

Instead of manually:

1. Cloning a repository
2. Installing dependencies
3. Running checks
4. Finding the failing files
5. Understanding the error
6. Writing a fix
7. Testing the fix
8. Creating a branch
9. Committing changes
10. Creating a Pull Request

ACR_AGENT performs these steps through an automated agent pipeline.

### High-level flow

```text
GitHub Repository
       │
       ▼
Repository Preparation
       │
       ▼
Code Analysis
       │
       ▼
Error Detection
       │
       ▼
Gemini AI Analysis
       │
       ▼
Automatic Code Fix
       │
       ▼
Validation
       │
       ├── Failed ──► Retry Healing
       │
       ▼
Git Operations
       │
       ▼
Commit + Push
       │
       ▼
Pull Request
```

---

# ✨ Key Features

## 🔍 Automated Repository Analysis

ACR_AGENT accepts a GitHub repository URL and prepares the repository for analysis.

It can detect common project environments including:

* Python
* JavaScript
* TypeScript
* Simple Python projects
* Simple JavaScript projects

---

## 🧠 AI-Powered Code Repair

Gemini AI analyzes:

* Error output
* Relevant source files
* Error location
* Error type
* Existing source code

It then generates structured fixes that can be applied automatically.

---

## 🔄 Iterative Healing

If the first fix does not resolve the detected problem, the system can repeat the:

```text
Analyze
   ↓
Generate Fix
   ↓
Apply Fix
   ↓
Validate
```

cycle until the issue is resolved or the configured retry limit is reached.

---

## 🐳 Isolated Docker Execution

Repository processing is performed inside a Docker worker environment.

This provides an isolated execution environment for:

* Repository cloning
* Dependency installation
* Build checks
* Syntax checks
* AI-based repair
* Git operations

---

## 📡 Real-Time Execution Logs

The frontend communicates with the backend using Socket.IO.

The dashboard can display:

* Current pipeline stage
* Execution logs
* Error messages
* Healing progress
* Completion status
* Final Pull Request information

---

## 🔀 Automated GitHub Pull Requests

After successful repair, ACR_AGENT can:

1. Create a working branch
2. Apply changes
3. Commit changes
4. Check repository ownership
5. Create a fork when required
6. Push the repaired code
7. Create a Pull Request

---

## 📊 Repair Results Dashboard

The frontend provides a dashboard containing:

* Pipeline status
* Repository information
* Execution progress
* Detected issues
* Applied fixes
* Branch information
* Pull Request link
* Execution statistics
* Fix distribution
* Downloadable JSON results

---

# 🏗️ How ACR_AGENT Works

ACR_AGENT follows a multi-stage autonomous pipeline.

```text
┌─────────────────────────┐
│      User Login         │
└────────────┬────────────┘
             │
             ▼
┌─────────────────────────┐
│   Repository URL Input  │
└────────────┬────────────┘
             │
             ▼
┌─────────────────────────┐
│ Repository Preparation  │
│ Clone + Environment     │
└────────────┬────────────┘
             │
             ▼
┌─────────────────────────┐
│     Code Analysis       │
│ Build / Syntax Checks   │
└────────────┬────────────┘
             │
             ▼
        Error Found?
          /      \
        No        Yes
        │          │
        ▼          ▼
      Done    Gemini AI
                  │
                  ▼
             Generate Fix
                  │
                  ▼
              Apply Fix
                  │
                  ▼
              Validate
               /    \
            Pass    Fail
             │       │
             │       └──────► Retry
             ▼
        Git Operations
             │
             ▼
        Commit + Push
             │
             ▼
       Create Pull Request
```

---

# 🏛️ System Architecture

```text
                    ┌──────────────────────┐
                    │      User / Browser  │
                    └──────────┬───────────┘
                               │
                               ▼
                    ┌──────────────────────┐
                    │   Next.js Frontend   │
                    │                      │
                    │ Login                │
                    │ Dashboard            │
                    │ Logs                 │
                    │ Results              │
                    └──────────┬───────────┘
                               │
                     HTTP / Socket.IO
                               │
                               ▼
                    ┌──────────────────────┐
                    │   FastAPI Backend    │
                    │                      │
                    │ API                  │
                    │ Socket.IO            │
                    │ Pipeline Controller  │
                    └──────────┬───────────┘
                               │
                               ▼
                    ┌──────────────────────┐
                    │   Docker Worker      │
                    │                      │
                    │ Repository Prep      │
                    │ Analysis             │
                    │ AI Healing           │
                    │ Git Operations       │
                    └───────┬───────┬──────┘
                            │       │
                ┌───────────┘       └───────────┐
                ▼                               ▼
        ┌───────────────┐               ┌───────────────┐
        │   Gemini AI   │               │    GitHub     │
        │               │               │               │
        │ Error         │               │ Repository    │
        │ Analysis      │               │ Fork          │
        │ Code Fix      │               │ Commit        │
        └───────────────┘               │ Pull Request  │
                                        └───────────────┘
```

---

# 📁 Project Structure

```text
ACR_AGENT/
│
├── backend/
│   ├── main.py
│   ├── worker_entrypoint.py
│   ├── repo_prep_agent.py
│   ├── analysis_agent.py
│   ├── healing_agent.py
│   ├── git_agent.py
│   ├── container_manager.py
│   ├── requirements.txt
│   ├── Dockerfile.worker
│   └── .env
│
├── frontend/
│   ├── app/
│   │   ├── api/
│   │   │   └── auth/
│   │   │       └── [...nextauth]/
│   │   │           └── route.ts
│   │   │
│   │   ├── login/
│   │   │   └── page.tsx
│   │   │
│   │   ├── components/
│   │   │   └── theme-provider.tsx
│   │   │
│   │   ├── layout.tsx
│   │   ├── providers.tsx
│   │   ├── page.tsx
│   │   ├── test/
│   │   │   └── page.tsx
│   │   └── globals.css
│   │
│   ├── components/
│   │   └── ui/
│   │       └── sonner.tsx
│   │
│   ├── lib/
│   │   └── utils.ts
│   │
│   ├── auth.ts
│   ├── middleware.ts
│   ├── package.json
│   ├── tsconfig.json
│   ├── next.config.ts
│   ├── postcss.config.mjs
│   ├── components.json
│   └── .env.local
│
├── .gitignore
└── README.md
```

> The authentication files shown above represent the Google authentication integration being added to the project. The original repository currently contains the core backend and frontend files documented in its source README.

---

# 🧰 Technology Stack

## Frontend

* Next.js
* React
* TypeScript
* Tailwind CSS
* shadcn/ui
* Socket.IO Client
* Recharts
* GSAP
* Lucide React
* Sonner
* next-themes
* Auth.js / NextAuth

The repository currently uses Next.js 16, React 19, Tailwind CSS 4, Socket.IO Client, Recharts, GSAP, and related frontend libraries.

## Backend

* Python
* FastAPI
* Uvicorn
* Python Socket.IO
* Pydantic
* GitPython
* PyGithub
* Docker SDK
* Requests
* aiohttp
* python-dotenv

## AI

* Google Gemini
* `google-genai`

## Infrastructure

* Docker
* Git
* GitHub API

---

# 🔄 Core Workflow

## Stage 1 — Repository Preparation

The repository preparation agent:

1. Receives the repository URL.
2. Clones the repository.
3. Detects the project environment.
4. Installs required dependencies.
5. Prepares the working branch.

The current implementation supports Python and JavaScript/TypeScript project detection.

---

# Stage 2 — Code Analysis

The analysis agent runs appropriate checks based on the detected project.

### Python

Possible checks include:

```bash
python -m compileall
```

### JavaScript / TypeScript

Possible checks include:

```bash
npm run build
```

or:

```bash
bun run build
```

Simple JavaScript files can also be syntax checked with Node.js.

The analysis stage returns the detected failure information and status.

---

# Stage 3 — AI Healing

When an error is detected, the healing agent:

1. Reads the error output.
2. Identifies relevant files.
3. Reads the source code.
4. Sends the required context to Gemini.
5. Receives structured fix information.
6. Validates the response.
7. Applies the generated changes.
8. Sends the repository back for validation.

The current implementation classifies fixes into categories such as:

* LINTING
* SYNTAX
* LOGIC
* TYPE

---

# Stage 4 — Git Operations

After successful repair:

```text
Create / checkout branch
        ↓
Stage changes
        ↓
Commit
        ↓
Check repository ownership
        ↓
Fork if necessary
        ↓
Push changes
        ↓
Create Pull Request
```

The Git agent uses GitHub APIs to manage repository and Pull Request operations.

---

# 🎨 Frontend

The main dashboard provides a user interface for starting and monitoring the repair process.

## Dashboard Capabilities

* Repository URL input
* Retry configuration
* Real-time execution logs
* Pipeline stage tracking
* Repair summary
* Applied-fix details
* Pull Request link
* Execution statistics
* Charts
* JSON result download

These capabilities are present in the current frontend implementation.

---

# 🔐 Authentication

ACR_AGENT uses Google-based authentication for protected access to the application.

### Authentication Flow

```text
User
 │
 ▼
Login Page
 │
 ▼
Continue with Google
 │
 ▼
Google Authentication
 │
 ▼
Authenticated Session
 │
 ▼
ACR_AGENT Dashboard
```

Authentication protects the main application while keeping the existing DevOps dashboard functionality intact.

### Authentication Components

```text
frontend/
├── auth.ts
├── middleware.ts
├── app/
│   ├── login/
│   │   └── page.tsx
│   ├── providers.tsx
│   └── api/
│       └── auth/
│           └── [...nextauth]/
│               └── route.ts
```

---

# 🔑 Environment Variables

## Backend

Create:

```text
backend/.env
```

Example:

```env
GEMINI_API_KEY=your_gemini_api_key
GITHUB_TOKEN=your_github_token
```

The original backend uses Gemini and GitHub credentials for AI repair and GitHub operations.

---

## Frontend

Create:

```text
frontend/.env.local
```

Example:

```env
NEXT_PUBLIC_BACKEND_URL=http://localhost:8000

GOOGLE_CLIENT_ID=your_google_client_id
GOOGLE_CLIENT_SECRET=your_google_client_secret

AUTH_SECRET=your_auth_secret
```

### Security

Never expose:

```text
GEMINI_API_KEY
GITHUB_TOKEN
GOOGLE_CLIENT_SECRET
AUTH_SECRET
```

to the client-side application.

Never commit `.env` or `.env.local` files to GitHub.

---

# 🚀 Installation

## Prerequisites

Install:

* Git
* Node.js
* npm
* Python 3.12
* Docker
* A Google Gemini API key
* A GitHub token
* Google OAuth credentials

---

# 1. Clone the Repository

```bash
git clone https://github.com/SuhasKumarHR/ACR_AGENT.git
cd ACR_AGENT
```

---

# 2. Backend Setup

```bash
cd backend
```

Create a virtual environment:

### Windows

```bash
python -m venv venv
venv\Scripts\activate
```

### Linux / macOS

```bash
python3 -m venv venv
source venv/bin/activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

---

# 3. Configure Backend Environment

Create:

```text
backend/.env
```

Add:

```env
GEMINI_API_KEY=your_gemini_api_key
GITHUB_TOKEN=your_github_token
```

---

# 4. Build the Docker Worker

From the `backend` directory:

```bash
docker build -f Dockerfile.worker -t acr-worker:latest .
```

---

# 5. Frontend Setup

Open another terminal:

```bash
cd frontend
```

Install dependencies:

```bash
npm install
```

Install authentication dependency:

```bash
npm install next-auth
```

---

# 6. Configure Frontend Environment

Create:

```text
frontend/.env.local
```

Add:

```env
NEXT_PUBLIC_BACKEND_URL=http://localhost:8000

GOOGLE_CLIENT_ID=your_google_client_id
GOOGLE_CLIENT_SECRET=your_google_client_secret
AUTH_SECRET=your_auth_secret
```

---

# ▶️ Running the Application

## Terminal 1 — Backend

```bash
cd backend
```

Start the FastAPI / Socket.IO server:

```bash
uvicorn main:socket_app --reload --host 0.0.0.0 --port 8000
```

The backend will be available at:

```text
http://localhost:8000
```

---

## Terminal 2 — Frontend

```bash
cd frontend
npm run dev
```

Open:

```text
http://localhost:3000
```

---

# 🔐 Google Login Flow

When the application starts:

```text
http://localhost:3000
       │
       ▼
 Authentication Check
       │
       ├── Not authenticated
       │          │
       │          ▼
       │       /login
       │          │
       │          ▼
       │   Continue with Google
       │          │
       │          ▼
       │    Google OAuth
       │          │
       │          ▼
       └──────► Dashboard
```

---

# 🧪 Testing Mode

The project also contains a frontend test page for testing the dashboard behavior without connecting to the actual backend.

Run:

```bash
cd frontend
npm run dev
```

Then open:

```text
http://localhost:3000/test
```

This provides a simulated pipeline for frontend testing.

---

# 📡 API

## Health Check

```http
GET /health
```

Used to verify that the backend is running.

---

## Run Pipeline

```http
POST /run
```

Example request:

```json
{
  "repo_url": "https://github.com/username/repository",
  "max_retries": 5
}
```

The backend uses this request to start repository analysis and repair.

---

# 📡 Real-Time Socket Events

The frontend uses Socket.IO for real-time communication.

## Start Agent

```text
start_agent
```

Starts the repository repair pipeline.

---

## Log

```text
log
```

Streams pipeline logs to the frontend.

---

## Completed

```text
completed
```

Returns the final pipeline result.

---

## Fatal Error

```text
error_fatal
```

Reports an unrecoverable pipeline error.

These events correspond to the current backend/frontend communication flow.

---

# 📊 Output

A successful pipeline produces structured information similar to:

```json
{
  "status": "SUCCESS",
  "total_time_minutes": 3.45,
  "fixes_applied": 5,
  "branch": "AI_FIX_BRANCH",
  "pr_link": "https://github.com/user/repository/pull/1",
  "iterations_used": 2,
  "total_failures": 5,
  "commits_count": 5,
  "fixes": [
    {
      "file_path": "src/utils.py",
      "bug_type": "SYNTAX",
      "line_number": 15,
      "explanation": "Syntax issue repaired",
      "commit_message": "Fix syntax issue",
      "status": "Fixed"
    }
  ]
}
```

The actual repository's output model includes pipeline status, timing, applied fixes, branch, Pull Request information, iterations, failures, commits, and detailed fix objects.

---

# 📋 Fix Information

Each detected fix can contain:

| Field            | Description                              |
| ---------------- | ---------------------------------------- |
| `file_path`      | File where the problem was detected      |
| `bug_type`       | Category of the problem                  |
| `line_number`    | Relevant line number                     |
| `explanation`    | Description of the issue/fix             |
| `commit_message` | Commit message generated for the repair  |
| `status`         | Whether the fix was successfully applied |

---

# 🐳 Docker Worker

The worker image provides an isolated environment for running the repair pipeline.

The worker is based on:

```text
python:3.12-slim
```

It includes tools required for:

* Git operations
* Python execution
* Node.js / npm checks
* AI repair
* Repository analysis

The container manager starts the worker, streams its logs, reads the final result, and cleans up the container after execution.

---

# 🔒 Security

ACR_AGENT processes source-code repositories and therefore must protect credentials and repository access.

### Recommended security practices

* Never commit API keys.
* Never commit GitHub tokens.
* Never expose OAuth client secrets to the browser.
* Keep `.env` and `.env.local` out of Git.
* Run untrusted repository code inside isolated containers.
* Validate AI-generated changes before applying them.
* Limit Docker resources where appropriate.
* Validate repository paths and URLs.
* Use minimum required GitHub token permissions.

---

# 🛠️ Troubleshooting

## Backend does not start

Check:

```bash
python --version
```

and:

```bash
pip install -r requirements.txt
```

Also verify that Docker is running.

---

## Frontend cannot connect to backend

Check:

```env
NEXT_PUBLIC_BACKEND_URL=http://localhost:8000
```

Then verify:

```text
http://localhost:8000/health
```

---

## Google Login fails

Verify:

* Google Client ID
* Google Client Secret
* `AUTH_SECRET`
* OAuth authorized origin
* OAuth redirect URI

For local development, the callback URL should be:

```text
http://localhost:3000/api/auth/callback/google
```

---

## Docker worker fails

Check:

```bash
docker images
```

Make sure the worker image exists:

```text
acr-worker:latest
```

If necessary, rebuild:

```bash
docker build -f Dockerfile.worker -t acr-worker:latest .
```

---

## Gemini AI fails

Check:

```env
GEMINI_API_KEY=your_key
```

Make sure the backend environment can access the key.

---

## GitHub Pull Request fails

Check:

```env
GITHUB_TOKEN=your_token
```

and verify that the token has the repository permissions required by your workflow.

---

# 🚀 Future Enhancements

Potential improvements for future versions include:

### Authentication & Users

* User profile management
* Repository history
* Per-user execution history
* Saved repositories
* User-specific configuration

### AI Improvements

* Support for additional AI models
* Better error classification
* Multi-file reasoning
* Test generation
* Regression detection
* AI-generated explanations

### DevOps Improvements

* CI/CD integration
* GitHub Actions integration
* Automated test execution
* Deployment verification
* Multiple repository support
* Scheduled repository scans

### Dashboard Improvements

* Execution history
* Repository health score
* Code-quality trends
* Repair analytics
* Detailed execution timeline
* Downloadable reports

---

# 📌 Project Goal

ACR_AGENT aims to reduce the manual effort required to identify and repair software issues.

The platform brings together:

```text
AI
+
DevOps
+
GitHub
+
Docker
+
Automated Code Analysis
+
Automated Code Repair
+
Pull Request Automation
```

into one autonomous development workflow.

---

# 👨‍💻 Development

For frontend development:

```bash
cd frontend
npm run dev
```

For backend development:

```bash
cd backend
uvicorn main:socket_app --reload --host 0.0.0.0 --port 8000
```

For a production frontend build:

```bash
cd frontend
npm run build
npm run start
```

---

# 📄 License

Add the project's chosen license here before publishing the project publicly.

---

## Project Summary

**ACR_AGENT** is an autonomous AI-powered code repair platform that:

> **Accepts a repository → analyzes the code → identifies problems → uses AI to generate fixes → validates the changes → commits the repair → pushes the changes → creates a Pull Request.**

The goal is to make software debugging and repair faster, more automated, and easier to monitor through a unified dashboard.
