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