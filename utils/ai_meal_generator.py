# utils/ai_meal_generator.py

import google.generativeai as genai
import json
from datetime import datetime
from config import Config
import logging
import os

logger = logging.getLogger(__name__)

class AIMealGenerator:
    """AI-powered meal plan generator using Google Gemini (FREE!)"""
    
    def __init__(self):
        # Configure Gemini
        api_key = os.environ.get('GEMINI_API_KEY') or Config.GEMINI_API_KEY
        if api_key:
            genai.configure(api_key=api_key)
            # Use the correct model name
            self.model = genai.GenerativeModel('gemini-2.0-flash')
            self.initialized = True
            print(f"AI Generator initialized with API key: {api_key[:10]}...")
        else:
            logger.warning("No Gemini API key found. AI features will be limited.")
            self.initialized = False
    
    def generate_personalized_meal_plan(self, user_profile, day, meal_type=None):
        """Generate AI-powered personalized meal plan"""
        
        if not self.initialized:
            logger.warning("AI generator not initialized. Using fallback.")
            return self._fallback_meal_plan(user_profile, day)
        
        prompt = self._create_meal_prompt(user_profile, day, meal_type)
        
        try:
            # Generate content with the model
            print("Sending request to Gemini...")
            response = self.model.generate_content(
                prompt,
                generation_config=genai.types.GenerationConfig(
                    temperature=0.7,
                    top_p=0.95,
                    top_k=40,
                    max_output_tokens=2048,
                )
            )
            
            # Extract text from response - UPDATED HANDLING
            response_text = ""
            
            # Try to get text from parts as suggested by the error
            try:
                if hasattr(response, 'candidates') and response.candidates:
                    for candidate in response.candidates:
                        if hasattr(candidate, 'content') and hasattr(candidate.content, 'parts'):
                            for part in candidate.content.parts:
                                if hasattr(part, 'text'):
                                    response_text += part.text
                
                # If no text extracted, try the simple accessor as fallback
                if not response_text and hasattr(response, 'text'):
                    try:
                        response_text = response.text
                    except ValueError:
                        # This will catch the "not simple text" error
                        pass
                        
            except Exception as e:
                print(f"Error extracting text from Gemini response: {e}")
            
            if not response_text:
                print("No text extracted from Gemini response - using fallback")
                return self._fallback_meal_plan(user_profile, day)
            
            # Debug: Print what we got
            print(f"Gemini Response Preview: {response_text[:200]}...")
            
            parsed_response = self._parse_gemini_response(response_text)
            
            # Validate the response
            if self._validate_meal_plan(parsed_response):
                print("Successfully parsed AI response")
                return parsed_response
            else:
                print("Invalid meal plan structure, using fallback")
                return self._fallback_meal_plan(user_profile, day)
                
        except Exception as e:
            logger.error(f"Gemini generation error: {type(e).__name__}: {str(e)}")
            print(f"Full error: {e}")
            # Fallback to enhanced traditional method
            return self._fallback_meal_plan(user_profile, day)
    
    def _create_meal_prompt(self, profile, day, meal_type=None):
        """Create detailed prompt for AI meal generation"""
        
        # Extract key information
        dietary_type = profile.get('dietary_type', 'omnivore')
        cuisine_prefs = profile.get('cuisine_preferences', ['indian'])
        
        # Format cuisine preferences
        if cuisine_prefs:
            formatted_cuisines = [c.replace('_', ' ').title() for c in cuisine_prefs]
            cuisine_str = ', '.join(formatted_cuisines)
        else:
            cuisine_str = 'Indian'
        
        calories = profile.get('daily_calories', 2000)
        
        # Simplified prompt that's less likely to trigger safety filters
        prompt = f"""Create a {dietary_type} meal plan for {day} featuring {cuisine_str} cuisine.

Daily calorie target: {calories} calories

Please provide a JSON response with exactly 4 meals (breakfast, snack, lunch, dinner) in this format:

{{
    "meals": [
        {{
            "type": "breakfast",
            "name": "Dish Name",
            "description": "Brief description",
            "ingredients": ["ingredient1", "ingredient2", "ingredient3"],
            "calories": 400,
            "prep_time": "20 minutes",
            "macros": {{"protein": 20, "carbs": 50, "fats": 15}},
            "notes": "Preparation tip"
        }},
        {{
            "type": "snack",
            "name": "Snack Name",
            "description": "Brief description",
            "ingredients": ["ingredient1", "ingredient2"],
            "calories": 200,
            "prep_time": "5 minutes",
            "macros": {{"protein": 10, "carbs": 25, "fats": 8}},
            "notes": "Healthy snack"
        }},
        {{
            "type": "lunch",
            "name": "Dish Name",
            "description": "Brief description",
            "ingredients": ["ingredient1", "ingredient2", "ingredient3", "ingredient4"],
            "calories": 600,
            "prep_time": "30 minutes",
            "macros": {{"protein": 30, "carbs": 70, "fats": 20}},
            "notes": "Main meal"
        }},
        {{
            "type": "dinner",
            "name": "Dish Name",
            "description": "Brief description",
            "ingredients": ["ingredient1", "ingredient2", "ingredient3"],
            "calories": 500,
            "prep_time": "25 minutes",
            "macros": {{"protein": 25, "carbs": 55, "fats": 18}},
            "notes": "Light dinner"
        }}
    ],
    "total_nutrition": {{
        "calories": {calories},
        "protein": 85,
        "carbs": 200,
        "fats": 61
    }},
    "meal_plan_notes": "Daily meal plan for {dietary_type} diet with {cuisine_str} cuisine"
}}

Important: Ensure the meal plan is {dietary_type} (no meat for vegetarian, no animal products for vegan).
Focus on authentic {cuisine_str} dishes."""
        
        return prompt
    
    def _parse_gemini_response(self, response_text):
        """Parse Gemini response into structured format"""
        try:
            # Clean the response text
            cleaned_text = response_text.strip()
            
            # Remove markdown code blocks if present
            if '```json' in cleaned_text:
                start = cleaned_text.find('```json') + 7
                end = cleaned_text.rfind('```')
                if end > start:
                    cleaned_text = cleaned_text[start:end].strip()
            elif '```' in cleaned_text:
                start = cleaned_text.find('```') + 3
                end = cleaned_text.rfind('```')
                if end > start:
                    cleaned_text = cleaned_text[start:end].strip()
            
            # Try to find JSON object
            if '{' in cleaned_text and '}' in cleaned_text:
                start = cleaned_text.find('{')
                end = cleaned_text.rfind('}') + 1
                cleaned_text = cleaned_text[start:end]
            
            return json.loads(cleaned_text)
        except json.JSONDecodeError as e:
            logger.error(f"JSON parsing failed: {str(e)}")
            return None
    
    def _validate_meal_plan(self, meal_plan):
        """Validate that the meal plan has the required structure"""
        if not meal_plan or not isinstance(meal_plan, dict):
            return False
        
        # Check for required keys
        if 'meals' not in meal_plan or not isinstance(meal_plan['meals'], list):
            return False
        
        if len(meal_plan['meals']) == 0:
            return False
        
        # Validate each meal
        for meal in meal_plan['meals']:
            if not isinstance(meal, dict):
                return False
            required_keys = ['type', 'name', 'calories']
            if not all(key in meal for key in required_keys):
                return False
        
        return True
    
    def _fallback_meal_plan(self, user_profile, day):
        """Fallback meal plan when AI generation fails"""
        dietary_type = user_profile.get('dietary_type', 'omnivore')
        cuisine_prefs = user_profile.get('cuisine_preferences', ['indian'])
        calories = user_profile.get('daily_calories', 2000)
        
        # Create a structured meal plan that matches AI format
        meal_plan = {
            "meals": [],
            "total_nutrition": {
                "calories": calories,
                "protein": user_profile.get('daily_macros', {}).get('protein_g', 85),
                "carbs": user_profile.get('daily_macros', {}).get('carbs_g', 200),
                "fats": user_profile.get('daily_macros', {}).get('fats_g', 60)
            },
            "meal_plan_notes": f"Balanced {dietary_type} meal plan for {day}"
        }
        
        # Generate meals based on dietary type
        if dietary_type == 'vegetarian' or dietary_type == 'vegan':
            meal_plan["meals"] = [
                {
                    "type": "breakfast",
                    "name": "Oatmeal with Fruits and Nuts",
                    "description": "Healthy start with complex carbs and proteins",
                    "ingredients": ["Rolled oats", "Banana", "Almonds", "Honey", "Milk/Plant milk"],
                    "calories": int(calories * 0.25),
                    "prep_time": "15 minutes",
                    "macros": {"protein": 15, "carbs": 45, "fats": 10},
                    "notes": "Add seasonal fruits for variety"
                },
                {
                    "type": "snack",
                    "name": "Mixed Nuts and Fruit",
                    "description": "Energy boosting healthy snack",
                    "ingredients": ["Almonds", "Walnuts", "Dried dates", "Apple"],
                    "calories": int(calories * 0.15),
                    "prep_time": "2 minutes",
                    "macros": {"protein": 8, "carbs": 20, "fats": 8},
                    "notes": "Great for mid-morning energy"
                },
                {
                    "type": "lunch",
                    "name": "Dal Rice with Vegetables",
                    "description": "Traditional wholesome Indian meal",
                    "ingredients": ["Toor dal", "Rice", "Mixed vegetables", "Spices", "Ghee"],
                    "calories": int(calories * 0.35),
                    "prep_time": "30 minutes",
                    "macros": {"protein": 25, "carbs": 60, "fats": 15},
                    "notes": "Complete protein from dal and rice combination"
                },
                {
                    "type": "dinner",
                    "name": "Vegetable Curry with Roti",
                    "description": "Light and nutritious dinner",
                    "ingredients": ["Mixed vegetables", "Whole wheat flour", "Spices", "Oil", "Yogurt"],
                    "calories": int(calories * 0.25),
                    "prep_time": "25 minutes",
                    "macros": {"protein": 12, "carbs": 35, "fats": 10},
                    "notes": "Easy to digest evening meal"
                }
            ]
        else:  # omnivore
            meal_plan["meals"] = [
                {
                    "type": "breakfast",
                    "name": "Scrambled Eggs with Toast",
                    "description": "Protein-rich morning meal",
                    "ingredients": ["Eggs", "Whole wheat bread", "Butter", "Milk", "Salt", "Pepper"],
                    "calories": int(calories * 0.25),
                    "prep_time": "10 minutes",
                    "macros": {"protein": 20, "carbs": 30, "fats": 15},
                    "notes": "High protein start to the day"
                },
                {
                    "type": "snack",
                    "name": "Greek Yogurt with Berries",
                    "description": "Probiotic-rich healthy snack",
                    "ingredients": ["Greek yogurt", "Mixed berries", "Honey", "Granola"],
                    "calories": int(calories * 0.15),
                    "prep_time": "5 minutes",
                    "macros": {"protein": 10, "carbs": 20, "fats": 5},
                    "notes": "Good for digestive health"
                },
                {
                    "type": "lunch",
                    "name": "Grilled Chicken Salad",
                    "description": "Light yet filling lunch",
                    "ingredients": ["Chicken breast", "Mixed greens", "Vegetables", "Olive oil", "Lemon"],
                    "calories": int(calories * 0.35),
                    "prep_time": "20 minutes",
                    "macros": {"protein": 35, "carbs": 25, "fats": 20},
                    "notes": "Lean protein with fresh vegetables"
                },
                {
                    "type": "dinner",
                    "name": "Fish Curry with Brown Rice",
                    "description": "Omega-3 rich dinner",
                    "ingredients": ["Fish", "Brown rice", "Coconut milk", "Spices", "Vegetables"],
                    "calories": int(calories * 0.25),
                    "prep_time": "30 minutes",
                    "macros": {"protein": 25, "carbs": 40, "fats": 15},
                    "notes": "Heart-healthy dinner option"
                }
            ]
        
        # Adjust for vegan if needed
        if dietary_type == 'vegan':
            meal_plan["meals"][0]["ingredients"] = ["Rolled oats", "Banana", "Almonds", "Maple syrup", "Almond milk"]
            meal_plan["meals"][0]["notes"] = "Use plant-based milk for vegan option"
            meal_plan["meals"][3]["ingredients"] = ["Mixed vegetables", "Whole wheat flour", "Spices", "Oil", "Cashew cream"]
            meal_plan["meals"][3]["notes"] = "Cashew cream adds richness without dairy"
        
        return meal_plan