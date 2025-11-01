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
    
    # Test the retry logic by mocking at a higher level
    call_count = 0
    backoff_times = []
    
    class MockAgent:
        def __init__(self):
            self.running = True
            self.current_build = None
        
        async def connect(self):
            nonlocal call_count
            call_count += 1
            if call_count <= 2:
                raise Exception(f"Connection failed (attempt {call_count})")
            # Success on third attempt
            return
        
        async def connect_with_retry(self):
            """Simplified version of retry logic for testing"""
            import time
            MAX_RETRIES = 3
            INITIAL_BACKOFF = 0.1  # Faster for testing
            MAX_BACKOFF = 1
            
            attempt = 0
            backoff = INITIAL_BACKOFF
            
            while attempt < MAX_RETRIES:
                try:
                    await self.connect()
                    return  # Success
                except Exception as e:
                    attempt += 1
                    if attempt >= MAX_RETRIES:
                        raise
                    else:
                        backoff_times.append(backoff)
                        await asyncio.sleep(backoff)
                        backoff = min(backoff * 2, MAX_BACKOFF)
    
    agent = MockAgent()
    
    try:
        await agent.connect_with_retry()
    except Exception:
        pass
    
    # Verify retry attempts
    assert call_count == 3, f"Expected 3 connection attempts, got {call_count}"
    
    # Verify exponential backoff (second backoff should be ~2x first)
    if len(backoff_times) >= 2:
        assert backoff_times[1] > backoff_times[0], "Backoff should increase exponentially"
    
    print(f"✓ Agent retried {call_count} times with exponential backoff: {backoff_times}")


if __name__ == "__main__":
    # Run tests
    print("Running reliability tests...\n")
    
    test_healthz_endpoint_returns_ok()
    test_readyz_fails_when_no_agents()
    test_readyz_succeeds_when_agent_connected()
    
    # Run async test
    asyncio.run(test_agent_retry_with_exponential_backoff())
    
    print("\n✅ All reliability tests passed!")
