# utils/diet_generator.py

def generate_diet(age, weight, day, dietary_type='omnivore'):
    # Example logic: Add vegetarian on Tue/Thu/Sat
    vegetarian_days = ["Tuesday", "Thursday", "Saturday"]
    is_veg_day = day in vegetarian_days

    plan = []

    # Base plans for different dietary types
    if dietary_type == 'vegetarian' or (dietary_type == 'omnivore' and is_veg_day):
        if weight < 50:
            plan.append("Breakfast: Banana smoothie with oats and nuts")
            plan.append("Lunch: Rice, dal, mixed vegetables, and yogurt")
            plan.append("Dinner: Khichdi with roasted vegetables and curd")
        elif weight < 70:
            plan.append("Breakfast: Poha with peanuts and vegetables")
            plan.append("Lunch: Roti, sabzi, dal, and paneer curry")
            plan.append("Dinner: Brown rice with vegetable curry and raita")
        else:
            plan.append("Breakfast: Oats with fruits and nuts")
            plan.append("Lunch: Quinoa salad with chickpeas and vegetables")
            plan.append("Dinner: Soup with multigrain bread and salad")
        plan.append("Note: Vegetarian meal plan for optimal nutrition.")
    
    elif dietary_type == 'vegan':
        if weight < 50:
            plan.append("Breakfast: Chia pudding with almond milk and berries")
            plan.append("Lunch: Rice, sambar, and stir-fried vegetables")
            plan.append("Dinner: Lentil soup with quinoa and salad")
        elif weight < 70:
            plan.append("Breakfast: Smoothie bowl with fruits and seeds")
            plan.append("Lunch: Buddha bowl with tofu and tahini dressing")
            plan.append("Dinner: Pasta with tomato sauce and nutritional yeast")
        else:
            plan.append("Breakfast: Overnight oats with plant milk and fruits")
            plan.append("Lunch: Chickpea curry with brown rice")
            plan.append("Dinner: Vegetable stir-fry with noodles")
        plan.append("Note: 100% plant-based vegan meal plan.")
    
    else:  # omnivore (non-veg days)
        if weight < 50:
            plan.append("Breakfast: Scrambled eggs with whole wheat toast")
            plan.append("Lunch: Chicken curry with rice and salad")
            plan.append("Dinner: Grilled fish with vegetables")
        elif weight < 70:
            plan.append("Breakfast: Poha with boiled eggs")
            plan.append("Lunch: Roti with chicken/mutton curry and vegetables")
            plan.append("Dinner: Egg curry with brown rice")
        else:
            plan.append("Breakfast: Omelette with multigrain bread")
            plan.append("Lunch: Grilled chicken salad with quinoa")
            plan.append("Dinner: Fish curry with steamed vegetables")
        plan.append("Note: Non-vegetarian meal plan with lean proteins.")

    # Add age-specific recommendations
    if age < 25:
        plan.append("Tip: Focus on protein-rich foods for growth and development.")
    elif age > 50:
        plan.append("Tip: Include calcium-rich foods and reduce sodium intake.")
    else:
        plan.append("Tip: Maintain balanced meals with adequate fiber.")

    return plan