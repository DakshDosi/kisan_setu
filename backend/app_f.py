from flask import Flask, render_template, request, jsonify, send_file
from flask_cors import CORS
from googletrans import Translator
from io import BytesIO
import requests
import os
import google.generativeai as genai

app = Flask(__name__, static_folder=".", static_url_path="")
CORS(app)

translator = Translator()

voice_id = "m5qndnI7u4OAdXhH0Mr5"

# Load API keys
GEMINI_API_KEY = "AIzaSyBGoGgo9UojYyObL3gaJXWRFn8g5t9Nq7s"
ELEVENLABS_API_KEY = "sk_3103f7418c50e49331e6e1c236d31828fbd5a56f0cc6c4ff"
ELEVENLABS_URL = "https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"

genai.configure(api_key=GEMINI_API_KEY)

def call_gemini(query_text):
    model = genai.GenerativeModel("gemini-1.5-flash")
    response = model.generate_content(
        f"You are an agriculture advisor for Indian farmers. "
        f"Answer in 2-3 simple sentences with practical solutions only. "
        f"Question: {query_text}"
    )
    return response.text

def call_elevenlabs(text, voice_id):
    headers = {
        "Content-Type": "application/json",
        "xi-api-key": ELEVENLABS_API_KEY,
    }
    data = {
        "text": text,
        "model_id": "eleven_multilingual_v2",
        "voice_settings": {
            "stability": 0.5,
            "similarity_boost": 0.8
        }
    }
    url = ELEVENLABS_URL.format(voice_id=voice_id)
    response = requests.post(url, headers=headers, json=data)
    response.raise_for_status()
    return BytesIO(response.content)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/ask', methods=['POST'])
def api_ask():
    data = request.get_json(silent=True) or {}
    question = (data.get('question') or '').strip()
    locale = (data.get('locale') or 'hi-IN').strip()
    
    if not all([GEMINI_API_KEY, ELEVENLABS_API_KEY, voice_id]):
        return jsonify(error="API keys or voice ID not configured."), 500

    if not question:
        return jsonify(error='Missing question'), 400

    try:
        # Detect and translate to English
        detection = translator.detect(question)
        translated = translator.translate(question, dest='en')

        # Send English query to Gemini
        gemini_answer_en = call_gemini(translated.text)

        # Translate Gemini's English response back to user's language
        target_lang = locale.split('-')[0] if '-' in locale else locale[:2]
        translated_answer = translator.translate(gemini_answer_en, dest=target_lang)

        # Generate audio using ElevenLabs
        audio_stream = call_elevenlabs(translated_answer.text, voice_id)

        # Return audio with proper headers
        response = send_file(audio_stream, mimetype="audio/mpeg")
        response.headers['Access-Control-Allow-Origin'] = '*'
        return response
        
    except Exception as e:
        print(f"Error in api_ask: {e}")  # For debugging
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

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000, debug=True)