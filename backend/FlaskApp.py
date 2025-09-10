from flask import Flask, render_template, request, jsonify
from googletrans import Translator

app = Flask(__name__)
translator = Translator()


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

    # Use translator to detect and translate user speech/text to English.
    try:
        detection = translator.detect(question)
        translated = translator.translate(question, dest='en')
        # For now, respond with the translated text as the "answer" so the
        # frontend can speak it. You can later replace this with your QA system
        # and then translate its answer back to the requested locale.
        return jsonify(
            answer=translated.text,
            original_text=question,
            detected_lang=detection.lang,
            translated_text=translated.text,
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
    app.run(host='0.0.0.0', port=5000, debug=True)


