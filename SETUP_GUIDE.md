# Dead Simple Infrastructure - Setup Guide

## 🎯 Quick Start (Current Environment)

The MVP is already running in your current environment! Here's what you can do right now:

### Current Setup
- ✅ **Console API**: Running at http://localhost:8001
- ✅ **Web UI**: Running at http://localhost:3000
- ✅ **MongoDB**: Connected and ready
- ⚠️ **Agent**: Not yet started (manual start required for full deployment testing)

### Test the Console UI

1. **Access the Dashboard**
   ```
   Open: http://localhost:3000
   ```

2. **Create Your First App**
   - Click "New App" button
   - Enter app name (e.g., `my-test-app`)
   - Enter Git repository URL
   - Click "Create App"

3. **View App Details**
   - Click on any app card
   - Explore tabs: Logs, Deployments, Secrets

4. **Add Secrets**
   - Go to Secrets tab
   - Click "Add Secret"
   - Enter key/value pairs (encrypted with AES-256-GCM)

### Test the API

```bash
# Check API status
curl http://localhost:8001/api/

# Create an app
curl -X POST http://localhost:8001/api/v1/apps \
  -H "Content-Type: application/json" \
  -d '{
    "name": "test-app",
    "repo_url": "https://github.com/user/repo.git"
  }'

# List all apps
curl http://localhost:8001/api/v1/apps

# Add a secret
APP_ID="<your-app-id>"
curl -X POST http://localhost:8001/api/v1/apps/$APP_ID/secrets \
  -H "Content-Type: application/json" \
  -d '{
    "app_id": "'$APP_ID'",
    "key": "DATABASE_URL",
    "value": "postgres://localhost:5432/mydb"
  }'
```

---

## 🐳 Docker Compose Setup (Full Stack)

For a complete local deployment with the Agent service:

### Prerequisites
- Docker & Docker Compose installed
- Git installed
- At least 4GB RAM available

### Steps

1. **Navigate to project directory**
   ```bash
   cd /app
   ```

2. **Start all services**
   ```bash
   docker-compose up -d
   ```

   This will start:
   - MongoDB (port 27017)
   - Console API (port 8001)
   - Frontend (port 3000)
   - Agent (connects to Console via WebSocket)

3. **Check service status**
   ```bash
   docker-compose ps
   ```

4. **View logs**
   ```bash
   # All services
   docker-compose logs -f

   # Specific service
   docker-compose logs -f agent
   docker-compose logs -f console
   ```

5. **Access the Console**
   - Web UI: http://localhost:3000
   - API: http://localhost:8001/api
   - API Docs: http://localhost:8001/docs

6. **Test a deployment**
   - Create an app with a Git repo that has a Dockerfile
   - Click "Deploy"
   - Watch logs in real-time
   - Access deployed app at the URL shown

7. **Stop services**
   ```bash
   docker-compose down
   ```

8. **Clean up (remove data)**
   ```bash
   docker-compose down -v
   ```

---

## 🛠️ Development Setup (Manual)

For local development without Docker:

### Terminal 1: MongoDB
```bash
# Start MongoDB
mongod --dbpath ./data/db
```

### Terminal 2: Console API (Backend)
```bash
cd /app/backend

# Install dependencies
pip install -r requirements.txt

# Set environment variables
export MONGO_URL="mongodb://localhost:27017"
export DB_NAME="dead_simple_infra"
export MASTER_ENCRYPTION_KEY="dev-master-key-32-bytes-long!!"
export CORS_ORIGINS="*"

# Start the server
uvicorn server:app --reload --port 8001
```

### Terminal 3: Agent (Optional - for full deployments)
```bash
cd /app/backend

# Set environment variables
export CONSOLE_WS_URL="ws://localhost:8001/api/v1/agents/stream"
export AGENT_NAME="local-agent"

# Start the agent
python agent.py
```

### Terminal 4: Frontend
```bash
cd /app/frontend

# Install dependencies (first time only)
yarn install

# Start development server
yarn start
```

The Console will be available at http://localhost:3000

---

## 🧪 Testing the Agent

The Agent is responsible for:
- Cloning Git repositories
- Building Docker images
- Running containers
- Streaming logs and metrics

### Prerequisites for Agent
- Docker daemon running
- Git CLI installed
- Python 3.11+
- Required Python packages: `websockets`, `docker`, `psutil`

### Start the Agent

**Option 1: Manual (Current Environment)**
```bash
cd /app/backend

export CONSOLE_WS_URL="ws://localhost:8001/api/v1/agents/stream"
export AGENT_NAME="local-agent"

python agent.py
```

**Option 2: Docker Compose**
```bash
docker-compose up agent
```

### Verify Agent Connection
- Open the Console UI (http://localhost:3000)
- Check the "Agents" status bar
- Should show "local-agent" with green status

### Test a Deployment

1. **Create a test repository** with:
   - `Dockerfile` (must expose port 8080)
   - Application code

2. **Example Dockerfile**:
   ```dockerfile
   FROM node:18-alpine
   WORKDIR /app
   COPY package*.json ./
   RUN npm install
   COPY . .
   EXPOSE 8080
   CMD ["npm", "start"]
   ```

3. **Deploy via Console**:
   - Create app with your repo URL
   - Click "Deploy"
   - Watch build logs in real-time
   - Access app at provided URL

---

## 📋 Environment Variables Reference

### Backend (Console API)
```bash
MONGO_URL="mongodb://localhost:27017"        # MongoDB connection string
DB_NAME="dead_simple_infra"                  # Database name
CORS_ORIGINS="*"                             # CORS allowed origins
MASTER_ENCRYPTION_KEY="your-32-byte-key"    # AES-256 encryption key
```

### Frontend
```bash
REACT_APP_BACKEND_URL="http://localhost:8001"  # Backend API URL
```

### Agent
```bash
CONSOLE_WS_URL="ws://localhost:8001/api/v1/agents/stream"  # WebSocket URL
AGENT_NAME="local-agent"                                    # Agent identifier
```

---

## 🔍 Troubleshooting

### Agent Not Connecting?
- Check if Console API is running: `curl http://localhost:8001/api/`
- Verify WebSocket URL is correct
- Check Docker socket permissions: `ls -l /var/run/docker.sock`
- View agent logs: `docker-compose logs agent`

### Build Failing?
- Ensure Dockerfile exists in repository
- Check Dockerfile exposes port 8080
- Verify Docker daemon is running: `docker ps`
- Check agent logs for error details

### Logs Not Streaming?
- Verify agent is connected (check Dashboard)
- Check browser console for SSE errors
- Ensure port 8001 is accessible
- Try refreshing the App Details page

### Port Already in Use?
```bash
# Find process using port
lsof -ti:8001
lsof -ti:3000

# Kill the process
kill -9 <PID>
```

### Database Issues?
```bash
# Check MongoDB status
docker-compose logs mongodb

# Reset database
docker-compose down -v
docker-compose up -d
```

---

## 🚀 Next Steps

1. **Try the Example App**
   - See `/app/examples/hello-world/README.md`
   - Create a GitHub repo with the example
   - Deploy it through the Console

2. **Add More Features**
   - Implement container restart policies
   - Add deployment rollback
   - Enhance monitoring metrics
   - Add GitHub webhook integration

3. **Production Considerations**
   - Add user authentication (JWT)
   - Use proper secret management (HashiCorp Vault, AWS KMS)
   - Configure HTTPS with Caddy/Traefik
   - Set up remote agents
   - Add resource limits and quotas

4. **Explore the Code**
   - Backend: `/app/backend/server.py` - Console API
   - Agent: `/app/backend/agent.py` - Deployment engine
   - Frontend: `/app/frontend/src/` - React UI
   - Encryption: `/app/backend/crypto.py` - AES-256-GCM

---

## 📚 Additional Resources

- **API Documentation**: http://localhost:8001/docs (when server is running)
- **Main README**: `/app/README.md`
- **Example App**: `/app/examples/hello-world/`
- **Docker Compose**: `/app/docker-compose.yml`

---

## 💡 Pro Tips

1. **Fast Iteration**: Use `--reload` flag with uvicorn for auto-reload during development
2. **View All Logs**: `docker-compose logs -f` shows all service logs in real-time
3. **Clean Slate**: Use `docker-compose down -v` to reset everything including database
4. **Test Locally**: Start just the Console API and Frontend for quick UI testing
5. **Agent Testing**: Use a simple Node.js or Python app with Dockerfile for initial tests

---

**Happy Deploying! 🎉**
