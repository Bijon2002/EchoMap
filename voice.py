"""
voice.py - Voice Interaction Engine for EchoMap
Provides client-side browser speech synthesis (TTS) and accessible Web Speech API
voice recognition for hands-free queries.
"""

import streamlit.components.v1 as components


def speak(text: str) -> None:
    """
    Instructs the browser to speak the provided text using the Web Speech API.
    Cancels any previous speech to avoid overlapping audio queues.
    """
    if not text:
        return

    # Escape backticks, backslashes, and dollar signs for safe JS template literals
    safe_text = (
        text.replace("\\", "\\\\")
        .replace("`", "\\`")
        .replace("$", "\\$")
        .replace('"', '\\"')
        .replace("\n", " ")
    )

    components.html(
        f"""
        <script>
            (function() {{
                if ("speechSynthesis" in window) {{
                    window.speechSynthesis.cancel();
                    const utterance = new SpeechSynthesisUtterance("{safe_text}");
                    utterance.lang = "en-GB";
                    utterance.rate = 1.0;
                    utterance.pitch = 1.0;
                    
                    // Voice selection: prefer a clear natural voice if available
                    const voices = window.speechSynthesis.getVoices();
                    const preferredVoice = voices.find(v => v.lang.startsWith("en") && (v.name.includes("Natural") || v.name.includes("Google")));
                    if (preferredVoice) {{
                        utterance.voice = preferredVoice;
                    }}
                    
                    window.speechSynthesis.speak(utterance);
                }}
            }})();
        </script>
        """,
        height=0,
        width=0,
    )


def voice_input_widget(component_key: str = "voice_input") -> None:
    """
    Renders an accessible, high-contrast microphone controller that utilizes the
    browser's native Web Speech API (SpeechRecognition / webkitSpeechRecognition).
    """
    components.html(
        f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                .voice-container {{
                    font-family: system-ui, -apple-system, sans-serif;
                    display: flex;
                    flex-direction: column;
                    align-items: center;
                    gap: 12px;
                    padding: 16px;
                    background: linear-gradient(135deg, #0d1117, #161b22);
                    border: 2px solid #30363d;
                    border-radius: 12px;
                    color: #f0f6fc;
                }}
                .mic-btn {{
                    background: #238636;
                    color: #ffffff;
                    border: none;
                    border-radius: 50%;
                    width: 72px;
                    height: 72px;
                    font-size: 32px;
                    cursor: pointer;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    transition: all 0.2s ease;
                    box-shadow: 0 4px 12px rgba(35, 134, 54, 0.4);
                    outline: 3px solid transparent;
                }}
                .mic-btn:hover, .mic-btn:focus {{
                    background: #2ea043;
                    transform: scale(1.06);
                    outline: 3px solid #58a6ff;
                }}
                .mic-btn.listening {{
                    background: #da3633;
                    animation: pulse 1.2s infinite;
                    box-shadow: 0 0 20px rgba(218, 54, 51, 0.6);
                }}
                @keyframes pulse {{
                    0% {{ transform: scale(1); }}
                    50% {{ transform: scale(1.1); }}
                    100% {{ transform: scale(1); }}
                }}
                .status-label {{
                    font-size: 15px;
                    font-weight: 600;
                    color: #8b949e;
                    text-align: center;
                }}
                .transcript-box {{
                    width: 95%;
                    padding: 10px;
                    min-height: 42px;
                    background: #090d13;
                    border: 1px solid #30363d;
                    border-radius: 6px;
                    font-size: 14px;
                    color: #58a6ff;
                    word-wrap: break-word;
                    text-align: center;
                }}
                .copy-hint {{
                    font-size: 12px;
                    color: #7ee787;
                }}
            </style>
        </head>
        <body>
            <div class="voice-container">
                <button id="micButton" class="mic-btn" aria-label="Start Voice Command" title="Click and speak your question">
                    🎙️
                </button>
                <div id="statusLabel" class="status-label">Click microphone to speak to EchoMap</div>
                <div id="transcriptBox" class="transcript-box" aria-live="polite">Spoken command will appear here...</div>
                <div id="hintLabel" class="copy-hint">Once spoken, click "Use Spoken Query" or copy into the question box below!</div>
            </div>

            <script>
                const micBtn = document.getElementById('micButton');
                const statusLabel = document.getElementById('statusLabel');
                const transcriptBox = document.getElementById('transcriptBox');
                let recognition = null;
                let isListening = false;

                const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;

                if (SpeechRecognition) {{
                    recognition = new SpeechRecognition();
                    recognition.continuous = false;
                    recognition.interimResults = true;
                    recognition.lang = 'en-US';

                    recognition.onstart = function() {{
                        isListening = true;
                        micBtn.classList.add('listening');
                        statusLabel.textContent = 'Listening... Speak now ("Where are my keys?")';
                        statusLabel.style.color = '#f85149';
                    }};

                    recognition.onresult = function(event) {{
                        let current = '';
                        for (let i = event.resultIndex; i < event.results.length; ++i) {{
                            current += event.results[i][0].transcript;
                        }}
                        transcriptBox.textContent = current;
                        // Copy to parent window input field if accessible
                        try {{
                            const parentInputs = window.parent.document.querySelectorAll('input[type="text"]');
                            if (parentInputs.length > 0) {{
                                const mainInput = parentInputs[0];
                                mainInput.value = current;
                                mainInput.dispatchEvent(new Event('input', {{ bubbles: true }}));
                            }}
                        }} catch (e) {{}}
                    }};

                    recognition.onerror = function(event) {{
                        isListening = false;
                        micBtn.classList.remove('listening');
                        statusLabel.textContent = 'Error: ' + event.error;
                        statusLabel.style.color = '#f85149';
                    }};

                    recognition.onend = function() {{
                        isListening = false;
                        micBtn.classList.remove('listening');
                        statusLabel.textContent = 'Finished listening. Click to speak again.';
                        statusLabel.style.color = '#8b949e';
                    }};

                    micBtn.addEventListener('click', function() {{
                        if (isListening) {{
                            recognition.stop();
                        }} else {{
                            transcriptBox.textContent = 'Listening...';
                            recognition.start();
                        }}
                    }});
                }} else {{
                    statusLabel.textContent = 'Speech Recognition not supported in this browser. Please use text input below.';
                    micBtn.style.opacity = '0.5';
                    micBtn.disabled = true;
                }}
            </script>
        </body>
        </html>
        """,
        height=210,
    )
