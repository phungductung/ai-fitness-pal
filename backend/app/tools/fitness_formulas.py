import math
import json


def calculate_tdee(weight_kg: float, height_cm: float, age: int, gender: str, activity_multiplier: float) -> str:
    """Calculate Total Daily Energy Expenditure using Mifflin-St Jeor Equation."""
    if gender.lower() == "male":
        bmr = (10 * weight_kg) + (6.25 * height_cm) - (5 * age) + 5
    else:
        bmr = (10 * weight_kg) + (6.25 * height_cm) - (5 * age) - 161
    tdee = round(bmr * activity_multiplier, 2)
    return (
        f"TDEE Calculation (Mifflin-St Jeor): "
        f"{gender}, {age}yo, {height_cm}cm, {weight_kg}kg, "
        f"activity multiplier {activity_multiplier}. "
        f"BMR = {round(bmr, 2)} kcal. "
        f"TDEE = {tdee} kcal/day."
    )


def calculate_1rm(weight: float, reps: int) -> str:
    """Calculate 1-Rep Max using the Epley formula."""
    if reps == 1:
        return f"Estimated 1RM for {weight}kg × {reps} rep = {weight} kg (single rep, no formula needed)."
    result = round(weight * (1 + reps / 30), 2)
    return (
        f"Estimated 1RM for {weight}kg × {reps} reps = {result} kg "
        f"(Epley formula: weight × (1 + reps/30))."
    )


def suggest_macros(tdee: float, goal: str) -> str:
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

    macros = {
        "calories": calories,
        "protein_g": round((calories * protein_p) / 4),
        "fat_g": round((calories * fat_p) / 9),
        "carbs_g": round((calories * carb_p) / 4),
    }
    return (
        f"Macro suggestion for '{goal}' goal with TDEE {tdee} kcal: "
        f"{json.dumps(macros)}. "
        f"Split: {int(protein_p*100)}% protein, {int(fat_p*100)}% fat, {int(carb_p*100)}% carbs."
    )
