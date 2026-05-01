import os
import sys
import json
from mcp.server.fastmcp import FastMCP
from supabase import create_client, Client

# Initialize FastMCP server
mcp = FastMCP("FitnessDataManager")

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

def get_supabase() -> Client:
    if not SUPABASE_URL or not SUPABASE_KEY:
        raise ValueError("SUPABASE_URL or SUPABASE_KEY is not set.")
    return create_client(SUPABASE_URL, SUPABASE_KEY)

@mcp.tool()
def get_personal_records() -> str:
    """Read the user's personal records (PRs) from the database."""
    try:
        supabase = get_supabase()
        response = supabase.table("personal_records").select("*").execute()
        if not response.data:
            return "No PR records found."
        return json.dumps(response.data)
    except Exception as e:
        return f"Database error: {str(e)}"

@mcp.tool()
def add_personal_record(exercise: str, weight: float, reps: int):
    """Log a new personal record to the database."""
    try:
        supabase = get_supabase()
        estimate_1rm = round(weight * (1 + reps/30), 2)
        
        supabase.table("personal_records").insert({
            "exercise": exercise,
            "weight": weight,
            "reps": reps,
            "1RM_Estimate": estimate_1rm
        }).execute()
        
        return f"Logged PR for {exercise}: {weight}kg x {reps}"
    except Exception as e:
        return f"Database error: {str(e)}"

@mcp.tool()
def query_fitness_diary(limit: int = 50) -> str:
    """Fetch the recent entries from the fitness diary database."""
    try:
        supabase = get_supabase()
        response = supabase.table("diary").select("*").order('date', desc=True).limit(limit).execute()
        if not response.data:
            return "No diary records found."
        return json.dumps(response.data)
    except Exception as e:
        return f"Database error: {str(e)}"

@mcp.tool()
def add_diary_entry(entry: str, calories: int, protein: int, weight: float = None, sleep_hours: float = 8.0, fatigue: int = 3):
    """Add a new daily entry to the fitness diary."""
    import datetime
    date = datetime.date.today().isoformat()
    try:
        supabase = get_supabase()
        supabase.table("diary").insert({
            "date": date,
            "entry": entry,
            "calories": calories,
            "protein": protein,
            "weight": weight,
            "sleep_hours": sleep_hours,
            "fatigue": fatigue
        }).execute()
        return f"Diary entry added for {date}"
    except Exception as e:
        return f"Database error: {str(e)}"

if __name__ == "__main__":
    print("Fitness MCP Server is running...", file=sys.stderr)
    mcp.run()
