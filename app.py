from flask import Flask, render_template, request, jsonify
from googletrans import Translator
import requests
import os

app = Flask(__name__,
            template_folder='backend/templates',
            static_folder='backend/static')
translator = Translator()

# Load Gemini API key from environment variable
GEMINI_API_KEY = "AIzaSyBGoGgo9UojYyObL3gaJXWRFn8g5t9Nq7s"
GEMINI_URL = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash-latest:generateContent?key={GEMINI_API_KEY}"

def call_gemini(query_text):
    headers = {"Content-Type": "application/json"}
    data = {
        "contents": [
            {"parts": [{"text": f"You are an agriculture advisor for Indian farmers. "
                                f"Answer in 2-3 simple sentences with practical solutions only. "
                                f"Question: {query_text}"}]}
        ]
    }
    response = requests.post(GEMINI_URL, headers=headers, json=data, timeout=60)
    response.raise_for_status()
    out = response.json()
    return out["candidates"][0]["content"]["parts"][0]["text"]



@app.route('/')
def index():
    # Renders templates/index.html
    return render_template('index.html')


@app.post('/api/ask')
def api_ask():
    data = request.get_json(silent=True) or {}
    question = (data.get('question') or '').strip()
    locale = (data.get('locale') or 'hi-IN').strip()

    if not question:
        return jsonify(error='Missing question'), 400

    try:
        # Detect and translate to English
        detection = translator.detect(question)
        translated = translator.translate(question, dest='en')

        # Send English query to Gemini
        gemini_answer_en = call_gemini(translated.text)

        # Translate Gemini’s English response back into the user’s locale
        translated_answer = translator.translate(gemini_answer_en, dest=locale.split('-')[0])

        return jsonify(
            original_text=question,
            detected_lang=detection.lang,
            translated_query=translated.text,
            gemini_answer_en=gemini_answer_en,
            final_answer=translated_answer.text,
            locale=locale,
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


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=6000, debug=True)
