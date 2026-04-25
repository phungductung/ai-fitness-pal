import os
import asyncio
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

class MCPClient:
    def __init__(self):
        # Determine the root directory (3 levels up from this file)
        root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
        
        # Path to the virtual environment's python executable
        self.python_path = os.path.join(root_dir, ".venv", "bin", "python")
        
        # Path to the server script
        self.server_script = os.path.join(root_dir, "fitness_mcp", "server.py")
        
        self.server_params = StdioServerParameters(
            command=self.python_path,
            args=[self.server_script],
            env=os.environ.copy()
        )

    async def call_tool(self, tool_name: str, arguments: dict = None):
        """Generic method to call any MCP tool."""
        try:
            async with stdio_client(self.server_params) as (read, write):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    result = await session.call_tool(tool_name, arguments or {})
                    # FastMCP tool results are typically in content[0].text
                    if hasattr(result, "content") and len(result.content) > 0:
                        return result.content[0].text
                    return str(result)
        except Exception as e:
            return f"Error calling MCP tool {tool_name}: {e}"

    async def get_prs(self):
        """Fetch PRs from the MCP server."""
        return await self.call_tool("get_personal_records")

    async def query_diary(self, sql_query: str):
        """Execute a query on the fitness diary via MCP."""
        return await self.call_tool("query_fitness_diary", {"query": sql_query})

    async def add_pr(self, exercise: str, weight: float, reps: int):
        """Log a new personal record via MCP."""
        return await self.call_tool("add_personal_record", {"exercise": exercise, "weight": weight, "reps": reps})

    async def add_diary(self, entry: str, calories: int, protein: int, weight: float = None, sleep_hours: float = 8.0, fatigue: int = 3):
        """Log a new diary entry via MCP."""
        return await self.call_tool("add_diary_entry", {
            "entry": entry, 
            "calories": calories, 
            "protein": protein, 
            "weight": weight,
            "sleep_hours": sleep_hours,
            "fatigue": fatigue
        })

# Helper to get the client instance
def get_mcp_client():
    return MCPClient()
