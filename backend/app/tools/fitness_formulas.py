import math

def calculate_tdee(weight_kg: float, height_cm: float, age: int, gender: str, activity_multiplier: float) -> float:
    """Calculate Total Daily Energy Expenditure using Mifflin-St Jeor Equation."""
    if gender.lower() == "male":
        bmr = (10 * weight_kg) + (6.25 * height_cm) - (5 * age) + 5
    else:
        bmr = (10 * weight_kg) + (6.25 * height_cm) - (5 * age) - 161
    return round(bmr * activity_multiplier, 2)

def calculate_1rm(weight: float, reps: int) -> float:
    """Calculate 1-Rep Max using the Epley formula."""
    if reps == 1: return weight
    return round(weight * (1 + reps/30), 2)

def suggest_macros(tdee: float, goal: str):
    """Suggest macros based on TDEE and goal (bulk, cut, maintain)."""
    if goal == "cut":
        calories = tdee - 500
        protein_p = 0.4; fat_p = 0.3; carb_p = 0.3
    elif goal == "bulk":
        calories = tdee + 300
        protein_p = 0.3; fat_p = 0.2; carb_p = 0.5
    else:
        calories = tdee
        protein_p = 0.3; fat_p = 0.3; carb_p = 0.4
    
    return {
        "calories": calories,
        "protein_g": round((calories * protein_p) / 4),
        "fat_g": round((calories * fat_p) / 9),
        "carbs_g": round((calories * carb_p) / 4)
    }
