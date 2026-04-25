import os
import sys
import pandas as pd
import sqlite3
from mcp.server.fastmcp import FastMCP

# Initialize FastMCP server
mcp = FastMCP("FitnessDataManager")

# Path to local data
DB_PATH = os.path.join(os.path.dirname(__file__), "data/diary.sqlite")
CSV_PATH = os.path.join(os.path.dirname(__file__), "data/prs.csv")

@mcp.tool()
def get_personal_records() -> str:
    """Read the user's personal records (PRs) from the CSV file."""
    if not os.path.exists(CSV_PATH):
        return "No PR records found."
    df = pd.read_csv(CSV_PATH)
    return df.to_json(orient="records")

@mcp.tool()
def add_personal_record(exercise: str, weight: float, reps: int):
    """Log a new personal record to the CSV file."""
    import datetime
    new_entry = {
        "Date": datetime.date.today().isoformat(),
        "Exercise": exercise,
        "Weight": weight,
        "Reps": reps,
        "1RM_Estimate": round(weight * (1 + reps/30), 2)
    }
    df = pd.read_csv(CSV_PATH) if os.path.exists(CSV_PATH) else pd.DataFrame()
    df = pd.concat([df, pd.DataFrame([new_entry])], ignore_index=True)
    df.to_csv(CSV_PATH, index=False)
    return f"Logged PR for {exercise}: {weight}kg x {reps}"

@mcp.tool()
def query_fitness_diary(query: str) -> str:
    """Execute a SQL query on the fitness diary database."""
    conn = sqlite3.connect(DB_PATH)
    try:
        df = pd.read_sql_query(query, conn)
        return df.to_json(orient="records")
    finally:
        conn.close()

@mcp.tool()
def add_diary_entry(entry: str, calories: int, protein: int, weight: float = None, sleep_hours: float = 8.0, fatigue: int = 3):
    """Add a new daily entry to the fitness diary."""
    import datetime
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    date = datetime.date.today().isoformat()
    cursor.execute(
        "INSERT INTO diary (date, entry, calories, protein, weight, sleep_hours, fatigue) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (date, entry, calories, protein, weight, sleep_hours, fatigue)
    )
    conn.commit()
    conn.close()
    return f"Diary entry added for {date}"

if __name__ == "__main__":
    print("Fitness MCP Server is running...", file=sys.stderr)
    mcp.run()
