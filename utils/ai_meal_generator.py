# utils/ai_meal_generator.py

import google.generativeai as genai
import json
import os
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

class AIMealGenerator:
    """AI-powered meal plan generator using Google Gemini."""

    def __init__(self):
        # Use your new Gemini API key here
        self.api_key = os.environ.get('GEMINI_API_KEY') or "AIzaSyBj_bwlNkl8NasqWfa4DBa1AVMMTOANfD0"
        if self.api_key:
            try:
                genai.configure(api_key=self.api_key)
                self.model = genai.GenerativeModel('gemini-1.5-flash')
                self.initialized = True
                print(f"✅ Gemini model initialized with API key: {self.api_key[:10]}...")
            except Exception as e:
                logger.error(f"Failed to initialize Gemini: {e}")
                self.initialized = False
        else:
            logger.warning("⚠️ No API key found for Gemini.")
            self.initialized = False

    def generate_personalized_meal_plan(self, user_profile, day, meal_type=None):
        if not self.initialized:
            return self._fallback_meal_plan(user_profile, day)

        prompt = self._create_prompt(user_profile, day, meal_type)

        try:
            print("🔍 Sending prompt to Gemini...")
            response = self.model.generate_content(
                prompt,
                generation_config=genai.types.GenerationConfig(
                    temperature=0.7,
                    top_p=0.9,
                    top_k=20,
                    max_output_tokens=1024  # Reduced to avoid OOM
                )
            )

            response_text = getattr(response, 'text', '').strip()
            if not response_text:
                logger.warning("Empty Gemini response received.")
                return self._fallback_meal_plan(user_profile, day)

            return {
                "day": day,
                "meal_type": meal_type or "All",
                "generated_plan": response_text,
                "timestamp": datetime.utcnow().isoformat()
            }

        except Exception as e:
            logger.error(f"❌ Gemini API call failed: {e}")
            return self._fallback_meal_plan(user_profile, day)

    def _create_prompt(self, profile, day, meal_type):
        cuisines = ', '.join(profile.get("cuisine_preferences", [])) or "any"
        diet_type = profile.get("dietary_type", "balanced")
        goal = profile.get("goal", "general wellness")

        return (
            f"Generate a 1-day {diet_type} meal plan with {meal_type or 'all meals'} "
            f"for a person trying to achieve '{goal}'. "
            f"Include only items from these cuisines: {cuisines}. "
            f"Keep the response compact and structured as:\n\n"
            f"Breakfast:\n- Item 1\n- Item 2\n\nLunch:\n- Item 1\n- Item 2\n\nDinner:\n- Item 1\n- Item 2\n"
        )

    def _fallback_meal_plan(self, profile, day):
        return {
            "day": day,
            "meal_type": "Fallback",
            "generated_plan": "Oats for breakfast, dal-chawal for lunch, and khichdi for dinner.",
            "note": "Fallback plan used due to API error or missing key.",
            "timestamp": datetime.utcnow().isoformat()
        }
