from flask import Flask, render_template, request, jsonify, redirect, url_for, session
from geopy.geocoders import Nominatim
from googletrans import Translator
from flask_sqlalchemy import SQLAlchemy
import requests
import json
import numpy as np
import os
import base64
import io

# --- API Keys ---
# Get a free API key from https://openweathermap.org/api
WEATHER_API_KEY = "bc2237bac8bb6b6a2f6cc72ed14fc6b33"
# Get a free API key from https://aistudio.google.com/app/apikey
GEMINI_API_KEY = "YOUR_GEMINI_API_KEY"

# --- Geocoding Setup ---
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
    password = db.Column(db.String(200), nullable=False)
    crop_type = db.Column(db.String(100))
    soil_type = db.Column(db.String(100))
    location = db.Column(db.String(200))

# Create tables
with app.app_context():
    db.create_all()

# ---------------------------
# Helper Functions for APIs
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

def get_weather_data(lat, lon):
    """Fetches weather data for given coordinates using OpenWeatherMap API."""
    if not lat or not lon:
        return None
    
    url = f"https://api.openweathermap.org/data/2.5/weather?lat={lat}&lon={lon}&appid={WEATHER_API_KEY}&units=metric"
    
    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        
        weather_info = {
            "temperature": data.get("main", {}).get("temp"),
            "feels_like": data.get("main", {}).get("feels_like"),
            "humidity": data.get("main", {}).get("humidity"),
            "description": data.get("weather", [{}])[0].get("description"),
            "main_weather": data.get("weather", [{}])[0].get("main"),
            "wind_speed": data.get("wind", {}).get("speed"),
            "rain_1h": data.get("rain", {}).get("1h", 0),
        }
        
        return weather_info
    except requests.exceptions.RequestException as e:
        print(f"Error fetching weather data: {e}")
        return None

def ask_gemini_api(prompt):
    """Sends a prompt to the Gemini API and returns the response."""
    # This is a placeholder. You would use the actual Gemini API here.
    return "This is a sample response from the AI."

# ---------------------------
# Routes
# ---------------------------
@app.route('/')
def landing():
    return render_template('landing.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        phone = request.form['phone']
        password = request.form['password']

        farmer = Farmer.query.filter_by(phone=phone).first()

        if farmer and farmer.password == password:
            session['user_phone'] = phone
            return redirect(url_for('profile'))
        else:
            error = "Incorrect phone number or password."
            return render_template('login.html', error=error)
    
    return render_template('login.html')

@app.route('/profile')
def profile():
    if 'user_phone' not in session:
        return redirect(url_for('login'))

    user_phone = session.get('user_phone')
    farmer = Farmer.query.filter_by(phone=user_phone).first()

    if not farmer:
        return "User not found", 404
    
    return render_template('profile.html', farmer=farmer)

@app.route('/index')
def index():
    if 'user_phone' not in session:
        return redirect(url_for('login'))
    return render_template('index.html')

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

        user_phone = session.get('user_phone')
        farmer = Farmer.query.filter_by(phone=user_phone).first()
        location_name = farmer.location if farmer else None
        
        lat, lon = get_coordinates_from_location(location_name)
        
        weather_info = get_weather_data(lat, lon)
        
        if weather_info:
            weather_text = (
                f"Current weather in {location_name}: Temperature is {weather_info['temperature']}°C, "
                f"feels like {weather_info['feels_like']}°C. Wind speed is {weather_info['wind_speed']} m/s. "
                f"Description: {weather_info['description']}. Rain in last hour: {weather_info['rain_1h']} mm."
            )
            ai_prompt = f"The user asked: '{question}'. Here is the current weather information: {weather_text}. Based on this, provide a relevant and helpful response for a farmer."
        else:
            ai_prompt = question
        
        ai_answer = ask_gemini_api(ai_prompt)
        
        translated_answer = translator.translate(ai_answer, dest=detection.lang).text
        
        return jsonify(
            answer=translated_answer,
            original_text=question,
            translated_text=ai_answer,
            locale=locale,
            weather_data=weather_info
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
            password=password,
            crop_type=crop_type,
            soil_type=soil_type,
            location=location
        )
        db.session.add(farmer)
        db.session.commit()

        return "Farmer registered successfully!"

    return render_template('registration.html')

@app.route('/farmers')
def show_farmers():
    farmers = Farmer.query.all()
    return render_template('farmers.html', farmers=farmers)

@app.route('/logout')
def logout():
    session.pop('user_phone', None)
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
