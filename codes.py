.env:
# MongoDB Configuration (using your existing URI)
MONGO_URI=mongodb+srv://dietadmi:dietpass123@cluster0.frfock5.mongodb.net/diet_planner?retryWrites=true&w=majority&appName=Cluster0

SECRET_KEY=your-random-secret-key


# Google Gemini API Configuration
# Get your free API key from: https://makersuite.google.com/app/apikey
GEMINI_API_KEY=AIzaSyBj_bwlNkl8NasqWfa4DBa1AVMMTOANfD0

# Gemini Model
GEMINI_MODEL=gemini-2.5-pro

# Feature Flags
ENABLE_AI_MEAL_PLANNING=true
ENABLE_NUTRITION_TRACKING=true

# Development Settings
FLASK_DEBUG=true

app.py:
from flask import Flask, render_template, request, session, redirect, url_for, flash
from flask_pymongo import PyMongo
from utils.diet_generator import generate_diet
from utils.ai_meal_generator import AIMealGenerator
from models.user_profile import UserProfile
import os
from datetime import datetime
from bson import json_util
import json

app = Flask(__name__)

# ✅ Configuration
app.config["MONGO_URI"] = os.environ.get("MONGO_URI") or "mongodb+srv://yashitiwary:9838yashi@cluster0.r5x2deh.mongodb.net/diet_planner?retryWrites=true&w=majority"
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-secret-key-change-this")

mongo = PyMongo(app)  # Initialize MongoDB
ai_generator = AIMealGenerator()  # Initialize AI Generator

# ✅ Home Page
@app.route('/')
def index():
    # Check if user has a profile
    has_profile = 'user_profile' in session and session['user_profile'] is not None
    profile_data = None
    
    if has_profile:
        profile_data = session.get('user_profile')
        # Debug print
        print(f"Profile found in session: {profile_data.get('age')} years old")
    
    return render_template('index.html', has_profile=has_profile, profile=profile_data)

# ✅ User Profile Page
@app.route('/profile')
def profile():
    # Pass existing profile data if available
    existing_profile = session.get('user_profile', None)
    return render_template('profile.html', profile=existing_profile)

# ✅ Save User Profile
@app.route('/save_profile', methods=['POST'])
def save_profile():
    try:
        # Create user profile from form data
        profile_data = {
            'age': int(request.form.get('age')),
            'weight': float(request.form.get('weight')),
            'height': float(request.form.get('height')),
            'gender': request.form.get('gender'),
            'activity_level': request.form.get('activity_level'),
            'goal': request.form.get('goal'),
            'dietary_type': request.form.get('dietary_type'),
            'allergies': request.form.getlist('allergies'),
            'medical_conditions': request.form.getlist('medical_conditions'),
            'cuisine_preferences': request.form.getlist('cuisine_preferences'),
            'spice_tolerance': request.form.get('spice_tolerance'),
            'meal_prep_time': request.form.get('meal_prep_time'),
            'cooking_skill': request.form.get('cooking_skill')
        }
        
        # Debug print
        print(f"Creating profile with data: {profile_data}")
        
        # Create and calculate profile
        profile = UserProfile.create_profile(profile_data)
        profile = UserProfile.calculate_nutrition_needs(profile)
        
        # Save to MongoDB
        result = mongo.db.profiles.insert_one(profile)
        
        # Store profile in session WITHOUT the MongoDB _id
        profile_for_session = profile.copy()
        if '_id' in profile_for_session:
            profile_for_session['_id'] = str(profile_for_session['_id'])
        
        session['user_profile'] = profile_for_session
        session['profile_id'] = str(result.inserted_id)
        session.permanent = True  # Make session persistent
        
        # Debug print
        print(f"Profile saved to session: {session.get('user_profile')}")
        
        flash('Profile created successfully! Your AI meal plans will now be personalized.', 'success')
        return redirect(url_for('profile_created'))
        
    except Exception as e:
        print(f"Error creating profile: {str(e)}")
        flash(f'Error creating profile: {str(e)}', 'error')
        return redirect(url_for('profile'))

# ✅ Profile Created Success Page
@app.route('/profile_created')
def profile_created():
    if 'user_profile' not in session:
        return redirect(url_for('profile'))
    
    profile = session.get('user_profile')
    return render_template('profile_created.html', profile=profile)

# ✅ Handle Form Submission
@app.route('/generate', methods=['POST'])
def generate():
    try:
        day = request.form['day']
        
        # Check if user has a profile
        if 'user_profile' in session and session['user_profile'] is not None:
            user_profile = session['user_profile']
            print("Using saved profile:", user_profile.get('age'), user_profile.get('dietary_type'))
        else:
            # Get data from quick form
            quick_dietary_type = request.form.get('quick_dietary_type', 'omnivore')
            quick_cuisines = request.form.getlist('quick_cuisine')
            
            # Create basic profile from form with new fields
            user_profile = UserProfile.create_profile({
                'age': int(request.form.get('age', 25)),
                'weight': float(request.form.get('weight', 70)),
                'height': float(request.form.get('height', 170)),
                'gender': 'unspecified',
                'activity_level': 'moderate',
                'goal': 'maintain',
                'dietary_type': quick_dietary_type,
                'cuisine_preferences': quick_cuisines if quick_cuisines else ['indian', 'continental']
            })
            user_profile = UserProfile.calculate_nutrition_needs(user_profile)
            print(f"Using quick profile with diet type: {quick_dietary_type} and cuisines: {quick_cuisines}")
        
        # Check if AI generator is properly initialized
        if not os.environ.get('GEMINI_API_KEY'):
            flash('Gemini API key not found! Using basic meal plan.', 'warning')
            raise Exception("No API key")
        
        # Generate AI-powered diet plan
        diet_plan = ai_generator.generate_personalized_meal_plan(user_profile, day)
        
        # Save to MongoDB
        plan_doc = {
            'profile_id': session.get('profile_id'),
            'day': day,
            'diet_plan': diet_plan,
            'created_at': datetime.utcnow()
        }
        mongo.db.plans.insert_one(plan_doc)
        
        return render_template('ai_result.html', 
                             diet_plan=diet_plan, 
                             profile=user_profile, 
                             day=day)

    except Exception as e:
        print(f"Error generating meal plan: {str(e)}")
        # Fallback to simple diet generation
        age = int(request.form.get('age', 25))
        weight = float(request.form.get('weight', 70))
        dietary_type = request.form.get('quick_dietary_type', 'omnivore')
        diet_chart = generate_diet(age, weight, day, dietary_type)
        
        return render_template('result.html', 
                             diet=diet_chart, 
                             age=age, 
                             weight=weight, 
                             day=day,
                             error=str(e))

# ✅ Clear Profile
@app.route('/clear_profile')
def clear_profile():
    session.clear()
    flash('Profile cleared successfully!', 'info')
    return redirect(url_for('index'))

# ✅ Run App
if __name__ == '__main__':
    # Load environment variables
    from dotenv import load_dotenv
    load_dotenv()
    
    # Set session to be permanent
    app.permanent_session_lifetime = 86400  # 24 hours
    
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)

config.py:
# config.py

import os

class Config:
    # MongoDB Configuration
    MONGO_URI = os.environ.get("MONGO_URI") or "mongodb+srv://yashitiwary:9838yashi@cluster0.r5x2deh.mongodb.net/diet_planner?retryWrites=true&w=majority"
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-key-change-this")
    
    # Google Gemini Configuration (FREE!)
    GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "AIzaSyAu4Oddsfl1HNGmHR6ya5BzJ1fPSAkK240")
    GEMINI_MODEL = "gemini-2.0-flash"
    
    # AI Configuration
    AI_TEMPERATURE = 0.7  # Creativity level for meal generation
    AI_MAX_TOKENS = 2000  # Max response length
    
    # Rate Limiting for AI API calls
    AI_RATE_LIMIT_PER_USER = 50  # Gemini has generous free tier
    
    # Caching
    CACHE_EXPIRY = 3600  # 1 hour cache for AI responses
    
    # Meal Planning Defaults
    DEFAULT_CUISINE_STYLE = "international"
    DEFAULT_MEAL_COMPLEXITY = "medium"
    MAX_INGREDIENTS_PER_MEAL = 12
    
    # Feature Flags
    ENABLE_AI_MEAL_PLANNING = os.environ.get("ENABLE_AI_MEAL_PLANNING", "true").lower() == "true"
    ENABLE_NUTRITION_TRACKING = os.environ.get("ENABLE_NUTRITION_TRACKING", "true").lower() == "true"
    
    # Development/Production
    DEBUG = os.environ.get("FLASK_DEBUG", "true").lower() == "true"
    TESTING = os.environ.get("TESTING", "false").lower() == "true"
    
    # Session Configuration
    SESSION_TYPE = 'filesystem'
    PERMANENT_SESSION_LIFETIME = 86400  # 24 hours in seconds

README.md:
# diet-planner

Something.py:
import os
import tkinter as tk
from tkinter import filedialog, scrolledtext, messagebox
import threading

class CodeScannerGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Code Scanner for AI")
        self.root.geometry("800x600")
        
        # Create menu frame
        menu_frame = tk.Frame(root)
        menu_frame.pack(fill=tk.X, padx=10, pady=10)
        
        # Directory selection
        tk.Label(menu_frame, text="Directory:").pack(side=tk.LEFT, padx=5)
        self.dir_var = tk.StringVar()
        tk.Entry(menu_frame, textvariable=self.dir_var, width=50).pack(side=tk.LEFT, padx=5)
        tk.Button(menu_frame, text="Browse", command=self.browse_directory).pack(side=tk.LEFT, padx=5)
        tk.Button(menu_frame, text="Scan", command=self.start_scan, bg="green", fg="white").pack(side=tk.LEFT, padx=5)
        
        # Output text area
        self.output_text = scrolledtext.ScrolledText(root, wrap=tk.WORD)
        self.output_text.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Button frame
        button_frame = tk.Frame(root)
        button_frame.pack(fill=tk.X, padx=10, pady=10)
        
        tk.Button(button_frame, text="Copy to Clipboard", command=self.copy_to_clipboard).pack(side=tk.LEFT, padx=5)
        tk.Button(button_frame, text="Save to File", command=self.save_to_file).pack(side=tk.LEFT, padx=5)
        tk.Button(button_frame, text="Clear", command=self.clear_output).pack(side=tk.LEFT, padx=5)
        
        # Status label
        self.status_label = tk.Label(root, text="Ready", bd=1, relief=tk.SUNKEN, anchor=tk.W)
        self.status_label.pack(side=tk.BOTTOM, fill=tk.X)
    
    def browse_directory(self):
        directory = filedialog.askdirectory()
        if directory:
            self.dir_var.set(directory)
    
    def start_scan(self):
        directory = self.dir_var.get()
        if not directory or not os.path.exists(directory):
            messagebox.showerror("Error", "Please select a valid directory")
            return
        
        # Run scan in separate thread to prevent GUI freezing
        threading.Thread(target=self.scan_directory, args=(directory,), daemon=True).start()
    
    def scan_directory(self, directory):
        self.status_label.config(text="Scanning...")
        self.output_text.delete(1.0, tk.END)
        
        output_lines = []
        file_count = 0
        
        skip_dirs = {
            '__pycache__', '.git', '.vscode', '.idea', 'node_modules',
            'venv', 'env', '.env', 'dist', 'build', '.pytest_cache'
        }
        
        skip_extensions = {
            '.pyc', '.pyo', '.exe', '.dll', '.so', '.dylib',
            '.jpg', '.jpeg', '.png', '.gif', '.bmp', '.ico',
            '.mp3', '.mp4', '.avi', '.mov', '.pdf', '.zip',
            '.tar', '.gz', '.rar', '.7z', '.db', '.sqlite'
        }
        
        for root, dirs, files in os.walk(directory):
            dirs[:] = [d for d in dirs if d not in skip_dirs]
            
            for file in files:
                file_path = os.path.join(root, file)
                relative_path = os.path.relpath(file_path, directory)
                
                _, ext = os.path.splitext(file.lower())
                if ext in skip_extensions:
                    continue
                
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    output_lines.append(f"{relative_path}:")
                    output_lines.append(content)
                    output_lines.append("")
                    
                    file_count += 1
                    self.status_label.config(text=f"Processed {file_count} files... Current: {relative_path}")
                    
                except Exception:
                    continue
        
        # Update output text
        final_output = "\n".join(output_lines)
        self.output_text.insert(1.0, final_output)
        self.status_label.config(text=f"Scan complete! Processed {file_count} files.")
    
    def copy_to_clipboard(self):
        content = self.output_text.get(1.0, tk.END)
        self.root.clipboard_clear()
        self.root.clipboard_append(content)
        self.status_label.config(text="Copied to clipboard!")
    
    def save_to_file(self):
        content = self.output_text.get(1.0, tk.END)
        file_path = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")]
        )
        if file_path:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            self.status_label.config(text=f"Saved to {file_path}")
    
    def clear_output(self):
        self.output_text.delete(1.0, tk.END)
        self.status_label.config(text="Output cleared")

if __name__ == "__main__":
    root = tk.Tk()
    app = CodeScannerGUI(root)
    root.mainloop()

models\user_profile.py:
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

models\__init__.py:
# models/__init__.py

"""
Models package for the AI Diet Planner application.
"""

from .user_profile import UserProfile

__all__ = ['UserProfile']

static\css\style.css:
body {
    font-family: 'Segoe UI', sans-serif;
    background: linear-gradient(to right, #89f7fe, #66a6ff);
    margin: 0;
    padding: 40px;
    color: #333;
}

.container {
    max-width: 500px;
    margin: auto;
    background: #fff;
    padding: 30px;
    border-radius: 15px;
    box-shadow: 0 0 20px rgba(0,0,0,0.1);
}

input, button {
    display: block;
    width: 100%;
    margin-bottom: 15px;
    padding: 10px;
    border-radius: 10px;
    border: 1px solid #ccc;
}

button {
    background: #4CAF50;
    color: white;
    font-weight: bold;
    cursor: pointer;
}

.card {
    padding: 20px;
    background: #f1f1f1;
    border-radius: 10px;
}


templates\ai_result.html:
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Your AI-Generated Meal Plan</title>
    <style>
        body {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            font-family: 'Segoe UI', sans-serif;
            margin: 0;
            padding: 20px;
            min-height: 100vh;
        }

        .container {
            max-width: 1000px;
            margin: auto;
            background: white;
            padding: 40px;
            border-radius: 20px;
            box-shadow: 0 20px 40px rgba(0, 0, 0, 0.1);
        }

        .header {
            text-align: center;
            margin-bottom: 40px;
        }

        h1 {
            color: #333;
            margin-bottom: 10px;
        }

        .subtitle {
            color: #666;
            font-size: 18px;
        }

        .nutrition-summary {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
            border-radius: 15px;
            margin-bottom: 30px;
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            text-align: center;
        }

        .nutrition-item {
            padding: 20px;
            background: rgba(255, 255, 255, 0.1);
            border-radius: 10px;
            backdrop-filter: blur(10px);
        }

        .nutrition-value {
            font-size: 36px;
            font-weight: bold;
            margin-bottom: 5px;
        }

        .nutrition-label {
            font-size: 14px;
            opacity: 0.9;
        }

        .meal-card {
            background: #f8f9fa;
            border-radius: 15px;
            padding: 30px;
            margin-bottom: 20px;
            position: relative;
            overflow: hidden;
            transition: transform 0.3s, box-shadow 0.3s;
        }

        .meal-card:hover {
            transform: translateY(-5px);
            box-shadow: 0 10px 30px rgba(0, 0, 0, 0.1);
        }

        .meal-type {
            display: inline-block;
            background: #667eea;
            color: white;
            padding: 5px 15px;
            border-radius: 20px;
            font-size: 12px;
            font-weight: bold;
            text-transform: uppercase;
            margin-bottom: 10px;
        }

        .meal-name {
            font-size: 24px;
            font-weight: bold;
            color: #333;
            margin-bottom: 10px;
        }

        .meal-description {
            color: #666;
            margin-bottom: 20px;
            line-height: 1.6;
        }

        .meal-details {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin-bottom: 20px;
        }

        .detail-section {
            background: white;
            padding: 15px;
            border-radius: 10px;
            box-shadow: 0 2px 5px rgba(0, 0, 0, 0.05);
        }

        .detail-title {
            font-weight: bold;
            color: #4a5568;
            margin-bottom: 10px;
            display: flex;
            align-items: center;
        }

        .detail-title i {
            margin-right: 8px;
            color: #667eea;
        }

        .ingredients-list {
            list-style: none;
            padding: 0;
            margin: 0;
        }

        .ingredients-list li {
            padding: 5px 0;
            padding-left: 20px;
            position: relative;
        }

        .ingredients-list li:before {
            content: '•';
            color: #667eea;
            font-weight: bold;
            position: absolute;
            left: 0;
        }

        .macro-grid {
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 10px;
            text-align: center;
        }

        .macro-item {
            padding: 10px;
            background: #f0f4f8;
            border-radius: 8px;
        }

        .macro-value {
            font-size: 18px;
            font-weight: bold;
            color: #667eea;
        }

        .macro-label {
            font-size: 12px;
            color: #666;
        }

        .meal-notes {
            background: #e6f3ff;
            border-left: 4px solid #3182ce;
            padding: 15px;
            border-radius: 5px;
            margin-top: 15px;
        }

        .meal-notes p {
            margin: 0;
            color: #2c5282;
            font-size: 14px;
        }

        .action-buttons {
            display: flex;
            gap: 15px;
            justify-content: center;
            margin-top: 30px;
        }

        .btn {
            padding: 12px 30px;
            border-radius: 10px;
            text-decoration: none;
            font-weight: bold;
            transition: all 0.3s;
            display: inline-flex;
            align-items: center;
            gap: 8px;
        }

        .btn-primary {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
        }

        .btn-secondary {
            background: white;
            color: #667eea;
            border: 2px solid #667eea;
        }

        .btn:hover {
            transform: translateY(-2px);
            box-shadow: 0 5px 15px rgba(102, 126, 234, 0.3);
        }

        .profile-summary {
            background: #f0f4f8;
            padding: 20px;
            border-radius: 10px;
            margin-bottom: 30px;
            display: flex;
            justify-content: space-around;
            flex-wrap: wrap;
            gap: 15px;
        }

        .profile-item {
            text-align: center;
        }

        .profile-label {
            font-size: 12px;
            color: #666;
            text-transform: uppercase;
            letter-spacing: 1px;
        }

        .profile-value {
            font-size: 18px;
            font-weight: bold;
            color: #333;
        }

        .ai-badge {
            display: inline-flex;
            align-items: center;
            background: #f0f4f8;
            padding: 5px 15px;
            border-radius: 20px;
            font-size: 12px;
            color: #667eea;
            margin-left: 10px;
        }

        @media (max-width: 768px) {
            .container {
                padding: 20px;
            }
            
            .nutrition-summary {
                grid-template-columns: 1fr;
            }
            
            .meal-details {
                grid-template-columns: 1fr;
            }
        }
    </style>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css">
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🎯 Your AI-Generated Meal Plan 
                <span class="ai-badge">
                    <i class="fas fa-robot"></i> Powered by Gemini AI
                </span>
            </h1>
            <p class="subtitle">Personalized nutrition for {{ day }}</p>
        </div>

        <!-- Profile Summary -->
        <div class="profile-summary">
            <div class="profile-item">
                <div class="profile-label">Age</div>
                <div class="profile-value">{{ profile.age }} years</div>
            </div>
            <div class="profile-item">
                <div class="profile-label">Weight</div>
                <div class="profile-value">{{ profile.weight }} kg</div>
            </div>
            <div class="profile-item">
                <div class="profile-label">Goal</div>
                <div class="profile-value">{{ profile.goal.replace('_', ' ').title() }}</div>
            </div>
            <div class="profile-item">
                <div class="profile-label">Diet Type</div>
                <div class="profile-value">{{ profile.dietary_type.title() }}</div>
            </div>
            <div class="profile-item">
                <div class="profile-label">Activity</div>
                <div class="profile-value">{{ profile.activity_level.title() }}</div>
            </div>
        </div>

        <!-- Nutrition Summary -->
        <div class="nutrition-summary">
            <div class="nutrition-item">
                <div class="nutrition-value">{{ diet_plan.total_nutrition.calories }}</div>
                <div class="nutrition-label">Daily Calories</div>
            </div>
            <div class="nutrition-item">
                <div class="nutrition-value">{{ diet_plan.total_nutrition.protein }}g</div>
                <div class="nutrition-label">Protein</div>
            </div>
            <div class="nutrition-item">
                <div class="nutrition-value">{{ diet_plan.total_nutrition.carbs }}g</div>
                <div class="nutrition-label">Carbohydrates</div>
            </div>
            <div class="nutrition-item">
                <div class="nutrition-value">{{ diet_plan.total_nutrition.fats }}g</div>
                <div class="nutrition-label">Healthy Fats</div>
            </div>
        </div>

        <!-- Meal Cards -->
        {% for meal in diet_plan.meals %}
        <div class="meal-card">
            <span class="meal-type">{{ meal.type }}</span>
            <h2 class="meal-name">{{ meal.name }}</h2>
            <p class="meal-description">{{ meal.description }}</p>
            
            <div class="meal-details">
                <div class="detail-section">
                    <div class="detail-title">
                        <i class="fas fa-carrot"></i> Ingredients
                    </div>
                    <ul class="ingredients-list">
                        {% for ingredient in meal.ingredients %}
                        <li>{{ ingredient }}</li>
                        {% endfor %}
                    </ul>
                </div>
                
                <div class="detail-section">
                    <div class="detail-title">
                        <i class="fas fa-chart-pie"></i> Nutrition Info
                    </div>
                    <div class="macro-grid">
                        <div class="macro-item">
                            <div class="macro-value">{{ meal.calories }}</div>
                            <div class="macro-label">Calories</div>
                        </div>
                        <div class="macro-item">
                            <div class="macro-value">{{ meal.macros.protein }}g</div>
                            <div class="macro-label">Protein</div>
                        </div>
                        <div class="macro-item">
                            <div class="macro-value">{{ meal.macros.carbs }}g</div>
                            <div class="macro-label">Carbs</div>
                        </div>
                    </div>
                    <div style="margin-top: 10px; text-align: center;">
                        <i class="fas fa-clock"></i> Prep Time: {{ meal.prep_time }}
                    </div>
                </div>
            </div>
            
            {% if meal.notes %}
            <div class="meal-notes">
                <p><i class="fas fa-lightbulb"></i> {{ meal.notes }}</p>
            </div>
            {% endif %}
        </div>
        {% endfor %}

        <!-- Overall Plan Notes -->
        {% if diet_plan.meal_plan_notes %}
        <div class="meal-card" style="background: #e6f3ff;">
            <h3 style="color: #2c5282; margin-bottom: 10px;">
                <i class="fas fa-info-circle"></i> Meal Plan Notes
            </h3>
            <p style="color: #2c5282; margin: 0;">{{ diet_plan.meal_plan_notes }}</p>
        </div>
        {% endif %}

        <!-- Action Buttons -->
        <div class="action-buttons">
            <a href="/" class="btn btn-secondary">
                <i class="fas fa-arrow-left"></i> Back to Planner
            </a>
            <a href="/profile" class="btn btn-primary">
                <i class="fas fa-user-edit"></i> Update Profile
            </a>
            <a href="#" class="btn btn-primary" onclick="window.print()">
                <i class="fas fa-download"></i> Save Plan
            </a>
        </div>
    </div>
</body>
</html>

templates\base.html:
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Diet Planner</title>
    <link rel="stylesheet" href="{{ url_for('static', filename='css/style.css') }}">
</head>
<body>
    <div class="container">
        <h1>Diet Planner</h1>
        {% block content %}{% endblock %}
    </div>
</body>
</html>


templates\dashboard.html:
{% extends "base.html" %}
{% block content %}
<h2>Hello {{ name }}, here's your diet for {{ day }}</h2>
<div class="card">
    {% for meal, item in diet.items() %}
        <p><strong>{{ meal }}:</strong> {{ item }}</p>
    {% endfor %}
</div>
<a href="/">Plan Again</a>
{% endblock %}


templates\index.html:
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>AI Diet Planner - Powered by Gemini</title>
    <style>
        body {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            font-family: 'Segoe UI', sans-serif;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            min-height: 100vh;
            margin: 0;
            padding: 20px;
        }

        .container {
            background: white;
            padding: 40px;
            border-radius: 20px;
            box-shadow: 0 20px 40px rgba(0, 0, 0, 0.1);
            text-align: center;
            width: 100%;
            max-width: 500px;
            animation: slideUp 0.5s ease;
        }

        @keyframes slideUp {
            from {
                transform: translateY(40px);
                opacity: 0;
            }
            to {
                transform: translateY(0);
                opacity: 1;
            }
        }

        h1 {
            margin-bottom: 10px;
            color: #333;
            font-size: 32px;
        }

        .subtitle {
            color: #666;
            margin-bottom: 30px;
            font-size: 16px;
        }

        .ai-badge {
            display: inline-flex;
            align-items: center;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 8px 20px;
            border-radius: 25px;
            font-size: 14px;
            margin-bottom: 30px;
            gap: 8px;
            animation: pulse 2s infinite;
        }

        @keyframes pulse {
            0% {
                box-shadow: 0 0 0 0 rgba(102, 126, 234, 0.4);
            }
            70% {
                box-shadow: 0 0 0 10px rgba(102, 126, 234, 0);
            }
            100% {
                box-shadow: 0 0 0 0 rgba(102, 126, 234, 0);
            }
        }

        .profile-status {
            background: linear-gradient(135deg, #48bb78 0%, #38a169 100%);
            color: white;
            padding: 20px;
            border-radius: 15px;
            margin-bottom: 30px;
            animation: fadeIn 0.5s ease;
        }

        @keyframes fadeIn {
            from {
                opacity: 0;
            }
            to {
                opacity: 1;
            }
        }

        .profile-status h3 {
            margin: 0 0 10px 0;
            font-size: 20px;
        }

        .profile-info {
            display: flex;
            justify-content: space-around;
            flex-wrap: wrap;
            gap: 15px;
            margin-top: 15px;
        }

        .profile-stat {
            background: rgba(255, 255, 255, 0.2);
            padding: 10px 20px;
            border-radius: 10px;
            backdrop-filter: blur(10px);
        }

        .profile-stat-value {
            font-size: 18px;
            font-weight: bold;
        }

        .profile-stat-label {
            font-size: 12px;
            opacity: 0.9;
        }

        .form-section {
            background: #f8f9fa;
            padding: 20px;
            border-radius: 15px;
            margin-bottom: 20px;
        }

        label {
            display: block;
            margin: 15px 0 5px;
            font-weight: bold;
            color: #555;
            text-align: left;
        }

        input, select {
            width: 100%;
            padding: 12px;
            margin-bottom: 10px;
            border-radius: 10px;
            border: 2px solid #e2e8f0;
            font-size: 16px;
            transition: border-color 0.3s;
        }

        input:focus, select:focus {
            outline: none;
            border-color: #667eea;
            box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
        }

        .radio-group {
            display: flex;
            gap: 15px;
            justify-content: center;
            margin: 10px 0;
        }

        .radio-item {
            display: flex;
            align-items: center;
            background: white;
            padding: 10px 15px;
            border-radius: 10px;
            border: 2px solid #e2e8f0;
            cursor: pointer;
            transition: all 0.3s;
        }

        .radio-item:hover {
            border-color: #667eea;
            transform: translateY(-2px);
        }

        .radio-item input[type="radio"] {
            width: auto;
            margin: 0 8px 0 0;
        }

        .radio-item label {
            margin: 0;
            cursor: pointer;
            font-weight: normal;
        }

        .radio-item.selected {
            border-color: #667eea;
            background: #f0f4ff;
        }

        button {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 15px 30px;
            border: none;
            border-radius: 10px;
            font-size: 16px;
            font-weight: bold;
            cursor: pointer;
            transition: all 0.3s;
            width: 100%;
            margin-top: 10px;
        }

        button:hover {
            transform: translateY(-2px);
            box-shadow: 0 10px 25px rgba(102, 126, 234, 0.3);
        }

        .profile-prompt {
            background: #e6f3ff;
            border: 2px dashed #3182ce;
            padding: 20px;
            border-radius: 15px;
            margin-bottom: 20px;
            text-align: center;
        }

        .profile-prompt h3 {
            color: #2c5282;
            margin-bottom: 10px;
        }

        .profile-prompt p {
            color: #2c5282;
            margin-bottom: 15px;
            font-size: 14px;
        }

        .btn-profile {
            background: #3182ce;
            color: white;
            padding: 10px 25px;
            border-radius: 8px;
            text-decoration: none;
            display: inline-block;
            transition: all 0.3s;
            font-weight: bold;
        }

        .btn-profile:hover {
            background: #2c5282;
            transform: translateY(-2px);
        }

        .profile-actions {
            display: flex;
            gap: 10px;
            justify-content: center;
            margin-top: 10px;
        }

        .btn-secondary {
            background: #e53e3e;
            color: white;
            padding: 8px 20px;
            border-radius: 8px;
            text-decoration: none;
            font-size: 14px;
            transition: all 0.3s;
        }

        .btn-secondary:hover {
            background: #c53030;
            transform: translateY(-2px);
        }

        footer {
            margin-top: 30px;
            font-size: 12px;
            color: #666;
        }

        .features {
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 15px;
            margin-bottom: 30px;
        }

        .feature-item {
            background: #f0f4f8;
            padding: 15px;
            border-radius: 10px;
            text-align: center;
            transition: transform 0.3s;
        }

        .feature-item:hover {
            transform: translateY(-3px);
        }

        .feature-icon {
            font-size: 24px;
            margin-bottom: 5px;
        }

        .feature-text {
            font-size: 12px;
            color: #666;
        }

        .divider {
            margin: 30px 0;
            position: relative;
            text-align: center;
        }

        .divider::before {
            content: '';
            position: absolute;
            top: 50%;
            left: 0;
            right: 0;
            height: 1px;
            background: #e2e8f0;
        }

        .divider span {
            background: white;
            padding: 0 15px;
            position: relative;
            color: #666;
            font-size: 14px;
        }

        .quick-form-info {
            background: #fef3c7;
            padding: 10px;
            border-radius: 8px;
            margin-bottom: 20px;
            font-size: 13px;
            color: #92400e;
        }

        .cuisine-grid {
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 10px;
            margin: 10px 0;
        }

        .cuisine-item {
            background: white;
            padding: 8px;
            border: 2px solid #e2e8f0;
            border-radius: 8px;
            cursor: pointer;
            transition: all 0.3s;
            font-size: 14px;
        }

        .cuisine-item:hover {
            border-color: #667eea;
            transform: translateY(-2px);
        }

        .cuisine-item input[type="checkbox"] {
            display: none;
        }

        .cuisine-item.selected {
            background: #f0f4ff;
            border-color: #667eea;
            font-weight: 600;
        }

        .cuisine-item.selected::before {
            content: '✓ ';
            color: #667eea;
        }
    </style>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css">
</head>
<body>
    <div class="container">
        <h1>🍎 AI Diet Planner</h1>
        <p class="subtitle">Personalized nutrition powered by artificial intelligence</p>
        
        <div class="ai-badge">
            <i class="fas fa-robot"></i>
            <span>Powered by Google Gemini AI</span>
        </div>

        <!-- Show profile status if user has a profile -->
        {% if has_profile %}
        <div class="profile-status">
            <h3>✅ Profile Active</h3>
            <p style="margin: 5px 0;">Welcome back! Your personalized settings are loaded.</p>
            <div class="profile-info">
                <div class="profile-stat">
                    <div class="profile-stat-value">{{ profile.age }} yrs</div>
                    <div class="profile-stat-label">Age</div>
                </div>
                <div class="profile-stat">
                    <div class="profile-stat-value">{{ profile.daily_calories }}</div>
                    <div class="profile-stat-label">Daily Cal</div>
                </div>
                <div class="profile-stat">
                    <div class="profile-stat-value">{{ profile.dietary_type|title }}</div>
                    <div class="profile-stat-label">Diet Type</div>
                </div>
            </div>
            <div class="profile-actions">
                <a href="/profile" class="btn-profile">
                    <i class="fas fa-edit"></i> Edit Profile
                </a>
                <a href="/clear_profile" class="btn-secondary" onclick="return confirm('Are you sure you want to clear your profile?')">
                    <i class="fas fa-trash"></i> Clear
                </a>
            </div>
        </div>
        {% else %}
        <!-- Show features if no profile -->
        <div class="features">
            <div class="feature-item">
                <div class="feature-icon">🎯</div>
                <div class="feature-text">Personalized Plans</div>
            </div>
            <div class="feature-item">
                <div class="feature-icon">🧠</div>
                <div class="feature-text">AI-Generated</div>
            </div>
            <div class="feature-item">
                <div class="feature-icon">🥗</div>
                <div class="feature-text">Healthy Recipes</div>
            </div>
            <div class="feature-item">
                <div class="feature-icon">📊</div>
                <div class="feature-text">Macro Tracking</div>
            </div>
        </div>

        <!-- Profile Prompt -->
        <div class="profile-prompt">
            <h3>🌟 Get Your Personalized AI Meal Plan!</h3>
            <p>Create a detailed profile for customized recommendations based on your health goals, dietary preferences, and lifestyle.</p>
            <a href="/profile" class="btn-profile">
                <i class="fas fa-user-plus"></i> Create My Profile
            </a>
        </div>

        <div class="divider">
            <span>OR</span>
        </div>
        {% endif %}

        <!-- Flashed messages -->
        {% with messages = get_flashed_messages(with_categories=true) %}
            {% if messages %}
                {% for category, message in messages %}
                    <div style="background: #d4edda; border: 1px solid #c3e6cb; color: #155724; padding: 10px; border-radius: 8px; margin-bottom: 20px;">
                        {{ message }}
                    </div>
                {% endfor %}
            {% endif %}
        {% endwith %}

        <!-- Quick Form or Generate with Profile -->
        <form action="/generate" method="post" id="quickForm">
            {% if not has_profile %}
            <div class="quick-form-info">
                <i class="fas fa-info-circle"></i> Quick plan with basic info (create profile for better results)
            </div>
            
            <div class="form-section">
                <label for="age">Age</label>
                <input type="number" name="age" id="age" required min="10" max="100" placeholder="Enter your age">

                <label for="weight">Weight (kg)</label>
                <input type="number" name="weight" id="weight" required step="0.1" min="20" max="300" placeholder="Enter your weight">

                <label>Dietary Preference</label>
                <div class="radio-group">
                    <div class="radio-item">
                        <input type="radio" name="quick_dietary_type" id="veg" value="vegetarian" required>
                        <label for="veg">🥬 Vegetarian</label>
                    </div>
                    <div class="radio-item">
                        <input type="radio" name="quick_dietary_type" id="nonveg" value="omnivore" required>
                        <label for="nonveg">🍖 Non-Vegetarian</label>
                    </div>
                    <div class="radio-item">
                        <input type="radio" name="quick_dietary_type" id="vegan" value="vegan" required>
                        <label for="vegan">🌱 Vegan</label>
                    </div>
                </div>

                <label>Preferred Cuisine Styles (Select multiple)</label>
                <div class="cuisine-grid">
                    <label class="cuisine-item">
                        <input type="checkbox" name="quick_cuisine" value="north_indian">
                        North Indian
                    </label>
                    <label class="cuisine-item">
                        <input type="checkbox" name="quick_cuisine" value="south_indian">
                        South Indian
                    </label>
                    <label class="cuisine-item">
                        <input type="checkbox" name="quick_cuisine" value="chinese">
                        Chinese
                    </label>
                    <label class="cuisine-item">
                        <input type="checkbox" name="quick_cuisine" value="continental">
                        Continental
                    </label>
                    <label class="cuisine-item">
                        <input type="checkbox" name="quick_cuisine" value="mediterranean">
                        Mediterranean
                    </label>
                    <label class="cuisine-item">
                        <input type="checkbox" name="quick_cuisine" value="italian">
                        Italian
                    </label>
                    <label class="cuisine-item">
                        <input type="checkbox" name="quick_cuisine" value="mexican">
                        Mexican
                    </label>
                    <label class="cuisine-item">
                        <input type="checkbox" name="quick_cuisine" value="thai">
                        Thai
                    </label>
                    <label class="cuisine-item">
                        <input type="checkbox" name="quick_cuisine" value="japanese">
                        Japanese
                    </label>
                </div>

                <label for="day">Select Day</label>
                <select name="day" id="day" required>
                    <option value="">-- Choose a Day --</option>
                    <option value="Monday">Monday</option>
                    <option value="Tuesday">Tuesday</option>
                    <option value="Wednesday">Wednesday</option>
                    <option value="Thursday">Thursday</option>
                    <option value="Friday">Friday</option>
                    <option value="Saturday">Saturday</option>
                    <option value="Sunday">Sunday</option>
                </select>
            </div>
            {% else %}
            <div class="form-section">
                <p style="color: #666; margin-bottom: 15px;">
                    <i class="fas fa-check-circle" style="color: #48bb78;"></i> 
                    Using your saved profile for personalized recommendations
                </p>
                <label for="day">Select Day</label>
                <select name="day" id="day" required>
                    <option value="">-- Choose a Day --</option>
                    <option value="Monday">Monday</option>
                    <option value="Tuesday">Tuesday</option>
                    <option value="Wednesday">Wednesday</option>
                    <option value="Thursday">Thursday</option>
                    <option value="Friday">Friday</option>
                    <option value="Saturday">Saturday</option>
                    <option value="Sunday">Sunday</option>
                </select>
            </div>
            {% endif %}

            <button type="submit">
                <i class="fas fa-magic"></i> Generate AI Plan
            </button>
        </form>
        
        <footer>
            Made with 💪 and 🥗 | Powered by AI
        </footer>
    </div>

    <script>
        // Handle radio button selection styling
        document.querySelectorAll('.radio-item input[type="radio"]').forEach(radio => {
            radio.addEventListener('change', function() {
                // Remove selected class from all radio items in the group
                document.querySelectorAll('.radio-item').forEach(item => {
                    item.classList.remove('selected');
                });
                // Add selected class to parent of checked radio
                if (this.checked) {
                    this.closest('.radio-item').classList.add('selected');
                }
            });
        });

        // Handle cuisine checkbox selection styling
        document.querySelectorAll('.cuisine-item input[type="checkbox"]').forEach(checkbox => {
            checkbox.addEventListener('change', function() {
                if (this.checked) {
                    this.closest('.cuisine-item').classList.add('selected');
                } else {
                    this.closest('.cuisine-item').classList.remove('selected');
                }
            });
        });

        // Initialize selected state on page load
        document.querySelectorAll('.radio-item input[type="radio"]:checked').forEach(radio => {
            radio.closest('.radio-item').classList.add('selected');
        });

        document.querySelectorAll('.cuisine-item input[type="checkbox"]:checked').forEach(checkbox => {
            checkbox.closest('.cuisine-item').classList.add('selected');
        });
    </script>
</body>
</html>

templates\profile.html:
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Create Your Profile - AI Diet Planner</title>
    <style>
        body {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            font-family: 'Segoe UI', sans-serif;
            margin: 0;
            padding: 20px;
            min-height: 100vh;
        }

        .container {
            max-width: 800px;
            margin: auto;
            background: white;
            padding: 40px;
            border-radius: 20px;
            box-shadow: 0 20px 40px rgba(0, 0, 0, 0.1);
        }

        h1 {
            color: #333;
            text-align: center;
            margin-bottom: 10px;
        }

        .subtitle {
            text-align: center;
            color: #666;
            margin-bottom: 30px;
        }

        .form-section {
            margin-bottom: 30px;
            padding: 20px;
            background: #f8f9fa;
            border-radius: 10px;
        }

        .section-title {
            font-size: 18px;
            font-weight: bold;
            color: #4a5568;
            margin-bottom: 15px;
            display: flex;
            align-items: center;
        }

        .section-title::before {
            content: '';
            width: 4px;
            height: 20px;
            background: #667eea;
            margin-right: 10px;
        }

        .form-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 15px;
        }

        label {
            display: block;
            margin-bottom: 5px;
            color: #555;
            font-weight: 500;
        }

        input, select {
            width: 100%;
            padding: 10px;
            border: 2px solid #e2e8f0;
            border-radius: 8px;
            font-size: 14px;
            transition: border-color 0.3s;
        }

        input:focus, select:focus {
            outline: none;
            border-color: #667eea;
        }

        .checkbox-group {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
            gap: 10px;
        }

        .checkbox-item {
            display: flex;
            align-items: center;
        }

        .checkbox-item input[type="checkbox"] {
            width: auto;
            margin-right: 8px;
        }

        button {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 15px 40px;
            border: none;
            border-radius: 10px;
            font-size: 16px;
            font-weight: bold;
            cursor: pointer;
            display: block;
            margin: 30px auto 0;
            transition: transform 0.3s;
        }

        button:hover {
            transform: translateY(-2px);
            box-shadow: 0 5px 15px rgba(102, 126, 234, 0.4);
        }

        .info-box {
            background: #e6f3ff;
            border-left: 4px solid #3182ce;
            padding: 10px 15px;
            margin-bottom: 20px;
            border-radius: 5px;
        }

        .info-box p {
            margin: 0;
            color: #2c5282;
            font-size: 14px;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>🎯 Create Your Personalized Profile</h1>
        <p class="subtitle">Tell us about yourself for AI-powered meal recommendations</p>

        <div class="info-box">
            <p>📊 Your information helps our AI create meals perfectly suited to your needs, preferences, and health goals.</p>
        </div>

        <form action="/save_profile" method="post">
            <!-- Basic Information -->
            <div class="form-section">
                <h3 class="section-title">Basic Information</h3>
                <div class="form-grid">
                    <div>
                        <label for="age">Age</label>
                        <input type="number" name="age" id="age" required min="10" max="100">
                    </div>
                    <div>
                        <label for="gender">Gender</label>
                        <select name="gender" id="gender" required>
                            <option value="">Select</option>
                            <option value="male">Male</option>
                            <option value="female">Female</option>
                            <option value="other">Other</option>
                        </select>
                    </div>
                    <div>
                        <label for="weight">Weight (kg)</label>
                        <input type="number" name="weight" id="weight" required step="0.1" min="20" max="300">
                    </div>
                    <div>
                        <label for="height">Height (cm)</label>
                        <input type="number" name="height" id="height" required min="100" max="250">
                    </div>
                </div>
            </div>

            <!-- Health Goals -->
            <div class="form-section">
                <h3 class="section-title">Health Goals</h3>
                <div class="form-grid">
                    <div>
                        <label for="goal">Primary Goal</label>
                        <select name="goal" id="goal" required>
                            <option value="maintain">Maintain Weight</option>
                            <option value="lose_weight">Lose Weight</option>
                            <option value="gain_weight">Gain Weight</option>
                            <option value="muscle_gain">Build Muscle</option>
                        </select>
                    </div>
                    <div>
                        <label for="activity_level">Activity Level</label>
                        <select name="activity_level" id="activity_level" required>
                            <option value="sedentary">Sedentary (Little/no exercise)</option>
                            <option value="light">Light (Exercise 1-3 days/week)</option>
                            <option value="moderate">Moderate (Exercise 3-5 days/week)</option>
                            <option value="active">Active (Exercise 6-7 days/week)</option>
                            <option value="very_active">Very Active (Physical job + exercise)</option>
                        </select>
                    </div>
                </div>
            </div>

            <!-- Dietary Preferences -->
            <div class="form-section">
                <h3 class="section-title">Dietary Preferences</h3>
                <div class="form-grid">
                    <div>
                        <label for="dietary_type">Diet Type</label>
                        <select name="dietary_type" id="dietary_type" required>
                            <option value="omnivore">Omnivore (Everything)</option>
                            <option value="vegetarian">Vegetarian</option>
                            <option value="vegan">Vegan</option>
                            <option value="pescatarian">Pescatarian</option>
                        </select>
                    </div>
                    <div>
                        <label for="spice_tolerance">Spice Preference</label>
                        <select name="spice_tolerance" id="spice_tolerance">
                            <option value="mild">Mild</option>
                            <option value="medium">Medium</option>
                            <option value="spicy">Spicy</option>
                        </select>
                    </div>
                </div>

                <div style="margin-top: 15px;">
                    <label>Allergies (Check all that apply)</label>
                    <div class="checkbox-group">
                        <div class="checkbox-item">
                            <input type="checkbox" name="allergies" value="nuts" id="allergy_nuts">
                            <label for="allergy_nuts">Nuts</label>
                        </div>
                        <div class="checkbox-item">
                            <input type="checkbox" name="allergies" value="dairy" id="allergy_dairy">
                            <label for="allergy_dairy">Dairy</label>
                        </div>
                        <div class="checkbox-item">
                            <input type="checkbox" name="allergies" value="eggs" id="allergy_eggs">
                            <label for="allergy_eggs">Eggs</label>
                        </div>
                        <div class="checkbox-item">
                            <input type="checkbox" name="allergies" value="gluten" id="allergy_gluten">
                            <label for="allergy_gluten">Gluten</label>
                        </div>
                        <div class="checkbox-item">
                            <input type="checkbox" name="allergies" value="seafood" id="allergy_seafood">
                            <label for="allergy_seafood">Seafood</label>
                        </div>
                        <div class="checkbox-item">
                            <input type="checkbox" name="allergies" value="soy" id="allergy_soy">
                            <label for="allergy_soy">Soy</label>
                        </div>
                    </div>
                </div>
            </div>

            <!-- Medical Conditions -->
            <div class="form-section">
                <h3 class="section-title">Medical Conditions (Optional)</h3>
                <div class="checkbox-group">
                    <div class="checkbox-item">
                        <input type="checkbox" name="medical_conditions" value="diabetes" id="med_diabetes">
                        <label for="med_diabetes">Diabetes</label>
                    </div>
                    <div class="checkbox-item">
                        <input type="checkbox" name="medical_conditions" value="hypertension" id="med_hypertension">
                        <label for="med_hypertension">Hypertension</label>
                    </div>
                    <div class="checkbox-item">
                        <input type="checkbox" name="medical_conditions" value="cholesterol" id="med_cholesterol">
                        <label for="med_cholesterol">High Cholesterol</label>
                    </div>
                    <div class="checkbox-item">
                        <input type="checkbox" name="medical_conditions" value="thyroid" id="med_thyroid">
                        <label for="med_thyroid">Thyroid Issues</label>
                    </div>
                </div>
            </div>

            <!-- Lifestyle -->
            <div class="form-section">
                <h3 class="section-title">Lifestyle & Preferences</h3>
                <div class="form-grid">
                    <div>
                        <label for="meal_prep_time">Available Cooking Time</label>
                        <select name="meal_prep_time" id="meal_prep_time">
                            <option value="quick">Quick (< 20 mins)</option>
                            <option value="medium">Medium (20-40 mins)</option>
                            <option value="elaborate">Elaborate (40+ mins)</option>
                        </select>
                    </div>
                    <div>
                        <label for="cooking_skill">Cooking Skill Level</label>
                        <select name="cooking_skill" id="cooking_skill">
                            <option value="beginner">Beginner</option>
                            <option value="intermediate">Intermediate</option>
                            <option value="advanced">Advanced</option>
                        </select>
                    </div>
                </div>

                <div style="margin-top: 15px;">
                    <label>Preferred Cuisines (Check all that apply)</label>
                    <div class="checkbox-group">
                        <div class="checkbox-item">
                            <input type="checkbox" name="cuisine_preferences" value="indian" id="cuisine_indian">
                            <label for="cuisine_indian">Indian</label>
                        </div>
                        <div class="checkbox-item">
                            <input type="checkbox" name="cuisine_preferences" value="chinese" id="cuisine_chinese">
                            <label for="cuisine_chinese">Chinese</label>
                        </div>
                        <div class="checkbox-item">
                            <input type="checkbox" name="cuisine_preferences" value="italian" id="cuisine_italian">
                            <label for="cuisine_italian">Italian</label>
                        </div>
                        <div class="checkbox-item">
                            <input type="checkbox" name="cuisine_preferences" value="mexican" id="cuisine_mexican">
                            <label for="cuisine_mexican">Mexican</label>
                        </div>
                        <div class="checkbox-item">
                            <input type="checkbox" name="cuisine_preferences" value="mediterranean" id="cuisine_mediterranean">
                            <label for="cuisine_mediterranean">Mediterranean</label>
                        </div>
                        <div class="checkbox-item">
                            <input type="checkbox" name="cuisine_preferences" value="thai" id="cuisine_thai">
                            <label for="cuisine_thai">Thai</label>
                        </div>
                    </div>
                </div>
            </div>

            <button type="submit">🚀 Create My AI Meal Plan</button>
        </form>
    </div>
</body>
</html>

templates\profile_created.html:
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Profile Created Successfully - AI Diet Planner</title>
    <style>
        body {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            font-family: 'Segoe UI', sans-serif;
            margin: 0;
            padding: 20px;
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
        }

        .container {
            max-width: 800px;
            background: white;
            padding: 40px;
            border-radius: 20px;
            box-shadow: 0 20px 40px rgba(0, 0, 0, 0.1);
            animation: slideUp 0.5s ease;
        }

        @keyframes slideUp {
            from {
                transform: translateY(40px);
                opacity: 0;
            }
            to {
                transform: translateY(0);
                opacity: 1;
            }
        }

        .success-header {
            text-align: center;
            margin-bottom: 30px;
        }

        .success-icon {
            font-size: 60px;
            margin-bottom: 20px;
            animation: bounce 1s ease;
        }

        @keyframes bounce {
            0%, 20%, 50%, 80%, 100% {
                transform: translateY(0);
            }
            40% {
                transform: translateY(-20px);
            }
            60% {
                transform: translateY(-10px);
            }
        }

        h1 {
            color: #333;
            margin-bottom: 10px;
        }

        .subtitle {
            color: #666;
            font-size: 16px;
        }

        .profile-summary {
            background: #f8f9fa;
            padding: 30px;
            border-radius: 15px;
            margin-bottom: 30px;
        }

        .summary-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }

        .summary-item {
            text-align: center;
            padding: 15px;
            background: white;
            border-radius: 10px;
            box-shadow: 0 2px 5px rgba(0, 0, 0, 0.05);
        }

        .summary-label {
            font-size: 12px;
            color: #666;
            text-transform: uppercase;
            letter-spacing: 1px;
            margin-bottom: 5px;
        }

        .summary-value {
            font-size: 24px;
            font-weight: bold;
            color: #667eea;
        }

        .nutrition-targets {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
            border-radius: 15px;
            margin-bottom: 30px;
        }

        .nutrition-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
            gap: 20px;
            text-align: center;
        }

        .nutrition-item {
            padding: 20px;
            background: rgba(255, 255, 255, 0.1);
            border-radius: 10px;
            backdrop-filter: blur(10px);
        }

        .nutrition-value {
            font-size: 32px;
            font-weight: bold;
            margin-bottom: 5px;
        }

        .nutrition-label {
            font-size: 14px;
            opacity: 0.9;
        }

        .preferences-section {
            background: #e6f3ff;
            padding: 20px;
            border-radius: 10px;
            margin-bottom: 30px;
        }

        .pref-title {
            font-size: 18px;
            font-weight: bold;
            color: #2c5282;
            margin-bottom: 15px;
        }

        .pref-list {
            display: flex;
            flex-wrap: wrap;
            gap: 10px;
        }

        .pref-tag {
            background: white;
            padding: 5px 15px;
            border-radius: 20px;
            font-size: 14px;
            color: #333;
            border: 1px solid #e2e8f0;
        }

        .action-buttons {
            display: flex;
            gap: 15px;
            justify-content: center;
            flex-wrap: wrap;
        }

        .btn {
            padding: 15px 30px;
            border-radius: 10px;
            text-decoration: none;
            font-weight: bold;
            transition: all 0.3s;
            display: inline-flex;
            align-items: center;
            gap: 8px;
            border: none;
            cursor: pointer;
        }

        .btn-primary {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
        }

        .btn-secondary {
            background: white;
            color: #667eea;
            border: 2px solid #667eea;
        }

        .btn:hover {
            transform: translateY(-2px);
            box-shadow: 0 5px 15px rgba(102, 126, 234, 0.3);
        }

        .alert {
            background: #d4edda;
            border: 1px solid #c3e6cb;
            color: #155724;
            padding: 15px;
            border-radius: 10px;
            margin-bottom: 20px;
            text-align: center;
        }
    </style>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css">
</head>
<body>
    <div class="container">
        <div class="success-header">
            <div class="success-icon">✅</div>
            <h1>Profile Created Successfully!</h1>
            <p class="subtitle">Your personalized nutrition targets have been calculated</p>
        </div>

        {% with messages = get_flashed_messages(with_categories=true) %}
            {% if messages %}
                {% for category, message in messages %}
                    <div class="alert">{{ message }}</div>
                {% endfor %}
            {% endif %}
        {% endwith %}

        <!-- Profile Summary -->
        <div class="profile-summary">
            <h3 style="margin-bottom: 20px; color: #333;">Your Profile Summary</h3>
            <div class="summary-grid">
                <div class="summary-item">
                    <div class="summary-label">Age</div>
                    <div class="summary-value">{{ profile.age }}</div>
                </div>
                <div class="summary-item">
                    <div class="summary-label">Weight</div>
                    <div class="summary-value">{{ profile.weight }} kg</div>
                </div>
                <div class="summary-item">
                    <div class="summary-label">Height</div>
                    <div class="summary-value">{{ profile.height }} cm</div>
                </div>
                <div class="summary-item">
                    <div class="summary-label">BMI</div>
                    <div class="summary-value">{{ "%.1f"|format(profile.weight / ((profile.height/100) ** 2)) }}</div>
                </div>
                <div class="summary-item">
                    <div class="summary-label">Goal</div>
                    <div class="summary-value">{{ profile.goal.replace('_', ' ').title() }}</div>
                </div>
                <div class="summary-item">
                    <div class="summary-label">Activity</div>
                    <div class="summary-value">{{ profile.activity_level.title() }}</div>
                </div>
            </div>
        </div>

        <!-- Nutrition Targets -->
        <div class="nutrition-targets">
            <h3 style="text-align: center; margin-bottom: 20px;">Your Daily Nutrition Targets</h3>
            <div class="nutrition-grid">
                <div class="nutrition-item">
                    <div class="nutrition-value">{{ profile.daily_calories }}</div>
                    <div class="nutrition-label">Calories</div>
                </div>
                <div class="nutrition-item">
                    <div class="nutrition-value">{{ profile.daily_macros.protein_g }}g</div>
                    <div class="nutrition-label">Protein</div>
                </div>
                <div class="nutrition-item">
                    <div class="nutrition-value">{{ profile.daily_macros.carbs_g }}g</div>
                    <div class="nutrition-label">Carbs</div>
                </div>
                <div class="nutrition-item">
                    <div class="nutrition-value">{{ profile.daily_macros.fats_g }}g</div>
                    <div class="nutrition-label">Fats</div>
                </div>
            </div>
        </div>

        <!-- Preferences -->
        <div class="preferences-section">
            <div class="pref-title">
                <i class="fas fa-check-circle"></i> Your Preferences Are Saved
            </div>
            <div class="pref-list">
                <span class="pref-tag">{{ profile.dietary_type.title() }}</span>
                <span class="pref-tag">{{ profile.spice_tolerance.title() }} Spice</span>
                <span class="pref-tag">{{ profile.cooking_skill.title() }} Cook</span>
                {% if profile.allergies %}
                    {% for allergy in profile.allergies %}
                        <span class="pref-tag" style="background: #fee; color: #c00;">No {{ allergy.title() }}</span>
                    {% endfor %}
                {% endif %}
            </div>
        </div>

        <!-- Action Buttons -->
        <div class="action-buttons">
            <a href="/" class="btn btn-primary">
                <i class="fas fa-utensils"></i> Generate My First Meal Plan
            </a>
            <a href="/profile" class="btn btn-secondary">
                <i class="fas fa-edit"></i> Edit Profile
            </a>
        </div>
    </div>
</body>
</html>

templates\result.html:
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Your Diet Plan</title>
    <style>
        body {
            background: linear-gradient(to right, #a1c4fd, #c2e9fb);
            font-family: 'Segoe UI', sans-serif;
            text-align: center;
            padding: 50px;
            color: #333;
        }

        .card {
            background: white;
            border-radius: 20px;
            padding: 30px;
            max-width: 600px;
            margin: auto;
            box-shadow: 0 10px 30px rgba(0, 0, 0, 0.2);
        }

        h1 {
            margin-bottom: 10px;
        }

        ul {
            text-align: left;
            list-style-type: none;
            padding-left: 0;
        }

        li {
            margin-bottom: 10px;
            background: #f2f2f2;
            padding: 10px;
            border-radius: 10px;
        }

        a {
            margin-top: 20px;
            display: inline-block;
            background: #3498db;
            color: white;
            padding: 10px 20px;
            border-radius: 10px;
            text-decoration: none;
            transition: 0.3s;
        }

        a:hover {
            background: #2980b9;
        }
    </style>
</head>
<body>
    <div class="card">
        <h1>🥗 Your Diet Plan for {{ day }}</h1>
        <p><strong>Age:</strong> {{ age }} years</p>
        <p><strong>Weight:</strong> {{ weight }} kg</p>
        <ul>
            {% for item in diet %}
                <li>{{ item }}</li>
            {% endfor %}
        </ul>
        <a href="/">← Back to Planner</a>
    </div>
</body>
</html>


utils\ai_meal_generator.py:
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
            self.model = genai.GenerativeModel('gemini-2.5-flash')
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

utils\diet_generator.py:
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

utils\__init__.py:
# utils/__init__.py

"""
Utilities package for the AI Diet Planner application.
"""

from .diet_generator import generate_diet
from .ai_meal_generator import AIMealGenerator

__all__ = ['generate_diet', 'AIMealGenerator']

