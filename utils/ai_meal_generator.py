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
            self.model = genai.GenerativeModel('gemini-1.5-flash')
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
            
            # Extract text from response
            response_text = ""
            
            # Check if response has text
            if hasattr(response, 'text'):
                response_text = response.text
                print(f"Got response text directly: {len(response_text)} characters")
            
            # If no text, try to extract from candidates
            if not response_text and hasattr(response, 'candidates'):
                print(f"Checking candidates... found {len(response.candidates)}")
                for candidate in response.candidates:
                    if hasattr(candidate, 'content'):
                        if hasattr(candidate.content, 'parts'):
                            for part in candidate.content.parts:
                                if hasattr(part, 'text'):
                                    response_text += part.text
                                    print(f"Extracted {len(part.text)} characters from part")
            
            # If still no text, check for safety ratings or other issues
            if not response_text:
                print("No text found in response. Checking for safety issues...")
                if hasattr(response, 'prompt_feedback'):
                    print(f"Prompt feedback: {response.prompt_feedback}")
                if hasattr(response, 'candidates') and response.candidates:
                    for i, candidate in enumerate(response.candidates):
                        if hasattr(candidate, 'finish_reason'):
                            print(f"Candidate {i} finish reason: {candidate.finish_reason}")
                        if hasattr(candidate, 'safety_ratings'):
                            print(f"Candidate {i} safety ratings: {candidate.safety_ratings}")
            
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