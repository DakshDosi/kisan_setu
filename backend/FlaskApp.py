from flask import Flask, render_template, request, jsonify, redirect, url_for, session
from geopy.geocoders import Nominatim
from googletrans import Translator
from flask_sqlalchemy import SQLAlchemy
import requests
import os
import json

geolocator = Nominatim(user_agent="KisanSetu_App")

app = Flask(__name__)
translator = Translator()

# Set a secret key for session management
app.secret_key = 'your_secret_key_here'

# ---------------------------
# Database Setup
# ---------------------------
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///farmers.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# Farmer table
class Farmer(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    phone = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)  # ⚠ hash later for security
    crop_type = db.Column(db.String(100))
    soil_type = db.Column(db.String(100))
    location = db.Column(db.String(200))

# Create tables
with app.app_context():
    db.create_all()

# ---------------------------
# Helper function for geocoding
# ---------------------------
def get_coordinates_from_location(location_name):
    """Converts a location name to latitude and longitude."""
    try:
        location = geolocator.geocode(location_name)
        if location:
            return location.latitude, location.longitude
        return None, None
    except Exception as e:
        print(f"Error during geocoding: {e}")
        return None, None

# ---------------------------
# Routes
# ---------------------------
@app.route('/')
def index():
    # If the user is not in the session, redirect to the login page
    if 'user_phone' not in session:
        return redirect(url_for('login'))
    # This page serves as the main AI chat page for logged-in users.
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        phone = request.form['phone']
        password = request.form['password']

        # Find the farmer by phone number
        farmer = Farmer.query.filter_by(phone=phone).first()

        # Check if farmer exists and password matches
        # ⚠ In a real application, you would use a password hashing library (e.g., bcrypt)
        # to compare the hashed password, not the plain text password.
        if farmer and farmer.password == password:
            # Authentication successful, add user to session and redirect to the index page
            session['user_phone'] = phone
            return redirect(url_for('index'))
        else:
            # Authentication failed, show an error message
            error = "Incorrect phone number or password."
            return render_template('login.html', error=error)
    
    return render_template('login.html')

@app.post('/api/ask')
def api_ask():
    data = request.get_json(silent=True) or {}
    question = (data.get('question') or '').strip()
    locale = (data.get('locale') or 'hi-IN').strip()

    if not question:
        return jsonify(error='Missing question'), 400

    try:
        detection = translator.detect(question)
        translated = translator.translate(question, dest='en')

        # Get the logged-in user's phone number from the session
        user_phone = session.get('user_phone')
        
        # Look up the farmer's location in the database
        farmer = Farmer.query.filter_by(phone=user_phone).first()
        location_name = farmer.location if farmer else None
        
        # Get coordinates for the farmer's location
        lat, lon = None, None
        if location_name:
            lat, lon = get_coordinates_from_location(location_name)
            
        # You can now use these coordinates (lat, lon) to get a weather forecast.
        # This is where you would make a call to your weather API.
        
        return jsonify(
            answer=translated.text,
            original_text=question,
            detected_lang=detection.lang,
            translated_text=translated.text,
            locale=locale,
            location_coordinates={"latitude": lat, "longitude": lon} # Added for verification
        )
    except Exception as e:
        return jsonify(error=str(e)), 500

@app.route('/translate', methods=['POST'])
def translate_text():
    data = request.get_json() or {}
    text = data.get('text', '')
    if not (text or '').strip():
        return jsonify({'error': 'No text provided'}), 400
    try:
        detection = translator.detect(text)
        translated = translator.translate(text, dest='en')
        return jsonify({
            'original_text': text,
            'detected_lang': detection.lang,
            'translated_text': translated.text
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ---------------------------
# Farmer Registration (with HTML form)
# ---------------------------
@app.route('/register', methods=['GET', 'POST'])
def register_farmer():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        phone = request.form['phone']
        password = request.form['password']
        crop_type = request.form.get('crop_type')
        soil_type = request.form.get('soil_type')
        location = request.form.get('location')

        farmer = Farmer(
            name=name,
            email=email,
            phone=phone,
            password=password,  # ⚠ hash later for security
            crop_type=crop_type,
            soil_type=soil_type,
            location=location
        )
        db.session.add(farmer)
        db.session.commit()

        return "Farmer registered successfully!"

    return render_template('registration.html')

# ---------------------------
# Route to display all farmers (for trial purposes)
# ---------------------------
@app.route('/farmers')
def show_farmers():
    farmers = Farmer.query.all()
    return render_template('farmers.html', farmers=farmers)

# ---------------------------
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
