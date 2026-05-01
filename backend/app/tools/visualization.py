import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import pandas as pd
import os
from supabase import create_client

def generate_progress_chart(exercise: str, output_path: str = "progress_chart.png"):
    """
    Generate a progress chart for a specific exercise from the database.
    """
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_KEY")
    if not supabase_url or not supabase_key:
        return "Database error: SUPABASE_URL or SUPABASE_KEY is not set."
    
    try:
        supabase = create_client(supabase_url, supabase_key)
        response = supabase.table("personal_records").select("*").ilike("exercise", f"%{exercise}%").order("date").execute()
        if not response.data:
            return f"No data found for {exercise}."
        
        df = pd.DataFrame(response.data)
    except Exception as e:
        return f"Database error: {str(e)}"

    df['date'] = pd.to_datetime(df['date'])
    
    # Styling for a premium look
    plt.style.use('dark_background')
    fig, ax = plt.subplots(figsize=(10, 6))
    
    ax.plot(df['date'], df['1RM_Estimate'], marker='o', linestyle='-', color='#00d4ff', linewidth=2, label='Est. 1RM')
    ax.fill_between(df['date'], df['1RM_Estimate'], color='#00d4ff', alpha=0.1)
    
    ax.set_title(f"Progress: {exercise.capitalize()}", fontsize=16, color='white', pad=20)
    ax.set_xlabel("Date", fontsize=12, color='gray')
    ax.set_ylabel("Weight (kg)", fontsize=12, color='gray')
    
    ax.grid(True, linestyle='--', alpha=0.3)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    
    plt.xticks(rotation=45)
    plt.tight_layout()
    
    plt.savefig(output_path)
    plt.close(fig)
    
    return f"Chart generated successfully at {output_path}"
