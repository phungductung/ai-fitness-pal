import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import pandas as pd
import os

def generate_progress_chart(data_csv: str, exercise: str, output_path: str = "progress_chart.png"):
    """
    Generate a progress chart for a specific exercise from the CSV data.
    """
    if not os.path.exists(data_csv):
        return "Data file not found."
    
    df = pd.read_csv(data_csv)
    df['Date'] = pd.to_datetime(df['Date'])
    
    # Filter for the specific exercise
    exercise_df = df[df['Exercise'].str.lower() == exercise.lower()].sort_values('Date')
    
    if exercise_df.empty:
        return f"No data found for {exercise}."

    # Styling for a premium look
    plt.style.use('dark_background')
    fig, ax = plt.subplots(figsize=(10, 6))
    
    ax.plot(exercise_df['Date'], exercise_df['1RM_Estimate'], marker='o', linestyle='-', color='#00d4ff', linewidth=2, label='Est. 1RM')
    ax.fill_between(exercise_df['Date'], exercise_df['1RM_Estimate'], color='#00d4ff', alpha=0.1)
    
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
