# Dead Simple Infrastructure

> A minimal personal DevOps automation console for solo developers. Deploy Docker-based apps locally with one click.

## 🎯 Overview

**Dead Simple Infrastructure (DSI)** is a local-first deployment platform that allows you to:
- Connect a Git repository
- Automatically build Docker containers
- Deploy and manage applications
- View logs and metrics in real-time
- Manage secrets securely (AES-256-GCM encryption)

Think of it as "Vercel meets Local-First Deployment" — all the convenience of cloud platforms, running entirely on your machine.

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────┐
│                     Console (Web UI)                    │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐ │
│  │  Dashboard   │  │ App Details  │  │   Secrets    │ │
│  └──────────────┘  └──────────────┘  └──────────────┘ │
└─────────────────────────────────────────────────────────┘
                          ↕ REST API / WebSocket / SSE
┌─────────────────────────────────────────────────────────┐
│              Console API (FastAPI Backend)              │
│  • Apps Management  • Deployments  • Secrets Vault      │
└─────────────────────────────────────────────────────────┘
                          ↕ WebSocket Commands
┌─────────────────────────────────────────────────────────┐
│                    Agent (Python)                        │
│  • Git Clone  • Docker Build  • Container Management    │
│  • Log Streaming  • Metrics Collection                  │
└─────────────────────────────────────────────────────────┘
                          ↕ Docker API
┌─────────────────────────────────────────────────────────┐
│                   Running Containers                     │
│         (Your deployed applications)                     │
└─────────────────────────────────────────────────────────┘
```

## 🚀 Quick Start

### Prerequisites
- Docker & Docker Compose
- Git
- Node.js 18+ (for local frontend development)
- Python 3.11+ (for local backend development)

### Option 1: Docker Compose (Recommended)

1. **Clone the repository**
```bash
git clone <your-repo-url>
cd dead-simple-infra
```

2. **Start all services**
```bash
docker-compose up -d
```

3. **Access the Console**
- Web UI: http://localhost:3000
- API: http://localhost:8001/api
- API Docs: http://localhost:8001/docs

4. **Stop services**
```bash
docker-compose down
```

### Option 2: Local Development

**Terminal 1 - MongoDB**
```bash
mongod --dbpath ./data/db
```

**Terminal 2 - Backend Console**
```bash
cd backend
pip install -r requirements.txt
export MONGO_URL="mongodb://localhost:27017"
export DB_NAME="dead_simple_infra"
export MASTER_ENCRYPTION_KEY="dev-master-key-32-bytes-long!!"
uvicorn server:app --reload --port 8001
```

**Terminal 3 - Agent**
```bash
cd backend
export CONSOLE_WS_URL="ws://localhost:8001/api/v1/agents/stream"
export AGENT_NAME="local-agent"
python agent.py
```

**Terminal 4 - Frontend**
```bash
cd frontend
yarn install
yarn start
```

## 📖 Usage Guide

### 1. Create an App

1. Click **"New App"** button in the Dashboard
2. Enter:
   - **App Name**: e.g., `my-node-app`
   - **Git Repository URL**: e.g., `https://github.com/user/my-app.git`
3. Click **"Create App"**

**Requirements:**
- Your repository must contain a `Dockerfile`
- The Dockerfile should expose port `8080` (this is mapped automatically)

### 2. Deploy the App

1. Click **"Deploy"** button on the app card
2. The agent will:
   - Clone your repository
   - Build the Docker image
   - Start a container
   - Stream logs to the Console
3. Once deployed, you'll see:
   - Status changes to **"running"**
   - Application URL (e.g., `http://localhost:32768`)
   - Live logs in the App Details page

### 3. Manage Secrets

1. Navigate to the **App Details** page
2. Click **"Secrets"** tab
3. Click **"Add Secret"**
4. Enter:
   - **Key**: e.g., `DATABASE_URL`
   - **Value**: e.g., `postgres://...`
5. Secrets are encrypted with AES-256-GCM before storage

### 4. Monitor Your App

The **App Details** page shows:
- **Real-time Metrics**: CPU, Memory, Uptime, Request Count
- **Live Logs**: Terminal-style log viewer with SSE streaming
- **Deployment History**: List of all deployments
- **Secrets**: Manage environment variables

## 🔐 Security Features

- **AES-256-GCM Encryption**: All secrets are encrypted before storage
- **Outbound-only Agent**: Agent connects to Console (no inbound ports)
- **WebSocket Authentication**: Secure bidirectional communication
- **No Hardcoded Secrets**: All configuration via environment variables

## 🛠️ Tech Stack

### Backend (Console API)
- **Framework**: FastAPI (Python)
- **Database**: MongoDB
- **Encryption**: `cryptography` library (AES-256-GCM)
- **Communication**: WebSocket + Server-Sent Events (SSE)

### Frontend (Console UI)
- **Framework**: React (TypeScript/JavaScript)
- **UI Components**: shadcn/ui (Radix UI)
- **Styling**: Tailwind CSS
- **Routing**: React Router
- **HTTP Client**: Axios

### Agent (Data Plane)
- **Language**: Python
- **Container Runtime**: Docker SDK
- **Git**: subprocess (git CLI)
- **Metrics**: psutil

## 📁 Project Structure

```
dead-simple-infra/
├── backend/
│   ├── server.py          # FastAPI Console API
│   ├── agent.py           # Agent service
│   ├── crypto.py          # AES-GCM encryption utilities
│   ├── requirements.txt   # Python dependencies
│   ├── Dockerfile         # Console Docker image
│   └── Dockerfile.agent   # Agent Docker image
├── frontend/
│   ├── src/
│   │   ├── App.js         # Main React app
│   │   ├── App.css        # Terminal-style theme
│   │   ├── pages/
│   │   │   ├── Dashboard.jsx      # Apps listing
│   │   │   └── AppDetails.jsx    # App management
│   │   └── components/ui/         # shadcn/ui components
│   ├── package.json
│   └── Dockerfile
├── docker-compose.yml     # Local deployment setup
└── README.md
```

## 🔧 API Reference

### Apps
- `POST /api/v1/apps` - Create a new app
- `GET /api/v1/apps` - List all apps
- `GET /api/v1/apps/{id}` - Get app details
- `DELETE /api/v1/apps/{id}` - Delete an app

### Deployments
- `POST /api/v1/apps/{id}/deploy` - Trigger deployment
- `GET /api/v1/apps/{id}/status` - Get deployment status
- `GET /api/v1/deployments/{app_id}` - List deployments

### Secrets
- `POST /api/v1/apps/{id}/secrets` - Add encrypted secret
- `GET /api/v1/apps/{id}/secrets` - List secrets (encrypted values hidden)
- `DELETE /api/v1/apps/{id}/secrets/{secret_id}` - Delete secret

### Agents
- `POST /api/v1/agents/register` - Register agent
- `GET /api/v1/agents` - List agents
- `WS /api/v1/agents/stream` - WebSocket for agent communication

### Monitoring
- `GET /api/v1/apps/{id}/logs/stream` - SSE log streaming
- `GET /api/v1/apps/{id}/metrics` - Get metrics history

## 🧪 Example: Deploy a Sample App

### Create a simple Node.js app with Dockerfile:

**app.js**
```javascript
const express = require('express');
const app = express();
const PORT = 8080;

app.get('/', (req, res) => {
  res.json({ message: 'Hello from Dead Simple Infrastructure!' });
});

app.listen(PORT, () => {
  console.log(`Server running on port ${PORT}`);
});
```

**Dockerfile**
```dockerfile
FROM node:18-alpine
WORKDIR /app
COPY package*.json ./
RUN npm install
COPY . .
EXPOSE 8080
CMD ["node", "app.js"]
```

**package.json**
```json
{
  "name": "sample-app",
  "version": "1.0.0",
  "dependencies": {
    "express": "^4.18.0"
  }
}
```

Push to GitHub and deploy via DSI Console!

## 🎨 UI Design

The Console features a **developer-focused dark theme** with:
- Terminal-style log viewer
- GitHub-inspired color palette
- Real-time status indicators
- Smooth animations and transitions
- Monospace fonts for code elements

## 🚧 Limitations & MVP Scope

This is an **MVP** with intentional simplifications:
- ✅ Single-user mode (no authentication)
- ✅ Docker-based apps only (Dockerfile required)
- ✅ Local deployment only
- ✅ Basic metrics (CPU, memory)
- ❌ No CI/CD pipelines
- ❌ No auto-scaling
- ❌ No load balancing
- ❌ No HTTPS/TLS (use Caddy/Traefik for production)

## 🔮 Future Enhancements

- Multi-user support with JWT authentication
- Auto HTTPS with Caddy integration
- Support for non-Docker deployments
- Advanced monitoring (request tracing, error tracking)
- Deployment rollbacks
- Resource limits and quotas
- Remote agent support (deploy to other machines)
- GitHub webhooks for auto-deploy

## 🐛 Troubleshooting

### Agent not connecting?
- Check if Console API is running on port 8001
- Verify WebSocket URL in agent environment
- Check Docker socket permissions

### Build failing?
- Ensure Dockerfile exists in your repository
- Check build logs in App Details page
- Verify Dockerfile exposes port 8080

### Logs not streaming?
- Check if agent is connected (Dashboard shows agent status)
- Verify SSE connection in browser dev tools
- Try refreshing the App Details page

## 📄 License

MIT License - feel free to use this for personal or commercial projects.

## 🤝 Contributing

This is an MVP built for learning and demonstration. Contributions welcome!

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

---

**Built with ❤️ for developers who want cloud-like convenience without the cloud.**
