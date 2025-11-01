from fastapi import FastAPI, APIRouter, HTTPException, WebSocket, WebSocketDisconnect, Request
from fastapi.responses import StreamingResponse
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional, Dict, Any
import uuid
from datetime import datetime, timezone
import asyncio
import json

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# Create the main app without a prefix
app = FastAPI(title="Dead Simple Infrastructure Console")

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")

# Store active WebSocket connections
active_agents: Dict[str, WebSocket] = {}
log_subscribers: Dict[str, List[asyncio.Queue]] = {}

# Define Models
class App(BaseModel):
    model_config = ConfigDict(extra="ignore")
    
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    repo_url: Optional[str] = None
    repo_type: str = "git"  # git or zip
    status: str = "idle"  # idle, building, running, failed, stopped
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    port: Optional[int] = None
    url: Optional[str] = None

class AppCreate(BaseModel):
    name: str
    repo_url: str
    repo_type: str = "git"

class Deployment(BaseModel):
    model_config = ConfigDict(extra="ignore")
    
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    app_id: str
    status: str = "pending"  # pending, building, running, failed, stopped
    build_logs: List[str] = []
    started_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: Optional[datetime] = None

class DeploymentTrigger(BaseModel):
    app_id: str

class Secret(BaseModel):
    model_config = ConfigDict(extra="ignore")
    
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    app_id: str
    key: str
    encrypted_value: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class SecretCreate(BaseModel):
    app_id: str
    key: str
    value: str

class Agent(BaseModel):
    model_config = ConfigDict(extra="ignore")
    
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    status: str = "offline"  # online, offline
    registered_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    last_seen: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class AgentRegister(BaseModel):
    name: str

class Metrics(BaseModel):
    app_id: str
    cpu_percent: float
    memory_mb: float
    uptime_seconds: int
    request_count: int
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

# API Routes

@api_router.get("/")
async def root():
    return {"message": "Dead Simple Infrastructure Console API v1", "status": "online"}

@api_router.get("/healthz")
async def healthz():
    """Health check endpoint - always returns 200 if service is up"""
    return {"status": "ok"}

@api_router.get("/readyz")
async def readyz():
    """Readiness check - fails if no agents connected"""
    if len(active_agents) == 0:
        raise HTTPException(status_code=503, detail="No agents connected")
    return {"status": "ok", "agents_count": len(active_agents)}

# Apps Management
@api_router.post("/v1/apps", response_model=App)
async def create_app(input: AppCreate):
    app_obj = App(**input.model_dump())
    doc = app_obj.model_dump()
    doc['created_at'] = doc['created_at'].isoformat()
    doc['updated_at'] = doc['updated_at'].isoformat()
    
    await db.apps.insert_one(doc)
    return app_obj

@api_router.get("/v1/apps", response_model=List[App])
async def list_apps():
    apps = await db.apps.find({}, {"_id": 0}).to_list(1000)
    for app in apps:
        if isinstance(app.get('created_at'), str):
            app['created_at'] = datetime.fromisoformat(app['created_at'])
        if isinstance(app.get('updated_at'), str):
            app['updated_at'] = datetime.fromisoformat(app['updated_at'])
    return apps

@api_router.get("/v1/apps/{app_id}", response_model=App)
async def get_app(app_id: str):
    app = await db.apps.find_one({"id": app_id}, {"_id": 0})
    if not app:
        raise HTTPException(status_code=404, detail="App not found")
    
    if isinstance(app.get('created_at'), str):
        app['created_at'] = datetime.fromisoformat(app['created_at'])
    if isinstance(app.get('updated_at'), str):
        app['updated_at'] = datetime.fromisoformat(app['updated_at'])
    return app

@api_router.delete("/v1/apps/{app_id}")
async def delete_app(app_id: str):
    result = await db.apps.delete_one({"id": app_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="App not found")
    
    # Also delete related secrets and deployments
    await db.secrets.delete_many({"app_id": app_id})
    await db.deployments.delete_many({"app_id": app_id})
    
    return {"message": "App deleted successfully"}

# Deployment Management
@api_router.post("/v1/apps/{app_id}/deploy")
async def trigger_deployment(app_id: str):
    # Check if app exists
    app = await db.apps.find_one({"id": app_id}, {"_id": 0})
    if not app:
        raise HTTPException(status_code=404, detail="App not found")
    
    # Create deployment record
    deployment = Deployment(app_id=app_id, status="pending")
    doc = deployment.model_dump()
    doc['started_at'] = doc['started_at'].isoformat()
    await db.deployments.insert_one(doc)
    
    # Update app status
    await db.apps.update_one(
        {"id": app_id},
        {"$set": {"status": "building", "updated_at": datetime.now(timezone.utc).isoformat()}}
    )
    
    # Send deploy command to agent via WebSocket
    if active_agents:
        agent_ws = list(active_agents.values())[0]
        try:
            await agent_ws.send_json({
                "type": "deploy",
                "deployment_id": deployment.id,
                "app_id": app_id,
                "repo_url": app.get('repo_url'),
                "app_name": app.get('name')
            })
        except Exception as e:
            logging.error(f"Failed to send deploy command: {e}")
    
    return deployment

@api_router.get("/v1/apps/{app_id}/status")
async def get_app_status(app_id: str):
    app = await db.apps.find_one({"id": app_id}, {"_id": 0})
    if not app:
        raise HTTPException(status_code=404, detail="App not found")
    
    # Get latest deployment
    latest_deployment = await db.deployments.find_one(
        {"app_id": app_id},
        {"_id": 0},
        sort=[("started_at", -1)]
    )
    
    # Get latest metrics
    latest_metrics = await db.metrics.find_one(
        {"app_id": app_id},
        {"_id": 0},
        sort=[("timestamp", -1)]
    )
    
    return {
        "app": app,
        "deployment": latest_deployment,
        "metrics": latest_metrics
    }

@api_router.get("/v1/deployments/{app_id}", response_model=List[Deployment])
async def get_deployments(app_id: str):
    deployments = await db.deployments.find(
        {"app_id": app_id},
        {"_id": 0}
    ).sort("started_at", -1).to_list(100)
    
    for dep in deployments:
        if isinstance(dep.get('started_at'), str):
            dep['started_at'] = datetime.fromisoformat(dep['started_at'])
        if dep.get('completed_at') and isinstance(dep['completed_at'], str):
            dep['completed_at'] = datetime.fromisoformat(dep['completed_at'])
    
    return deployments

# Secrets Management
@api_router.post("/v1/apps/{app_id}/secrets")
async def add_secret(app_id: str, secret: SecretCreate):
    from crypto import encrypt_secret
    
    # Verify app exists
    app = await db.apps.find_one({"id": app_id}, {"_id": 0})
    if not app:
        raise HTTPException(status_code=404, detail="App not found")
    
    # Encrypt the secret value
    encrypted_value = encrypt_secret(secret.value)
    
    secret_obj = Secret(
        app_id=app_id,
        key=secret.key,
        encrypted_value=encrypted_value
    )
    
    doc = secret_obj.model_dump()
    doc['created_at'] = doc['created_at'].isoformat()
    
    await db.secrets.insert_one(doc)
    return {"message": "Secret added successfully", "key": secret.key}

@api_router.get("/v1/apps/{app_id}/secrets")
async def get_secrets(app_id: str):
    secrets = await db.secrets.find({"app_id": app_id}, {"_id": 0, "encrypted_value": 0}).to_list(100)
    return secrets

@api_router.delete("/v1/apps/{app_id}/secrets/{secret_id}")
async def delete_secret(app_id: str, secret_id: str):
    result = await db.secrets.delete_one({"id": secret_id, "app_id": app_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Secret not found")
    return {"message": "Secret deleted successfully"}

# Agent Management
@api_router.post("/v1/agents/register", response_model=Agent)
async def register_agent(input: AgentRegister):
    agent_obj = Agent(**input.model_dump(), status="online")
    doc = agent_obj.model_dump()
    doc['registered_at'] = doc['registered_at'].isoformat()
    doc['last_seen'] = doc['last_seen'].isoformat()
    
    await db.agents.insert_one(doc)
    return agent_obj

@api_router.get("/v1/agents", response_model=List[Agent])
async def list_agents():
    agents = await db.agents.find({}, {"_id": 0}).to_list(100)
    for agent in agents:
        if isinstance(agent.get('registered_at'), str):
            agent['registered_at'] = datetime.fromisoformat(agent['registered_at'])
        if isinstance(agent.get('last_seen'), str):
            agent['last_seen'] = datetime.fromisoformat(agent['last_seen'])
    return agents

# WebSocket for Agent Communication
@app.websocket("/api/v1/agents/stream")
async def agent_websocket(websocket: WebSocket):
    await websocket.accept()
    agent_id = str(uuid.uuid4())
    active_agents[agent_id] = websocket
    
    logging.info(f"Agent {agent_id} connected")
    
    try:
        while True:
            data = await websocket.receive_json()
            msg_type = data.get("type")
            
            if msg_type == "log":
                # Broadcast log to subscribers
                app_id = data.get("app_id")
                if app_id in log_subscribers:
                    for queue in log_subscribers[app_id]:
                        await queue.put(data)
            
            elif msg_type == "status_update":
                # Update app status
                app_id = data.get("app_id")
                status = data.get("status")
                await db.apps.update_one(
                    {"id": app_id},
                    {"$set": {"status": status, "updated_at": datetime.now(timezone.utc).isoformat()}}
                )
                
                # Update deployment status
                deployment_id = data.get("deployment_id")
                if deployment_id:
                    await db.deployments.update_one(
                        {"id": deployment_id},
                        {"$set": {"status": status}}
                    )
            
            elif msg_type == "metrics":
                # Store metrics
                metrics_data = data.get("data", {})
                metrics_data['timestamp'] = datetime.now(timezone.utc).isoformat()
                await db.metrics.insert_one(metrics_data)
            
            elif msg_type == "deployment_complete":
                app_id = data.get("app_id")
                deployment_id = data.get("deployment_id")
                port = data.get("port")
                url = data.get("url")
                
                await db.apps.update_one(
                    {"id": app_id},
                    {"$set": {
                        "status": "running",
                        "port": port,
                        "url": url,
                        "updated_at": datetime.now(timezone.utc).isoformat()
                    }}
                )
                
                await db.deployments.update_one(
                    {"id": deployment_id},
                    {"$set": {
                        "status": "running",
                        "completed_at": datetime.now(timezone.utc).isoformat()
                    }}
                )
    
    except WebSocketDisconnect:
        logging.info(f"Agent {agent_id} disconnected")
    except Exception as e:
        logging.error(f"WebSocket error: {e}")
    finally:
        if agent_id in active_agents:
            del active_agents[agent_id]

# SSE for Log Streaming
@api_router.get("/v1/apps/{app_id}/logs/stream")
async def stream_logs(app_id: str):
    async def event_generator():
        queue = asyncio.Queue()
        
        if app_id not in log_subscribers:
            log_subscribers[app_id] = []
        log_subscribers[app_id].append(queue)
        
        try:
            while True:
                log_data = await queue.get()
                yield f"data: {json.dumps(log_data)}\n\n"
        except asyncio.CancelledError:
            if app_id in log_subscribers and queue in log_subscribers[app_id]:
                log_subscribers[app_id].remove(queue)
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        }
    )

# Metrics endpoint
@api_router.get("/v1/apps/{app_id}/metrics")
async def get_metrics(app_id: str, limit: int = 50):
    metrics = await db.metrics.find(
        {"app_id": app_id},
        {"_id": 0}
    ).sort("timestamp", -1).limit(limit).to_list(limit)
    
    for metric in metrics:
        if isinstance(metric.get('timestamp'), str):
            metric['timestamp'] = datetime.fromisoformat(metric['timestamp'])
    
    return metrics

# Include the router in the main app
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Graceful shutdown flag
shutdown_flag = False

@app.on_event("startup")
async def startup_event():
    logger.info("Console API starting up")

@app.on_event("shutdown")
async def shutdown_db_client():
    global shutdown_flag
    shutdown_flag = True
    logger.info("Initiating graceful shutdown...")
    
    # Close all active agent connections
    for agent_id, ws in list(active_agents.items()):
        try:
            await ws.close(code=1001, reason="Server shutting down")
            logger.info(f"Closed connection to agent {agent_id}")
        except Exception as e:
            logger.error(f"Error closing agent connection: {e}")
    
    # Close MongoDB client
    client.close()
    logger.info("Console API shutdown complete")
