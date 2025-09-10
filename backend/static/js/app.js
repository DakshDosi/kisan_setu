(() => {
  const elements = {
    start: document.getElementById('btn-start'),
    stop: document.getElementById('btn-stop'),
    ask: document.getElementById('btn-ask'),
    speak: document.getElementById('btn-speak'),
    cancelSpeak: document.getElementById('btn-cancel-speak'),
    transcriptBox: document.getElementById('transcript-box'),
    textInput: document.getElementById('text-input'),
    responseBox: document.getElementById('response-box'),
    statusText: document.getElementById('status-text'),
    micIndicator: document.getElementById('mic-indicator'),
    language: document.getElementById('language'),
    supportWarning: document.getElementById('support-warning'),
    cursor: document.getElementById('custom-cursor'),
  };

  const supportsRecognition = 'webkitSpeechRecognition' in window || 'SpeechRecognition' in window;
  const supportsSynthesis = 'speechSynthesis' in window && 'SpeechSynthesisUtterance' in window;

  if (!supportsRecognition || !supportsSynthesis) {
    elements.supportWarning.hidden = false;
  }

  // --- Custom Cursor ---
  const cursorEl = elements.cursor;
  if (cursorEl) {
    // Enable custom-cursor mode (hides native cursor via CSS)
    document.body.classList.add('cursor-enabled');
    let targetX = window.innerWidth / 2;
    let targetY = window.innerHeight / 2;
    let currentX = targetX;
    let currentY = targetY;
    const ease = 0.18;

    const raf = () => {
      currentX += (targetX - currentX) * ease;
      currentY += (targetY - currentY) * ease;
      cursorEl.style.left = currentX + 'px';
      cursorEl.style.top = currentY + 'px';
      requestAnimationFrame(raf);
    };
    requestAnimationFrame(raf);

    window.addEventListener('mousemove', (e) => {
      targetX = e.clientX; targetY = e.clientY;
    });

    const interactiveSelectors = 'button, .btn, select, input, textarea';
    document.addEventListener('mouseover', (e) => {
      if (e.target.closest && e.target.closest(interactiveSelectors)) {
        cursorEl.classList.add('cursor-grow');
      }
    });
    document.addEventListener('mouseout', (e) => {
      if (e.target.closest && e.target.closest(interactiveSelectors)) {
        cursorEl.classList.remove('cursor-grow');
      }
    });

    document.addEventListener('mousedown', () => {
      cursorEl.classList.remove('cursor-pulse');
      // force reflow to restart animation
      void cursorEl.offsetWidth;
      cursorEl.classList.add('cursor-pulse');
    });
  }

  // --- Speech Recognition setup ---
  let recognition = null;
  let recognizing = false;
  let interimTranscript = '';

  if (supportsRecognition) {
    const RecognitionCtor = window.SpeechRecognition || window.webkitSpeechRecognition;
    recognition = new RecognitionCtor();
    recognition.continuous = true;
    recognition.interimResults = true;
    recognition.maxAlternatives = 1;

    recognition.onstart = () => {
      recognizing = true;
      elements.statusText.textContent = 'Listening…';
      elements.micIndicator.classList.add('listening');
      elements.start.disabled = true;
      elements.stop.disabled = false;
      elements.start.classList.add('listening-active');
      document.body.classList.add('listening');
    };

    recognition.onerror = (event) => {
      console.warn('Recognition error', event.error);
      setStatus(`Mic error: ${event.error}`);
      elements.micIndicator.classList.remove('listening');
      recognizing = false;
      elements.start.disabled = false;
      elements.stop.disabled = true;
    };

    recognition.onend = () => {
      recognizing = false;
      elements.micIndicator.classList.remove('listening');
      elements.statusText.textContent = 'Idle';
      elements.start.disabled = false;
      elements.stop.disabled = true;
      elements.start.classList.remove('listening-active');
      document.body.classList.remove('listening');
    };

    recognition.onresult = (event) => {
      let finalTranscript = '';
      for (let i = event.resultIndex; i < event.results.length; i += 1) {
        const result = event.results[i];
        if (result.isFinal) {
          finalTranscript += result[0].transcript;
        } else {
          interimTranscript += result[0].transcript;
        }
      }

      const prev = elements.textInput.value.trim();
      const merged = [prev, finalTranscript.trim()].filter(Boolean).join(' ');
      if (finalTranscript) {
        elements.textInput.value = merged;
        interimTranscript = '';
      }
      elements.transcriptBox.textContent = interimTranscript || merged || '';
    };
  }

  function setStatus(text) {
    elements.statusText.textContent = text;
  }

  function getQuestionText() {
    const fromInput = elements.textInput.value.trim();
    const fromTranscript = elements.transcriptBox.textContent.trim();
    return fromInput || fromTranscript || '';
  }

  async function askBackend(question, locale) {
    const response = await fetch('/api/ask', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ question, locale }),
    });
    if (!response.ok) {
      const text = await response.text();
      throw new Error(text || `Request failed: ${response.status}`);
    }
    return response.json();
  }

  function speak(text, locale) {
    if (!supportsSynthesis) return;
    window.speechSynthesis.cancel();
    const utt = new SpeechSynthesisUtterance(text);
    utt.lang = locale;
    // Try to pick a matching voice if available
    const voice = window.speechSynthesis.getVoices().find(v => v.lang === locale);
    if (voice) utt.voice = voice;

    utt.onstart = () => {
      elements.speak.disabled = true;
      elements.cancelSpeak.disabled = false;
    };
    utt.onend = () => {
      elements.speak.disabled = false;
      elements.cancelSpeak.disabled = true;
    };

    window.speechSynthesis.speak(utt);
  }

  // --- Event listeners ---
  elements.start?.addEventListener('click', () => {
    if (!recognition) return;
    try {
      interimTranscript = '';
      elements.transcriptBox.textContent = '';
      recognition.lang = elements.language.value || 'hi-IN';
      recognition.start();
    } catch (e) {
      console.error(e);
    }
  });

  elements.stop?.addEventListener('click', () => {
    if (recognition && recognizing) recognition.stop();
  });

  elements.ask?.addEventListener('click', async () => {
    const question = getQuestionText();
    const locale = elements.language.value || 'hi-IN';
    if (!question) {
      setStatus('Please say or type a question.');
      return;
    }

    setStatus('Thinking…');
    document.body.classList.add('thinking');
    const bar = document.getElementById('activity-bar');
    if (bar) bar.hidden = false;
    const typing = document.getElementById('typing-indicator');
    if (typing) typing.hidden = false;
    elements.ask.disabled = true;
    try {
      const data = await askBackend(question, locale);
      const answer = data.final_answer || '';
      elements.responseBox.textContent = answer;
      // Trigger expand animation
      elements.responseBox.classList.remove('expand');
      void elements.responseBox.offsetWidth; // reflow
      elements.responseBox.classList.add('expand');
      setStatus('Ready');
      elements.speak.disabled = !answer;
      if (answer && supportsSynthesis) {
        // Auto-play the voice output for convenience
        speak(answer, locale);
      }
    } catch (err) {
      console.error(err);
      elements.responseBox.textContent = 'Sorry, something went wrong. Please try again.';
      elements.responseBox.classList.remove('expand');
      void elements.responseBox.offsetWidth;
      elements.responseBox.classList.add('expand');
      setStatus('Error');
    } finally {
      elements.ask.disabled = false;
      const typing2 = document.getElementById('typing-indicator');
      if (typing2) typing2.hidden = true;
      document.body.classList.remove('thinking');
      const bar2 = document.getElementById('activity-bar');
      if (bar2) bar2.hidden = true;
    }
  });

  elements.speak?.addEventListener('click', () => {
    const text = elements.responseBox.textContent.trim();
    const locale = elements.language.value || 'hi-IN';
    if (text) speak(text, locale);
  });

  elements.cancelSpeak?.addEventListener('click', () => {
    if (!supportsSynthesis) return;
    window.speechSynthesis.cancel();
  });

  // Load voices list (some browsers populate asynchronously)
  if (supportsSynthesis) {
    window.speechSynthesis.onvoiceschanged = () => {
      // no-op; the speak() function will pick a voice when called
    };
  }
})();


