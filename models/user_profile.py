# models/user_profile.py

from datetime import datetime

class UserProfile:
    """User profile schema for personalized diet planning"""
    
    @staticmethod
    def create_profile(data):
        """Create a new user profile with all dietary preferences"""
        return {
            'user_id': data.get('user_id'),
            'created_at': datetime.utcnow(),
            'updated_at': datetime.utcnow(),
            
            # Basic Information
            'age': data.get('age'),
            'weight': data.get('weight'),
            'height': data.get('height'),
            'gender': data.get('gender'),
            'activity_level': data.get('activity_level', 'moderate'),  # sedentary, light, moderate, active, very_active
            
            # Health Goals
            'goal': data.get('goal', 'maintain'),  # lose_weight, gain_weight, maintain, muscle_gain
            'target_weight': data.get('target_weight'),
            'weekly_goal': data.get('weekly_goal', 0.5),  # kg per week
            
            # Dietary Restrictions
            'dietary_type': data.get('dietary_type', 'omnivore'),  # vegetarian, vegan, pescatarian, omnivore
            'allergies': data.get('allergies', []),  # list of allergies
            'intolerances': data.get('intolerances', []),  # lactose, gluten, etc.
            'religious_restrictions': data.get('religious_restrictions'),  # halal, kosher, jain, hindu_vegetarian
            
            # Medical Conditions
            'medical_conditions': data.get('medical_conditions', []),  # diabetes, hypertension, cholesterol, etc.
            'medications': data.get('medications', []),
            
            # Food Preferences
            'liked_foods': data.get('liked_foods', []),
            'disliked_foods': data.get('disliked_foods', []),
            'cuisine_preferences': data.get('cuisine_preferences', []),  # indian, chinese, mediterranean, etc.
            'spice_tolerance': data.get('spice_tolerance', 'medium'),  # mild, medium, spicy
            
            # Lifestyle
            'meal_prep_time': data.get('meal_prep_time', 'medium'),  # quick, medium, elaborate
            'budget': data.get('budget', 'medium'),  # low, medium, high
            'cooking_skill': data.get('cooking_skill', 'intermediate'),  # beginner, intermediate, advanced
            
            # Meal Preferences
            'meals_per_day': data.get('meals_per_day', 3),
            'snacks_included': data.get('snacks_included', True),
            'water_intake_goal': data.get('water_intake_goal', 8),  # glasses per day
            
            # Calculated Fields
            'bmr': None,  # Basal Metabolic Rate
            'tdee': None,  # Total Daily Energy Expenditure
            'daily_calories': None,
            'macro_split': {
                'protein': 0.30,  # 30% of calories
                'carbs': 0.40,    # 40% of calories
                'fats': 0.30      # 30% of calories
            }
        }
    
    @staticmethod
    def calculate_nutrition_needs(profile):
        """Calculate BMR, TDEE, and calorie needs based on profile"""
        weight = profile['weight']
        height = profile['height']
        age = profile['age']
        gender = profile['gender']
        activity_level = profile['activity_level']
        goal = profile['goal']
        
        # Calculate BMR using Mifflin-St Jeor Equation
        if gender == 'male':
            bmr = 10 * weight + 6.25 * height - 5 * age + 5
        else:
            bmr = 10 * weight + 6.25 * height - 5 * age - 161
        
        # Activity multipliers
        activity_multipliers = {
            'sedentary': 1.2,
            'light': 1.375,
            'moderate': 1.55,
            'active': 1.725,
            'very_active': 1.9
        }
        
        tdee = bmr * activity_multipliers.get(activity_level, 1.55)
        
        # Adjust for goals
        if goal == 'lose_weight':
            daily_calories = tdee - 500  # 0.5kg loss per week
        elif goal == 'gain_weight':
            daily_calories = tdee + 500  # 0.5kg gain per week
        else:
            daily_calories = tdee
        
        # Update profile
        profile['bmr'] = round(bmr)
        profile['tdee'] = round(tdee)
        profile['daily_calories'] = round(daily_calories)
        
        # Calculate macros in grams
        protein_calories = daily_calories * profile['macro_split']['protein']
        carb_calories = daily_calories * profile['macro_split']['carbs']
        fat_calories = daily_calories * profile['macro_split']['fats']
        
        profile['daily_macros'] = {
            'protein_g': round(protein_calories / 4),  # 4 cal per gram
            'carbs_g': round(carb_calories / 4),      # 4 cal per gram
            'fats_g': round(fat_calories / 9)         # 9 cal per gram
        }
        
        return profile