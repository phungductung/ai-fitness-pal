from app.tools.fitness_formulas import calculate_tdee, calculate_1rm, suggest_macros

def test_calculate_tdee_male():
    # Weight: 80kg, Height: 180cm, Age: 25, Gender: male, Activity: 1.2
    # BMR = (10 * 80) + (6.25 * 180) - (5 * 25) + 5
    # BMR = 800 + 1125 - 125 + 5 = 1805
    # TDEE = 1805 * 1.2 = 2166.0
    result = calculate_tdee(80, 180, 25, "male", 1.2)
    assert "2166.0" in result
    assert "Mifflin-St Jeor" in result

def test_calculate_tdee_female():
    # Weight: 60kg, Height: 165cm, Age: 30, Gender: female, Activity: 1.55
    # BMR = (10 * 60) + (6.25 * 165) - (5 * 30) - 161
    # BMR = 600 + 1031.25 - 150 - 161 = 1320.25
    # TDEE = 1320.25 * 1.55 = 2046.3875 -> 2046.39
    result = calculate_tdee(60, 165, 30, "female", 1.55)
    assert "2046.39" in result

def test_calculate_1rm():
    # Weight: 100, Reps: 5
    # 1RM = 100 * (1 + 5/30) = 100 * (1 + 0.1666...) = 116.666... -> 116.67
    result = calculate_1rm(100, 5)
    assert "116.67" in result
    assert "Epley" in result
    
    # Reps: 1
    result_single = calculate_1rm(100, 1)
    assert "100" in result_single

def test_suggest_macros_cut():
    tdee = 2500
    # Goal: cut -> calories = 2000
    # Protein: 40% -> 800 kcal / 4 = 200g
    # Fat: 30% -> 600 kcal / 9 = 67g
    # Carbs: 30% -> 600 kcal / 4 = 150g
    result = suggest_macros(tdee, "cut")
    assert "2000" in result
    assert "200" in result   # protein_g
    assert "67" in result    # fat_g
    assert "150" in result   # carbs_g
    assert "cut" in result

def test_suggest_macros_bulk():
    tdee = 2500
    # Goal: bulk -> calories = 2800
    # Protein: 30% -> 840 kcal / 4 = 210g
    # Fat: 20% -> 560 kcal / 9 = 62g
    # Carbs: 50% -> 1400 kcal / 4 = 350g
    result = suggest_macros(tdee, "bulk")
    assert "2800" in result
    assert "210" in result   # protein_g
    assert "62" in result    # fat_g
    assert "350" in result   # carbs_g
    assert "bulk" in result
