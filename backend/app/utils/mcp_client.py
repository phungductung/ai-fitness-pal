import os
import sys
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from app.utils.logger import get_logger, thread_id_var

logger = get_logger("mcp_client")

class MCPClient:
    def __init__(self, thread_id: str = None):
        # Determine the root directory (3 levels up from this file)
        root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
        
        # Priority for python path:
        # 1. Environment variable MCP_PYTHON_PATH
        # 2. Current sys.executable
        # 3. Fallback to .venv in root
        self.python_path = os.getenv("MCP_PYTHON_PATH")
        if not self.python_path:
            self.python_path = sys.executable
            
        # Path to the server script
        self.server_script = os.path.join(root_dir, "fitness_mcp", "server.py")
        
        self.thread_id = thread_id
        if thread_id:
            thread_id_var.set(thread_id)
            
        logger.debug("Initializing MCP client", extra_fields={
            "python_path": self.python_path,
            "server_script": self.server_script
        })
        
        self.server_params = StdioServerParameters(
            command=self.python_path,
            args=[self.server_script],
            env=os.environ.copy()
        )

    async def call_tool(self, tool_name: str, arguments: dict = None):
        """Generic method to call any MCP tool."""
        # Ensure thread_id is set for this context
        if self.thread_id:
            thread_id_var.set(self.thread_id)
            
        logger.info(f"Calling MCP tool: {tool_name}", extra_fields={"arguments": arguments})
        try:
            async with stdio_client(self.server_params) as (read, write):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    result = await session.call_tool(tool_name, arguments or {})
                    
                    # FastMCP tool results are typically in content[0].text
                    if hasattr(result, "content") and len(result.content) > 0:
                        text_result = result.content[0].text
                        logger.debug(f"MCP tool {tool_name} returned success", extra_fields={"result_length": len(text_result)})
                        return text_result
                    
                    logger.debug(f"MCP tool {tool_name} returned non-text result")
                    return str(result)
        except Exception as e:
            logger.error(f"Error calling MCP tool {tool_name}", extra_fields={"error": str(e)}, exc_info=True)
            return f"Error calling MCP tool {tool_name}: {e}"

    async def get_prs(self):
        """Fetch PRs from the MCP server."""
        return await self.call_tool("get_personal_records")

    async def query_diary(self, limit: int = 10, order: str = "desc"):
        """Execute a query on the fitness diary via MCP."""
        return await self.call_tool("query_fitness_diary", {"limit": limit, "order": order})

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
def get_mcp_client(thread_id: str = None):
    return MCPClient(thread_id=thread_id)
