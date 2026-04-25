import asyncio
import os
import sys

# Add backend to path to import app
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend")))

from app.utils.mcp_client import get_mcp_client

async def test_mcp():
    mcp = get_mcp_client()
    print("Fetching PRs...")
    prs = await mcp.get_prs()
    print(f"Result: {prs}")

if __name__ == "__main__":
    asyncio.run(test_mcp())
