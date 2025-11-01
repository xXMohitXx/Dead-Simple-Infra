#!/usr/bin/env python3
"""
Dead Simple Infrastructure Agent

This agent connects to the Console via WebSocket, receives deployment commands,
builds and runs Docker containers, and streams logs/metrics back to the Console.
"""

import asyncio
import websockets
import json
import logging
import docker
import os
import tempfile
import shutil
from datetime import datetime
import psutil
import subprocess
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Configuration
CONSOLE_WS_URL = os.environ.get('CONSOLE_WS_URL', 'ws://localhost:8001/api/v1/agents/stream')
AGENT_NAME = os.environ.get('AGENT_NAME', 'local-agent')
WORK_DIR = Path('/tmp/dsi-agent-workspace')
WORK_DIR.mkdir(exist_ok=True)

# Retry configuration
MAX_RETRIES = 3
INITIAL_BACKOFF = 2  # seconds
MAX_BACKOFF = 60  # seconds

# Docker client
docker_client = docker.from_env()

# Track running containers
running_containers = {}

# Graceful shutdown flag
shutdown_flag = False

class Agent:
    def __init__(self):
        self.websocket = None
        self.running = True
    
    async def connect(self):
        """Connect to Console WebSocket"""
        logger.info(f"Connecting to Console at {CONSOLE_WS_URL}")
        
        while self.running:
            try:
                async with websockets.connect(CONSOLE_WS_URL) as websocket:
                    self.websocket = websocket
                    logger.info("Connected to Console")
                    
                    # Send registration
                    await self.send_message({
                        "type": "register",
                        "agent_name": AGENT_NAME
                    })
                    
                    # Start metrics loop
                    asyncio.create_task(self.metrics_loop())
                    
                    # Listen for commands
                    await self.listen_for_commands()
            
            except Exception as e:
                logger.error(f"Connection failed: {e}")
                await asyncio.sleep(5)  # Retry after 5 seconds
    
    async def listen_for_commands(self):
        """Listen for deployment commands from Console"""
        try:
            async for message in self.websocket:
                data = json.loads(message)
                msg_type = data.get('type')
                
                logger.info(f"Received command: {msg_type}")
                
                if msg_type == 'deploy':
                    asyncio.create_task(self.handle_deploy(data))
                elif msg_type == 'stop':
                    asyncio.create_task(self.handle_stop(data))
                elif msg_type == 'restart':
                    asyncio.create_task(self.handle_restart(data))
        
        except websockets.exceptions.ConnectionClosed:
            logger.warning("WebSocket connection closed")
        except Exception as e:
            logger.error(f"Error in listen loop: {e}")
    
    async def send_message(self, data: dict):
        """Send message to Console"""
        if self.websocket:
            try:
                await self.websocket.send(json.dumps(data))
            except Exception as e:
                logger.error(f"Failed to send message: {e}")
    
    async def send_log(self, app_id: str, deployment_id: str, log_line: str):
        """Send log line to Console"""
        await self.send_message({
            "type": "log",
            "app_id": app_id,
            "deployment_id": deployment_id,
            "log": log_line,
            "timestamp": datetime.utcnow().isoformat()
        })
    
    async def send_status_update(self, app_id: str, deployment_id: str, status: str):
        """Send status update to Console"""
        await self.send_message({
            "type": "status_update",
            "app_id": app_id,
            "deployment_id": deployment_id,
            "status": status
        })
    
    async def handle_deploy(self, data: dict):
        """Handle deployment command"""
        app_id = data.get('app_id')
        deployment_id = data.get('deployment_id')
        repo_url = data.get('repo_url')
        app_name = data.get('app_name', 'app')
        
        logger.info(f"Deploying app {app_id} from {repo_url}")
        
        try:
            await self.send_status_update(app_id, deployment_id, "building")
            await self.send_log(app_id, deployment_id, f"Starting deployment for {app_name}")
            
            # Create workspace for this app
            app_dir = WORK_DIR / app_id
            if app_dir.exists():
                shutil.rmtree(app_dir)
            app_dir.mkdir(parents=True)
            
            # Clone repository
            await self.send_log(app_id, deployment_id, f"Cloning repository: {repo_url}")
            clone_result = subprocess.run(
                ['git', 'clone', repo_url, str(app_dir)],
                capture_output=True,
                text=True,
                timeout=300
            )
            
            if clone_result.returncode != 0:
                raise Exception(f"Git clone failed: {clone_result.stderr}")
            
            await self.send_log(app_id, deployment_id, "Repository cloned successfully")
            
            # Check for Dockerfile
            dockerfile_path = app_dir / 'Dockerfile'
            if not dockerfile_path.exists():
                raise Exception("Dockerfile not found in repository")
            
            # Build Docker image
            image_tag = f"dsi-{app_name}:{deployment_id[:8]}"
            await self.send_log(app_id, deployment_id, f"Building Docker image: {image_tag}")
            
            image, build_logs = docker_client.images.build(
                path=str(app_dir),
                tag=image_tag,
                rm=True
            )
            
            for log in build_logs:
                if 'stream' in log:
                    log_line = log['stream'].strip()
                    if log_line:
                        await self.send_log(app_id, deployment_id, log_line)
            
            await self.send_log(app_id, deployment_id, "Docker image built successfully")
            
            # Stop existing container if running
            if app_id in running_containers:
                try:
                    old_container = running_containers[app_id]
                    old_container.stop(timeout=10)
                    old_container.remove()
                except Exception as e:
                    logger.warning(f"Failed to stop old container: {e}")
            
            # Run container
            await self.send_log(app_id, deployment_id, "Starting container...")
            
            container = docker_client.containers.run(
                image_tag,
                detach=True,
                name=f"dsi-{app_name}-{app_id[:8]}",
                ports={'8080/tcp': None},  # Auto-assign port
                restart_policy={"Name": "unless-stopped"},
                labels={"dsi.app_id": app_id, "dsi.deployment_id": deployment_id}
            )
            
            running_containers[app_id] = container
            
            # Get assigned port
            container.reload()
            port_bindings = container.attrs['NetworkSettings']['Ports']
            host_port = None
            if '8080/tcp' in port_bindings and port_bindings['8080/tcp']:
                host_port = port_bindings['8080/tcp'][0]['HostPort']
            
            url = f"http://localhost:{host_port}" if host_port else None
            
            await self.send_log(app_id, deployment_id, f"Container started successfully on port {host_port}")
            await self.send_log(app_id, deployment_id, f"Application URL: {url}")
            
            # Send deployment complete
            await self.send_message({
                "type": "deployment_complete",
                "app_id": app_id,
                "deployment_id": deployment_id,
                "port": int(host_port) if host_port else None,
                "url": url,
                "container_id": container.id
            })
            
            await self.send_status_update(app_id, deployment_id, "running")
            
            # Start log streaming for this container
            asyncio.create_task(self.stream_container_logs(app_id, deployment_id, container))
        
        except Exception as e:
            error_msg = f"Deployment failed: {str(e)}"
            logger.error(error_msg)
            await self.send_log(app_id, deployment_id, error_msg)
            await self.send_status_update(app_id, deployment_id, "failed")
    
    async def stream_container_logs(self, app_id: str, deployment_id: str, container):
        """Stream container logs to Console"""
        try:
            for log_line in container.logs(stream=True, follow=True):
                log_text = log_line.decode('utf-8').strip()
                if log_text:
                    await self.send_log(app_id, deployment_id, log_text)
        except Exception as e:
            logger.error(f"Error streaming logs: {e}")
    
    async def handle_stop(self, data: dict):
        """Stop a running container"""
        app_id = data.get('app_id')
        
        if app_id in running_containers:
            try:
                container = running_containers[app_id]
                container.stop(timeout=10)
                container.remove()
                del running_containers[app_id]
                logger.info(f"Stopped container for app {app_id}")
            except Exception as e:
                logger.error(f"Failed to stop container: {e}")
    
    async def handle_restart(self, data: dict):
        """Restart a container"""
        app_id = data.get('app_id')
        
        if app_id in running_containers:
            try:
                container = running_containers[app_id]
                container.restart(timeout=10)
                logger.info(f"Restarted container for app {app_id}")
            except Exception as e:
                logger.error(f"Failed to restart container: {e}")
    
    async def metrics_loop(self):
        """Periodically send metrics for running containers"""
        while self.running:
            try:
                for app_id, container in running_containers.items():
                    try:
                        container.reload()
                        stats = container.stats(stream=False)
                        
                        # Calculate CPU percentage
                        cpu_delta = stats['cpu_stats']['cpu_usage']['total_usage'] - \
                                    stats['precpu_stats']['cpu_usage']['total_usage']
                        system_delta = stats['cpu_stats']['system_cpu_usage'] - \
                                      stats['precpu_stats']['system_cpu_usage']
                        cpu_percent = (cpu_delta / system_delta) * 100.0 if system_delta > 0 else 0.0
                        
                        # Memory usage
                        memory_usage = stats['memory_stats'].get('usage', 0) / (1024 * 1024)  # MB
                        
                        await self.send_message({
                            "type": "metrics",
                            "data": {
                                "app_id": app_id,
                                "cpu_percent": round(cpu_percent, 2),
                                "memory_mb": round(memory_usage, 2),
                                "uptime_seconds": 0,  # Calculate from container start time
                                "request_count": 0  # Would need instrumentation
                            }
                        })
                    except Exception as e:
                        logger.error(f"Error collecting metrics for {app_id}: {e}")
                
                await asyncio.sleep(10)  # Send metrics every 10 seconds
            
            except Exception as e:
                logger.error(f"Error in metrics loop: {e}")
                await asyncio.sleep(10)

async def main():
    agent = Agent()
    await agent.connect()

if __name__ == '__main__':
    asyncio.run(main())
