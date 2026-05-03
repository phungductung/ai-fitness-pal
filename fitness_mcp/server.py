import os
import sys
import pandas as pd
from mcp.server.fastmcp import FastMCP
from supabase import create_client, Client
from dotenv import load_dotenv
from pydantic import ValidationError
import json

from schemas import (
    AddPersonalRecordMCPInput,
    QueryFitnessDiaryMCPInput,
    AddDiaryEntryMCPInput,
)

# Load environment variables
# Reaching out to the backend directory for .env where Supabase keys are stored
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "../backend/.env"))

# Initialize Supabase client
url: str = os.getenv("SUPABASE_URL")
key: str = os.getenv("SUPABASE_KEY")

if not url or not key:
    print("Warning: SUPABASE_URL or SUPABASE_KEY not found in .env", file=sys.stderr)

supabase: Client = create_client(url, key) if url and key else None

# Initialize FastMCP server
mcp = FastMCP("FitnessDataManager")

@mcp.tool()
def get_personal_records() -> str:
    """Read the user's personal records (PRs) from Supabase."""
    if not supabase:
        return "Supabase client not initialized. Check your .env file."
    try:
        # Join with exercises table to get the exercise name
        response = supabase.table("personal_records").select("date, weight, reps, one_rm_estimate, exercises(name)").order("date", desc=True).execute()
        
        # Map to PascalCase for frontend compatibility
        formatted_data = []
        for row in response.data:
            formatted_data.append({
                "Date": row.get("date"),
                "Exercise": row.get("exercises", {}).get("name") if row.get("exercises") else "Unknown",
                "Weight": row.get("weight"),
                "Reps": row.get("reps"),
                "1RM_Estimate": row.get("one_rm_estimate")
            })
        return json.dumps(formatted_data)
    except Exception as e:
        return f"Error fetching PRs from Supabase: {str(e)}"

@mcp.tool()
def add_personal_record(exercise: str, weight: float, reps: int):
    """Log a new personal record to Supabase.
    Args:
        exercise: Name of the exercise (e.g. 'Squat'). 1-100 chars.
        weight: Weight lifted in kg. Must be > 0 and <= 1000.
        reps: Number of reps. Must be between 1 and 100.
    """
    # --- Pydantic validation ---
    try:
        validated = AddPersonalRecordMCPInput(exercise=exercise, weight=weight, reps=reps)
    except ValidationError as e:
        return f"Input validation error: {e}"

    if not supabase:
        return "Supabase client not initialized."
    import datetime
    
    try:
        # 1. Get or create exercise ID
        ex_res = supabase.table("exercises").select("id").eq("name", validated.exercise).execute()
        if not ex_res.data:
            new_ex = supabase.table("exercises").insert({"name": validated.exercise}).execute()
            ex_id = new_ex.data[0]['id']
        else:
            ex_id = ex_res.data[0]['id']

        # 2. Insert the PR
        one_rm = round(validated.weight * (1 + validated.reps/30), 2)
        new_entry = {
            "date": datetime.date.today().isoformat(),
            "exercise_id": ex_id,
            "weight": validated.weight,
            "reps": validated.reps,
            "one_rm_estimate": one_rm
        }
        supabase.table("personal_records").insert(new_entry).execute()
        return f"Logged PR for {validated.exercise}: {validated.weight}kg x {validated.reps} (Est. 1RM: {one_rm}kg) to Supabase."
    except Exception as e:
        return f"Error logging PR to Supabase: {str(e)}"

@mcp.tool()
def query_fitness_diary(query: str = None) -> str:
    """
    Query the fitness diary for weight history, calories, and logs.
    Uses the aggregated compatibility view in Supabase.
    Args:
        query: Optional search/filter query (max 500 chars).
    """
    # --- Pydantic validation ---
    if query is not None:
        try:
            validated = QueryFitnessDiaryMCPInput(query=query)
        except ValidationError as e:
            return f"Input validation error: {e}"

    if not supabase:
        return "Supabase client not initialized."
    try:
        # Fetch from the view that combines nutrition_logs and body_metrics
        response = supabase.table("diary_entries_view").select("*").order("date", desc=True).limit(100).execute()
        if not response.data:
            return "No diary entries found in Supabase."
        
        return json.dumps(response.data)
    except Exception as e:
        return f"Error querying diary from Supabase: {str(e)}"

@mcp.tool()
def add_diary_entry(entry: str, calories: int, protein: int, weight: float = None, sleep_hours: float = 8.0, fatigue: int = 3):
    """Add a new daily entry to the fitness diary in Supabase.
    Args:
        entry: Meal/activity description. 1-1000 chars.
        calories: Calorie count (0-20000).
        protein: Protein in grams (0-2000).
        weight: Body weight in kg (20-500, optional).
        sleep_hours: Hours of sleep (0-24, default 8).
        fatigue: Fatigue level 1-5 (default 3).
    """
    # --- Pydantic validation ---
    try:
        validated = AddDiaryEntryMCPInput(
            entry=entry, calories=calories, protein=protein,
            weight=weight, sleep_hours=sleep_hours, fatigue=fatigue,
        )
    except ValidationError as e:
        return f"Input validation error: {e}"

    if not supabase:
        return "Supabase client not initialized."
    import datetime
    date = datetime.date.today().isoformat()
    
    try:
        # 1. Update/Insert body metrics
        supabase.table("body_metrics").upsert({
            "date": date,
            "weight": validated.weight,
            "sleep_hours": validated.sleep_hours,
            "fatigue_level": validated.fatigue
        }).execute()

        # 2. Insert nutrition log
        supabase.table("nutrition_logs").insert({
            "date": date,
            "entry_text": validated.entry,
            "calories": validated.calories,
            "protein_g": validated.protein
        }).execute()

        return f"Diary entry added to Supabase for {date}"
    except Exception as e:
        return f"Error adding diary entry to Supabase: {str(e)}"

if __name__ == "__main__":
    print("Fitness MCP Server (Supabase) is running...", file=sys.stderr)
    mcp.run()
