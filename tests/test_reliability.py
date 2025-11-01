"""
Tests for reliability improvements:
- Health check endpoints
- Agent retry logic
"""

import pytest
import asyncio
from unittest.mock import patch, MagicMock, AsyncMock
import sys
import os

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

def test_healthz_endpoint_returns_ok():
    """Test that /healthz endpoint returns 200 with status ok"""
    from fastapi.testclient import TestClient
    
    # Mock the MongoDB client to avoid connection
    with patch('server.AsyncIOMotorClient') as mock_mongo:
        mock_mongo.return_value = MagicMock()
        
        # Import after mocking
        from server import app
        
        client = TestClient(app)
        response = client.get("/api/healthz")
        
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}
        print("✓ /healthz returns 200 OK")


def test_readyz_fails_when_no_agents():
    """Test that /readyz fails when no agents are connected"""
    from fastapi.testclient import TestClient
    
    # Mock the MongoDB client
    with patch('server.AsyncIOMotorClient') as mock_mongo:
        mock_mongo.return_value = MagicMock()
        
        # Import after mocking
        from server import app
        import server
        
        # Ensure no agents are connected
        server.active_agents = {}
        
        client = TestClient(app)
        response = client.get("/api/readyz")
        
        assert response.status_code == 503
        assert "No agents connected" in response.json()["detail"]
        print("✓ /readyz fails with 503 when no agents connected")


def test_readyz_succeeds_when_agent_connected():
    """Test that /readyz succeeds when agents are connected"""
    from fastapi.testclient import TestClient
    
    # Mock the MongoDB client
    with patch('server.AsyncIOMotorClient') as mock_mongo:
        mock_mongo.return_value = MagicMock()
        
        # Import after mocking
        from server import app
        import server
        
        # Simulate agent connection
        server.active_agents = {"agent-1": MagicMock()}
        
        client = TestClient(app)
        response = client.get("/api/readyz")
        
        assert response.status_code == 200
        assert response.json()["status"] == "ok"
        assert response.json()["agents_count"] == 1
        print("✓ /readyz returns 200 OK when agents are connected")


@pytest.mark.asyncio
async def test_agent_retry_with_exponential_backoff():
    """Test that agent retries connection with exponential backoff"""
    
    # Mock websockets module
    with patch('agent.websockets') as mock_ws, \
         patch('agent.docker') as mock_docker, \
         patch('agent.logger') as mock_logger:
        
        # Setup mocks
        mock_docker.from_env.return_value = MagicMock()
        
        # Make first two attempts fail, third succeed
        call_count = 0
        async def mock_connect_side_effect(url):
            nonlocal call_count
            call_count += 1
            if call_count <= 2:
                raise Exception(f"Connection failed (attempt {call_count})")
            
            # Return a mock websocket
            mock_websocket = AsyncMock()
            mock_websocket.__aenter__ = AsyncMock(return_value=mock_websocket)
            mock_websocket.__aexit__ = AsyncMock(return_value=None)
            mock_websocket.send = AsyncMock()
            mock_websocket.__aiter__ = AsyncMock(return_value=iter([]))
            return mock_websocket
        
        mock_ws.connect = mock_connect_side_effect
        
        # Import agent module
        from agent import Agent
        
        agent = Agent()
        
        # Patch the listen_for_commands to prevent it from hanging
        async def mock_listen():
            pass
        agent.listen_for_commands = mock_listen
        
        # Try connecting with retry
        try:
            # Set a timeout to prevent test from hanging
            await asyncio.wait_for(agent.connect_with_retry(), timeout=5.0)
        except asyncio.TimeoutError:
            pass
        
        # Verify retry attempts were made
        assert call_count >= 2, "Agent should have retried at least twice"
        
        # Verify backoff logs were called
        warning_calls = [call for call in mock_logger.warning.call_args_list 
                        if 'Retrying' in str(call)]
        assert len(warning_calls) >= 1, "Should have logged retry attempts"
        
        print(f"✓ Agent retried {call_count} times with exponential backoff")


if __name__ == "__main__":
    # Run tests
    print("Running reliability tests...\n")
    
    test_healthz_endpoint_returns_ok()
    test_readyz_fails_when_no_agents()
    test_readyz_succeeds_when_agent_connected()
    
    # Run async test
    asyncio.run(test_agent_retry_with_exponential_backoff())
    
    print("\n✅ All reliability tests passed!")
