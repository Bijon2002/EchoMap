/**
 * EchoMap — E.D.I.T.H. Spatial Engine
 * TerraGrip Aesthetic · Expressive Human Voice Prosody · Push-to-Talk Spacebar · Live Settings
 * Team PythonCharlie | Univ. of Bedfordshire HCI + AI Hackathon
 */

(function () {
    'use strict';

    const state = {
        activeTab: 'tab-voice',
        voiceEnabled: localStorage.getItem('echomap_voice') !== 'false',
        highContrast: localStorage.getItem('echomap_contrast') === 'true',
        isListening: false,
        recognition: null,
        accumulatedTranscript: '',
        interimTranscript: '',
        silenceTimeout: null,
        voices: [],
        edithVoice: null,
        selectedVoice: null,
        selectedVoiceName: '__expressive_edith__',
        inflectionLevel: parseFloat(localStorage.getItem('echomap_inflection') || '1.5'),
        speechRate: 1.0,
        activeAudio: null,
        cameraStream: null,
        cameraActive: false,
        latestScan: null,
        latestObjects: [],
        previousObjects: [],
        selectedObject: null,
        lastSpokenText: '',
        audioContext: null,
        spacebarDown: false,
    };

    const PALETTE = [
        '#0284c7', '#059669', '#d97706', '#c2410c',
        '#7c3aed', '#e11d48', '#0d9488', '#475569',
    ];

    function refreshIcons() {
        if (window.lucide && typeof window.lucide.createIcons === 'function') {
            window.lucide.createIcons();
        }
    }

    // ===================================================================
    // AUDIO CHIMES
    // ===================================================================
    function getAudioContext() {
        if (!state.audioContext) {
            const AudioCtx = window.AudioContext || window.webkitAudioContext;
            if (AudioCtx) state.audioContext = new AudioCtx();
        }
        if (state.audioContext && state.audioContext.state === 'suspended') {
            state.audioContext.resume();
        }
        return state.audioContext;
    }

    function playChime(type = 'respond') {
        const ctx = getAudioContext();
        if (!ctx) return;
        try {
            const now = ctx.currentTime;
            const osc = ctx.createOscillator();
            const gain = ctx.createGain();
            osc.type = 'sine';
            osc.connect(gain);
            gain.connect(ctx.destination);
            if (type === 'listen') {
                osc.frequency.setValueAtTime(587.33, now);
                osc.frequency.exponentialRampToValueAtTime(880, now + 0.12);
                gain.gain.setValueAtTime(0.06, now);
                gain.gain.exponentialRampToValueAtTime(0.001, now + 0.25);
                osc.start(now); osc.stop(now + 0.25);
            } else {
                osc.frequency.setValueAtTime(1046.5, now);
                osc.frequency.exponentialRampToValueAtTime(783.99, now + 0.15);
                gain.gain.setValueAtTime(0.05, now);
                gain.gain.exponentialRampToValueAtTime(0.001, now + 0.32);
                osc.start(now); osc.stop(now + 0.32);
            }
        } catch (e) { /* silent */ }
    }

    // ===================================================================
    // DOM CACHE
    // ===================================================================
    const dom = {
        ariaAnnouncer: document.getElementById('aria-announcer'),
        apiStatusPill: document.getElementById('api-status-pill'),
        apiStatusLabel: document.getElementById('api-status-label'),
        ttsToggleBtn: document.getElementById('tts-toggle-btn'),
        contrastToggleBtn: document.getElementById('contrast-toggle-btn'),
        btnOpenSettings: document.getElementById('btn-open-settings'),
        settingsModal: document.getElementById('settings-modal'),
        btnCloseSettings: document.getElementById('btn-close-settings'),
        settingsForm: document.getElementById('settings-form'),
        settingsApiKey: document.getElementById('settings-api-key'),
        settingsModel: document.getElementById('settings-model'),
        btnToggleKeyVis: document.getElementById('btn-toggle-key-visibility'),
        settingsKeyStatus: document.getElementById('settings-key-status'),
        settingsFeedback: document.getElementById('settings-feedback'),
        btnTestKey: document.getElementById('btn-test-key'),
        btnSaveSettings: document.getElementById('btn-save-settings'),
        btnLoadSample: document.getElementById('btn-load-sample'),
        btnSimulateDiff: document.getElementById('btn-simulate-diff'),
        btnClearMemory: document.getElementById('btn-clear-memory'),
        tabs: document.querySelectorAll('.nav-link'),
        tabPanels: document.querySelectorAll('.deck-tab-view'),
        floatRadarPreview: document.getElementById('float-radar-preview'),
        floatObjectsSummary: document.getElementById('float-objects-summary'),
        micTriggerBtn: document.getElementById('mic-trigger-btn'),
        micBtnLabel: document.getElementById('mic-btn-label'),
        micStatusText: document.getElementById('mic-status-text'),
        soundwaveBars: document.getElementById('soundwave-bars'),
        liveTranscript: document.getElementById('live-transcript'),
        queryChips: document.querySelectorAll('.prompt-chip'),
        queryForm: document.getElementById('query-form'),
        textQueryInput: document.getElementById('text-query-input'),
        btnSendQuery: document.getElementById('btn-send-query'),
        btnReplaySpeech: document.getElementById('btn-replay-speech'),
        btnCopyResponse: document.getElementById('btn-copy-response'),
        btnTestVoice: document.getElementById('btn-test-voice'),
        speakingBadge: document.getElementById('speaking-badge'),
        responseText: document.getElementById('response-text'),
        responseTimestamp: document.getElementById('response-timestamp'),
        responseScanRef: document.getElementById('response-scan-ref'),
        voiceSelect: document.getElementById('voice-select'),
        voiceInflection: document.getElementById('voice-inflection'),
        inflectionVal: document.getElementById('inflection-val'),
        voiceRate: document.getElementById('voice-rate'),
        rateVal: document.getElementById('rate-val'),
        spatialSvg: document.getElementById('spatial-svg'),
        radarBeam: document.getElementById('radar-beam'),
        btnRadarSweep: document.getElementById('btn-radar-sweep'),
        btnRefreshMap: document.getElementById('btn-refresh-map'),
        objectTooltip: document.getElementById('object-tooltip'),
        tooltipTitle: document.getElementById('tooltip-title'),
        tooltipSector: document.getElementById('tooltip-sector'),
        tooltipCoords: document.getElementById('tooltip-coords'),
        tooltipConf: document.getElementById('tooltip-conf'),
        tooltipNear: document.getElementById('tooltip-near'),
        countFar: document.getElementById('count-far'),
        countMid: document.getElementById('count-mid'),
        countNear: document.getElementById('count-near'),
        listFar: document.getElementById('list-far'),
        listMid: document.getElementById('list-mid'),
        listNear: document.getElementById('list-near'),
        selectedDetailBox: document.getElementById('selected-detail-box'),
        sourceBtns: document.querySelectorAll('.source-pill'),
        webcamPane: document.getElementById('webcam-pane'),
        uploadPane: document.getElementById('upload-pane'),
        mockPane: document.getElementById('mock-pane'),
        webcamStream: document.getElementById('webcam-stream'),
        webcamCanvas: document.getElementById('webcam-canvas'),
        btnToggleCam: document.getElementById('btn-toggle-cam'),
        camToggleText: document.getElementById('cam-toggle-text'),
        btnCaptureScan: document.getElementById('btn-capture-scan'),
        cameraOfflineMsg: document.getElementById('camera-offline-msg'),
        dropZone: document.getElementById('drop-zone'),
        fileInput: document.getElementById('file-input'),
        btnLoadSamplePhoto: document.getElementById('btn-load-sample-photo'),
        uploadPreviewContainer: document.getElementById('upload-preview-container'),
        uploadPreviewImg: document.getElementById('upload-preview-img'),
        btnScanUpload: document.getElementById('btn-scan-upload'),
        btnTriggerMock: document.getElementById('btn-trigger-mock'),
        currentScanSummary: document.getElementById('current-scan-summary'),
        detectedCounter: document.getElementById('detected-counter'),
        detectionsTbody: document.getElementById('detections-tbody'),
        btnLoadDiffTest: document.getElementById('btn-load-diff-test'),
        btnRefreshDiff: document.getElementById('btn-refresh-diff'),
        diffPrevTitle: document.getElementById('diff-prev-title'),
        diffPrevTime: document.getElementById('diff-prev-time'),
        diffLatestTitle: document.getElementById('diff-latest-title'),
        diffLatestTime: document.getElementById('diff-latest-time'),
        metricSameCount: document.getElementById('metric-same-count'),
        metricMovedCount: document.getElementById('metric-moved-count'),
        metricMissingCount: document.getElementById('metric-missing-count'),
        metricNewCount: document.getElementById('metric-new-count'),
        diffItemsContainer: document.getElementById('diff-items-container'),
        correctionForm: document.getElementById('correction-form'),
        factObjName: document.getElementById('fact-obj-name'),
        factRelation: document.getElementById('fact-relation'),
        factRefObj: document.getElementById('fact-ref-obj'),
        factNote: document.getElementById('fact-note'),
        correctionsTbody: document.getElementById('corrections-tbody'),
        factsCounter: document.getElementById('facts-counter'),
    };

    // ===================================================================
    // ARIA & CONTRAST
    // ===================================================================
    function announceAria(message) {
        if (!dom.ariaAnnouncer) return;
        dom.ariaAnnouncer.textContent = '';
        setTimeout(() => { dom.ariaAnnouncer.textContent = message; }, 50);
    }

    function applyHighContrast(enabled) {
        state.highContrast = enabled;
        localStorage.setItem('echomap_contrast', enabled);
        document.body.classList.toggle('high-contrast', enabled);
        if (dom.contrastToggleBtn) dom.contrastToggleBtn.classList.toggle('active', enabled);
        announceAria(enabled ? 'High contrast enabled' : 'Standard mode');
        refreshIcons();
    }

    // ===================================================================
    // E.D.I.T.H. PROSODIC VOICE ENGINE (UPS & DOWNS)
    // ===================================================================
    function stopAllSpeech() {
        if (state.activeAudio) {
            try { state.activeAudio.pause(); state.activeAudio.currentTime = 0; } catch (e) {}
            state.activeAudio = null;
        }
        if ('speechSynthesis' in window) {
            try { window.speechSynthesis.cancel(); } catch (e) {}
        }
        if (dom.speakingBadge) dom.speakingBadge.classList.add('hidden');
        if (!state.isListening && dom.soundwaveBars) dom.soundwaveBars.classList.add('hidden');
    }

    function findEdithVoice(voices) {
        if (!voices || voices.length === 0) return null;
        const preferred = [
            'Microsoft Sonia Online (Natural)',
            'Microsoft Libby Online (Natural)',
            'Microsoft Sonia',
            'Microsoft Libby',
            'Google UK English Female',
            'Microsoft Hazel',
            'Microsoft Susan',
            'Samantha',
            'Victoria',
            'Karen',
            'Zira',
        ];
        for (const pref of preferred) {
            const found = voices.find(v => v.name.toLowerCase().includes(pref.toLowerCase()));
            if (found) return found;
        }
        return voices.find(v => v.lang.startsWith('en-GB'))
            || voices.find(v => v.lang.startsWith('en'))
            || voices[0];
    }

    function initVoiceEngine() {
        if (!dom.voiceSelect) return;
        dom.voiceSelect.innerHTML = '';

        const optExpressive = document.createElement('option');
        optExpressive.value = '__expressive_edith__';
        optExpressive.textContent = '✨ E.D.I.T.H. Expressive (Melodic Prosody)';
        dom.voiceSelect.appendChild(optExpressive);

        const optCloud = document.createElement('option');
        optCloud.value = '__cloud_gtts__';
        optCloud.textContent = '🌐 Cloud British Voice (gTTS)';
        dom.voiceSelect.appendChild(optCloud);

        if ('speechSynthesis' in window) {
            state.voices = window.speechSynthesis.getVoices() || [];
            state.edithVoice = findEdithVoice(state.voices);
            const enVoices = state.voices.filter(v => v.lang.startsWith('en'));
            (enVoices.length > 0 ? enVoices : state.voices).forEach(v => {
                const opt = document.createElement('option');
                opt.value = v.name;
                const isEdith = state.edithVoice && v.name === state.edithVoice.name;
                opt.textContent = isEdith ? `💎 ${v.name} (E.D.I.T.H.)` : `${v.name}`;
                dom.voiceSelect.appendChild(opt);
            });
        }

        dom.voiceSelect.value = state.selectedVoiceName || '__expressive_edith__';
    }

    function setupVoiceListeners() {
        if ('speechSynthesis' in window && window.speechSynthesis.onvoiceschanged !== undefined) {
            window.speechSynthesis.onvoiceschanged = initVoiceEngine;
        }

        if (dom.voiceSelect) {
            dom.voiceSelect.addEventListener('change', (e) => {
                state.selectedVoiceName = e.target.value;
                if (!['__expressive_edith__', '__cloud_gtts__'].includes(state.selectedVoiceName)) {
                    state.selectedVoice = state.voices.find(v => v.name === state.selectedVoiceName) || null;
                }
            });
        }

        if (dom.voiceInflection) {
            dom.voiceInflection.addEventListener('input', (e) => {
                state.inflectionLevel = parseFloat(e.target.value);
                localStorage.setItem('echomap_inflection', state.inflectionLevel);
                if (dom.inflectionVal) {
                    dom.inflectionVal.textContent = state.inflectionLevel <= 0.75
                        ? 'Subtle'
                        : state.inflectionLevel <= 1.25
                        ? 'Natural'
                        : state.inflectionLevel <= 1.75
                        ? 'Expressive'
                        : 'Dynamic';
                }
            });
        }

        if (dom.voiceRate) {
            dom.voiceRate.addEventListener('input', (e) => {
                state.speechRate = parseFloat(e.target.value);
                if (dom.rateVal) dom.rateVal.textContent = `${state.speechRate.toFixed(2)}x`;
                if (state.activeAudio) state.activeAudio.playbackRate = state.speechRate;
            });
        }
    }

    function splitProsodicClauses(text) {
        const raw = text.split(/([.!?;:]+|\s*,\s*)/g);
        const segments = [];
        let cur = '';

        for (let i = 0; i < raw.length; i++) {
            const chunk = raw[i];
            if (!chunk) continue;
            if (/^[.!?;:]+$/.test(chunk.trim())) {
                cur += chunk;
                if (cur.trim()) segments.push(cur.trim());
                cur = '';
            } else if (chunk.trim() === ',') {
                cur += ',';
                if (cur.trim().length > 12) {
                    segments.push(cur.trim());
                    cur = '';
                }
            } else {
                cur += (cur ? ' ' : '') + chunk.trim();
            }
        }
        if (cur.trim()) segments.push(cur.trim());
        return segments.length > 0 ? segments : [text];
    }

    function speakWithProsody(text) {
        if (!('speechSynthesis' in window)) return;
        window.speechSynthesis.cancel();

        const clauses = splitProsodicClauses(text);
        if (!clauses.length) return;

        if (dom.speakingBadge) dom.speakingBadge.classList.remove('hidden');
        if (dom.soundwaveBars) dom.soundwaveBars.classList.remove('hidden');

        const voiceToUse = (state.selectedVoiceName && !state.selectedVoiceName.startsWith('__'))
            ? state.voices.find(v => v.name === state.selectedVoiceName)
            : (state.edithVoice || findEdithVoice(state.voices));

        const baseRate = state.speechRate || 1.0;
        const inf = state.inflectionLevel || 1.5;
        const total = clauses.length;

        clauses.forEach((clause, index) => {
            const trimmed = clause.trim();
            if (!trimmed) return;

            const utterance = new SpeechSynthesisUtterance(trimmed);
            if (voiceToUse) utterance.voice = voiceToUse;
            utterance.lang = 'en-GB';

            const isQuestion = trimmed.endsWith('?');
            const isExclamation = trimmed.endsWith('!');
            const isFirst = index === 0;
            const isLast = index === total - 1;

            let pitch = 1.0;
            let rate = baseRate;

            if (isQuestion) {
                pitch = 1.0 + (0.24 * inf);
                rate = baseRate * 1.04;
            } else if (isExclamation) {
                pitch = 1.0 + (0.18 * inf);
                rate = baseRate * 1.06;
            } else if (isFirst && total > 1) {
                pitch = 1.0 + (0.12 * inf);
                rate = baseRate * 1.02;
            } else if (isLast && total > 1) {
                pitch = Math.max(0.75, 1.0 - (0.12 * inf));
                rate = baseRate * 0.94;
            } else {
                const undulate = (index % 2 === 0) ? (0.08 * inf) : (-0.05 * inf);
                pitch = 1.0 + undulate;
                rate = baseRate * (index % 2 === 0 ? 1.01 : 0.98);
            }

            utterance.pitch = Math.min(2.0, Math.max(0.6, pitch));
            utterance.rate = Math.min(2.0, Math.max(0.7, rate));

            if (isLast) {
                utterance.onend = () => {
                    if (dom.speakingBadge) dom.speakingBadge.classList.add('hidden');
                    if (!state.isListening && dom.soundwaveBars) dom.soundwaveBars.classList.add('hidden');
                    window._activeUtterance = null;
                };
                utterance.onerror = () => {
                    if (dom.speakingBadge) dom.speakingBadge.classList.add('hidden');
                    if (!state.isListening && dom.soundwaveBars) dom.soundwaveBars.classList.add('hidden');
                    window._activeUtterance = null;
                };
            }

            window._activeUtterance = utterance;
            window.speechSynthesis.speak(utterance);
        });

        if (window.speechSynthesis.paused) window.speechSynthesis.resume();
    }

    async function speakText(text) {
        if (!state.voiceEnabled || !text) return;
        state.lastSpokenText = text;
        stopAllSpeech();
        playChime('respond');

        if (state.selectedVoiceName === '__cloud_gtts__') {
            try {
                if (dom.speakingBadge) dom.speakingBadge.classList.remove('hidden');
                if (dom.soundwaveBars) dom.soundwaveBars.classList.remove('hidden');

                const res = await fetch('/api/tts', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ text, tld: 'co.uk' }),
                });

                if (res.ok) {
                    const blob = await res.blob();
                    const url = URL.createObjectURL(blob);
                    const audio = new Audio(url);
                    state.activeAudio = audio;
                    audio.playbackRate = state.speechRate || 1.0;
                    audio.onended = () => { stopAllSpeech(); URL.revokeObjectURL(url); };
                    audio.onerror = () => { URL.revokeObjectURL(url); speakWithProsody(text); };
                    await audio.play();
                    return;
                }
            } catch (err) {
                console.warn('Cloud TTS fallback to prosodic synth:', err);
            }
        }

        speakWithProsody(text);
    }

    // ===================================================================
    // SPEECH RECOGNITION (PUSH-TO-TALK & CONTINUOUS)
    // ===================================================================
    function initSpeechRecognition() {
        const SpeechRec = window.SpeechRecognition || window.webkitSpeechRecognition;
        if (!SpeechRec) {
            if (dom.micStatusText) dom.micStatusText.innerHTML = 'Speech API unavailable. Please type your query.';
            if (dom.micTriggerBtn) dom.micTriggerBtn.disabled = true;
            return;
        }

        state.recognition = new SpeechRec();
        state.recognition.continuous = true;
        state.recognition.interimResults = true;
        state.recognition.lang = 'en-GB';

        state.recognition.onstart = () => {
            state.isListening = true;
            playChime('listen');
            if (dom.micTriggerBtn) dom.micTriggerBtn.classList.add('listening');
            if (dom.micBtnLabel) dom.micBtnLabel.textContent = 'Listening…';
            if (dom.soundwaveBars) dom.soundwaveBars.classList.remove('hidden');
            if (dom.micStatusText) dom.micStatusText.innerHTML = 'E.D.I.T.H. is listening — speak clearly.';
            announceAria('Microphone active.');
        };

        state.recognition.onresult = (event) => {
            let interim = '';
            for (let i = event.resultIndex; i < event.results.length; i++) {
                const item = event.results[i];
                const chunk = item[0].transcript;
                if (item.isFinal) {
                    state.accumulatedTranscript = (state.accumulatedTranscript + ' ' + chunk).trim();
                } else {
                    interim += chunk;
                }
            }
            state.interimTranscript = interim;
            const full = (state.accumulatedTranscript + ' ' + interim).trim();
            if (full) {
                if (dom.liveTranscript) dom.liveTranscript.textContent = `"${full}"`;
                if (dom.textQueryInput) dom.textQueryInput.value = full;
            }

            // Auto-submit after 1.8s of silence if not holding spacebar
            clearTimeout(state.silenceTimeout);
            state.silenceTimeout = setTimeout(() => {
                if (!state.spacebarDown && state.isListening) {
                    const q = (state.accumulatedTranscript + ' ' + state.interimTranscript).trim();
                    if (q.length > 0) {
                        stopListening();
                        handleUserQuery(q);
                    }
                }
            }, 1800);
        };

        state.recognition.onerror = (event) => {
            if (event.error === 'not-allowed') {
                if (dom.micStatusText) dom.micStatusText.innerHTML = '⚠️ Mic blocked — allow access in address bar.';
                stopListening();
            } else if (event.error !== 'no-speech') {
                if (dom.micStatusText) dom.micStatusText.innerHTML = `⚠️ ${event.error} — hold Space to retry.`;
                stopListening();
            }
        };

        state.recognition.onend = () => {
            if (state.isListening && !state.spacebarDown) {
                const q = (state.accumulatedTranscript + ' ' + state.interimTranscript).trim();
                stopListening();
                if (q) handleUserQuery(q);
            } else if (!state.spacebarDown) {
                stopListening();
            }
        };
    }

    function startListening() {
        if (state.isListening) return;
        state.isListening = true;
        state.accumulatedTranscript = '';
        state.interimTranscript = '';
        clearTimeout(state.silenceTimeout);
        stopAllSpeech();
        playChime('listen');

        if (dom.micTriggerBtn) dom.micTriggerBtn.classList.add('listening');
        if (dom.micBtnLabel) dom.micBtnLabel.textContent = 'Listening…';
        if (dom.soundwaveBars) dom.soundwaveBars.classList.remove('hidden');
        if (dom.micStatusText) dom.micStatusText.innerHTML = '<span style="color:#0284c7;font-weight:700">● E.D.I.T.H. is listening — speak clearly...</span>';

        try {
            if (state.recognition) {
                state.recognition.start();
            } else {
                if (dom.micStatusText) dom.micStatusText.innerHTML = '⚠️ Web Speech API unavailable in this browser. Please type your query below.';
            }
        } catch (err) {
            if (err.name !== 'InvalidStateError') console.warn('Mic start error:', err);
        }
    }

    function stopListeningAndQuery() {
        const q = (state.accumulatedTranscript + ' ' + state.interimTranscript).trim();
        stopListening();
        if (q) {
            handleUserQuery(q);
        } else if (dom.textQueryInput && dom.textQueryInput.value.trim()) {
            handleUserQuery(dom.textQueryInput.value.trim());
        }
    }

    function stopListening() {
        state.isListening = false;
        clearTimeout(state.silenceTimeout);
        try { if (state.recognition) state.recognition.stop(); } catch (e) {}
        if (dom.micTriggerBtn) dom.micTriggerBtn.classList.remove('listening');
        if (dom.micBtnLabel) dom.micBtnLabel.textContent = 'Space to Talk';
        if (dom.soundwaveBars) dom.soundwaveBars.classList.add('hidden');
        if (dom.micStatusText) {
            dom.micStatusText.innerHTML = 'Microphone ready. Hold <kbd>Space</kbd> to speak.';
        }
    }

    // ===================================================================
    // QUERY HANDLING
    // ===================================================================
    async function handleUserQuery(query) {
        const q = (query || '').trim();
        if (!q) return;
        if (dom.liveTranscript) dom.liveTranscript.textContent = `"${q}"`;
        if (dom.textQueryInput) dom.textQueryInput.value = q;
        if (dom.responseText) dom.responseText.innerHTML = '<span style="color:#0284c7">Searching spatial memory…</span>';

        try {
            const res = await fetch('/api/query', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ query: q }),
            });
            if (!res.ok) throw new Error((await res.json()).detail || 'Query failed');
            const data = await res.json();
            displayAnswer(data.answer, data.timestamp, data.scan_id);
            speakText(data.answer);
            announceAria(`E.D.I.T.H.: ${data.answer}`);
        } catch (err) {
            const msg = `Error: ${err.message}`;
            if (dom.responseText) dom.responseText.textContent = msg;
            speakText(msg);
        }
    }

    function displayAnswer(answer, timestamp, scanId) {
        if (dom.responseText) dom.responseText.textContent = answer;
        if (timestamp && dom.responseTimestamp) {
            dom.responseTimestamp.textContent = new Date(timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
        }
        if (dom.responseScanRef) dom.responseScanRef.textContent = scanId ? `Scan #${scanId}` : 'Memory';
    }

    // ===================================================================
    // SETTINGS MODAL & GEMINI CONFIGURATION
    // ===================================================================
    async function openSettingsModal() {
        if (!dom.settingsModal) return;
        dom.settingsModal.classList.remove('hidden');
        if (dom.settingsFeedback) dom.settingsFeedback.classList.add('hidden');
        try {
            const res = await fetch('/api/settings');
            const data = await res.json();
            if (dom.settingsKeyStatus) {
                dom.settingsKeyStatus.textContent = data.configured
                    ? `Active key: ${data.masked_key}`
                    : 'No API key configured yet (Mock Demo mode)';
            }
            if (dom.settingsModel && data.model) {
                dom.settingsModel.value = data.model;
            }
        } catch (e) {}
    }

    function closeSettingsModal() {
        if (dom.settingsModal) dom.settingsModal.classList.add('hidden');
    }

    async function handleSaveSettings(testFirst = false) {
        const key = dom.settingsApiKey?.value.trim();
        const model = dom.settingsModel?.value;
        if (dom.settingsFeedback) {
            dom.settingsFeedback.className = 'settings-feedback';
            dom.settingsFeedback.textContent = 'Verifying with Google Gemini...';
            dom.settingsFeedback.classList.remove('hidden');
        }
        try {
            const res = await fetch('/api/settings', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ api_key: key, model, test_connection: testFirst || !!key }),
            });
            const data = await res.json();
            if (!res.ok) throw new Error(data.detail || 'Settings update failed');
            if (dom.settingsFeedback) {
                dom.settingsFeedback.className = 'settings-feedback success';
                dom.settingsFeedback.textContent = data.message || 'Settings saved successfully!';
            }
            if (dom.settingsApiKey) dom.settingsApiKey.value = '';
            if (dom.settingsKeyStatus) dom.settingsKeyStatus.textContent = `Active key: ${data.masked_key}`;
            fetchSystemStatus();
            if (!testFirst) {
                setTimeout(closeSettingsModal, 1400);
            }
        } catch (err) {
            if (dom.settingsFeedback) {
                dom.settingsFeedback.className = 'settings-feedback error';
                dom.settingsFeedback.textContent = `Error: ${err.message}`;
            }
        }
    }

    // ===================================================================
    // SYSTEM STATUS & DATA LOAD
    // ===================================================================
    async function fetchSystemStatus() {
        try {
            const data = await (await fetch('/api/status')).json();
            if (dom.apiStatusLabel) {
                dom.apiStatusLabel.textContent = data.gemini_api_configured
                    ? 'AI Ready'
                    : 'Demo Mode';
            }
            if (dom.floatObjectsSummary) {
                dom.floatObjectsSummary.textContent = `${data.latest_object_count || 0} objects mapped`;
            }
            refreshIcons();
        } catch (e) {}
    }

    async function loadLatestScanData() {
        try {
            const data = await (await fetch('/api/scans/latest')).json();
            state.latestScan = data.scan;
            state.latestObjects = data.objects || [];
            state.previousObjects = data.previous_objects || [];
            renderSpatialMap(data);
            renderDetectionsTable(data.objects);
            updateSectorCards(data.sectors);
            fetchSystemStatus();
            refreshIcons();
        } catch (e) { console.error('Scan data load error:', e); }
    }

    // ===================================================================
    // 2D RADAR MAP
    // ===================================================================
    function renderSpatialMap(data) {
        const svg = dom.spatialSvg;
        if (!svg) return;
        const objects = data.objects || [];
        const pairs = data.proximity_pairs || [];
        const W = 900, H = 550;
        svg.innerHTML = '';

        // Ambient Frosted Glass Shaders & Tactical Gradients
        const defs = document.createElementNS('http://www.w3.org/2000/svg', 'defs');
        defs.innerHTML = `
            <linearGradient id="radar-glass" x1="0%" y1="0%" x2="100%" y2="100%">
                <stop offset="0%" stop-color="rgba(255, 255, 255, 0.22)"/>
                <stop offset="100%" stop-color="rgba(255, 255, 255, 0.06)"/>
            </linearGradient>
            <linearGradient id="sweep-beam" x1="0%" y1="100%" x2="0%" y2="0%">
                <stop offset="0%" stop-color="rgba(2, 132, 199, 0)"/>
                <stop offset="100%" stop-color="#38bdf8"/>
            </linearGradient>
            <linearGradient id="sweep-cone" x1="0%" y1="0%" x2="100%" y2="0%">
                <stop offset="0%" stop-color="rgba(2, 132, 199, 0)"/>
                <stop offset="100%" stop-color="rgba(56, 189, 248, 0.22)"/>
            </linearGradient>
        `;
        svg.appendChild(defs);

        // Desk Surface (Translucent Frosted AeroGlass - Zero Solid White!)
        const desk = document.createElementNS('http://www.w3.org/2000/svg', 'rect');
        Object.entries({
            x: '24', y: '24', width: `${W - 48}`, height: `${H - 48}`, rx: '22',
            fill: 'url(#radar-glass)',
            stroke: 'rgba(255, 255, 255, 0.65)',
            'stroke-width': '1.5'
        }).forEach(([k, v]) => desk.setAttribute(k, v));
        svg.appendChild(desk);

        const cx = W / 2, cy = H / 2;

        // Tactical Range Rings with Glowing Cyan Ticks
        [90, 180, 270].forEach((r, i) => {
            const ring = document.createElementNS('http://www.w3.org/2000/svg', 'circle');
            Object.entries({
                cx, cy, r,
                fill: 'none',
                stroke: 'rgba(2, 132, 199, 0.22)',
                'stroke-width': '1',
                'stroke-dasharray': '6 6'
            }).forEach(([k, v]) => ring.setAttribute(k, `${v}`));
            svg.appendChild(ring);

            const lbl = document.createElementNS('http://www.w3.org/2000/svg', 'text');
            Object.entries({
                x: cx + 8, y: cy - r + 13,
                fill: '#0284c7',
                'font-size': '10',
                'font-family': 'JetBrains Mono,monospace',
                'font-weight': '700'
            }).forEach(([k, v]) => lbl.setAttribute(k, `${v}`));
            lbl.textContent = `${(i + 1) * 25}cm`;
            svg.appendChild(lbl);
        });

        // Tactile 9-Grid Guidelines
        const wS = (W - 48) / 3, hS = (H - 48) / 3;
        for (let i = 1; i <= 2; i++) {
            [
                { x1: 24 + i * wS, y1: 24, x2: 24 + i * wS, y2: H - 24 },
                { x1: 24, y1: 24 + i * hS, x2: W - 24, y2: 24 + i * hS },
            ].forEach(coords => {
                const line = document.createElementNS('http://www.w3.org/2000/svg', 'line');
                Object.entries({
                    ...coords,
                    stroke: 'rgba(15, 23, 42, 0.08)',
                    'stroke-width': '1',
                    'stroke-dasharray': '4 4'
                }).forEach(([k, v]) => line.setAttribute(k, `${v}`));
                svg.appendChild(line);
            });
        }

        // Animated Rotating Sonar Sweep Scanner Arm
        const scanArm = document.createElementNS('http://www.w3.org/2000/svg', 'g');
        scanArm.setAttribute('class', 'radar-scanner-arm');
        scanArm.innerHTML = `
            <polygon points="${cx},${cy} ${cx - 65},${cy - 250} ${cx},${cy - 265}" fill="url(#sweep-cone)"/>
            <line x1="${cx}" y1="${cy}" x2="${cx}" y2="${cy - 265}" stroke="url(#sweep-beam)" stroke-width="2.2" stroke-linecap="round"/>
        `;
        svg.appendChild(scanArm);

        // Center Coordinate Anchor Reticle
        const centerPin = document.createElementNS('http://www.w3.org/2000/svg', 'circle');
        Object.entries({ cx, cy, r: '5', fill: '#0284c7', stroke: '#ffffff', 'stroke-width': '2' }).forEach(([k, v]) => centerPin.setAttribute(k, `${v}`));
        svg.appendChild(centerPin);

        if (objects.length === 0) {
            const t = document.createElementNS('http://www.w3.org/2000/svg', 'text');
            Object.entries({
                x: W / 2, y: H / 2 + 30,
                'text-anchor': 'middle',
                fill: '#475569',
                'font-size': '14',
                'font-weight': '700'
            }).forEach(([k, v]) => t.setAttribute(k, `${v}`));
            t.textContent = 'No objects in memory. Load sample or scan desk.';
            svg.appendChild(t);
            return;
        }

        // Proximity Connecting Rays
        pairs.forEach(pair => {
            const px1 = 24 + pair.x1 * (W - 48), py1 = 24 + pair.y1 * (H - 48);
            const px2 = 24 + pair.x2 * (W - 48), py2 = 24 + pair.y2 * (H - 48);
            const line = document.createElementNS('http://www.w3.org/2000/svg', 'line');
            Object.entries({
                x1: px1, y1: py1, x2: px2, y2: py2,
                stroke: '#0284c7',
                'stroke-width': '1.5',
                'stroke-dasharray': '5 5',
                opacity: '0.6'
            }).forEach(([k, v]) => line.setAttribute(k, `${v}`));
            svg.appendChild(line);

            const mx = (px1 + px2) / 2, my = (py1 + py2) / 2;
            const bg = document.createElementNS('http://www.w3.org/2000/svg', 'rect');
            Object.entries({
                x: mx - 18, y: my - 10, width: '36', height: '20', rx: '10',
                fill: 'rgba(255, 255, 255, 0.88)',
                stroke: '#0284c7',
                'stroke-width': '1.2'
            }).forEach(([k, v]) => bg.setAttribute(k, `${v}`));
            svg.appendChild(bg);

            const dt = document.createElementNS('http://www.w3.org/2000/svg', 'text');
            Object.entries({
                x: mx, y: my + 4,
                'text-anchor': 'middle',
                fill: '#0369a1',
                'font-size': '10',
                'font-family': 'JetBrains Mono,monospace',
                'font-weight': '700'
            }).forEach(([k, v]) => dt.setAttribute(k, `${v}`));
            dt.textContent = `${Math.round(pair.distance * 100)}cm`;
            svg.appendChild(dt);
        });

        // Detected Object Nodes with Animated Pulsing Echo Rings
        objects.forEach((obj, idx) => {
            const color = PALETTE[idx % PALETTE.length];
            const x = 24 + obj.x * (W - 48), y = 24 + obj.y * (H - 48);
            const g = document.createElementNS('http://www.w3.org/2000/svg', 'g');
            g.style.cursor = 'pointer';

            // Animated expanding radar ping ripple
            const pingRing = document.createElementNS('http://www.w3.org/2000/svg', 'circle');
            Object.entries({
                cx: x, cy: y, r: '17',
                fill: 'none',
                stroke: color,
                'class': 'radar-ping-ring'
            }).forEach(([k, v]) => pingRing.setAttribute(k, `${v}`));
            g.appendChild(pingRing);

            // Halo & Primary Node
            [[x, y, 22, color, 0.22], [x, y, 16, color, 1]].forEach(([cxNode, cyNode, r, fill, opacity]) => {
                const c = document.createElementNS('http://www.w3.org/2000/svg', 'circle');
                Object.entries({
                    cx: cxNode, cy: cyNode, r, fill, opacity,
                    stroke: opacity === 1 ? '#ffffff' : 'none',
                    'stroke-width': '2.5'
                }).forEach(([k, v]) => c.setAttribute(k, `${v}`));
                g.appendChild(c);
            });

            const centerWhiteDot = document.createElementNS('http://www.w3.org/2000/svg', 'circle');
            Object.entries({ cx: x, cy: y, r: '4', fill: '#ffffff' }).forEach(([k, v]) => centerWhiteDot.setAttribute(k, `${v}`));
            g.appendChild(centerWhiteDot);

            // Translucent AeroGlass Label Tag
            const lbl = obj.name.charAt(0).toUpperCase() + obj.name.slice(1);
            const lw = lbl.length * 8 + 24;
            const bg = document.createElementNS('http://www.w3.org/2000/svg', 'rect');
            Object.entries({
                x: x + 22, y: y - 13, width: lw, height: '26', rx: '13',
                fill: 'rgba(255, 255, 255, 0.88)',
                stroke: color,
                'stroke-width': '1.6'
            }).forEach(([k, v]) => bg.setAttribute(k, `${v}`));
            g.appendChild(bg);

            const lt = document.createElementNS('http://www.w3.org/2000/svg', 'text');
            Object.entries({
                x: x + 34, y: y + 4,
                fill: '#0f172a',
                'font-size': '11',
                'font-weight': '750',
                'font-family': 'Plus Jakarta Sans,sans-serif'
            }).forEach(([k, v]) => lt.setAttribute(k, `${v}`));
            lt.textContent = lbl;
            g.appendChild(lt);

            g.addEventListener('mouseenter', (e) => showTooltip(obj, e));
            g.addEventListener('mouseleave', () => { if (dom.objectTooltip) dom.objectTooltip.classList.add('hidden'); });
            g.addEventListener('click', () => selectObject(obj));
            svg.appendChild(g);
        });
    }

    function showTooltip(obj, event) {
        if (!dom.objectTooltip) return;
        if (dom.tooltipTitle) dom.tooltipTitle.textContent = obj.name.toUpperCase();
        if (dom.tooltipSector) dom.tooltipSector.textContent = `Sector: ${obj.region_desc || '—'}`;
        if (dom.tooltipCoords) dom.tooltipCoords.textContent = `(${obj.x.toFixed(2)}, ${obj.y.toFixed(2)})`;
        if (dom.tooltipConf) dom.tooltipConf.textContent = `Confidence: ${Math.round(obj.confidence * 100)}%`;
        const dw = document.getElementById('desk-wrapper');
        if (dw) {
            const r = dw.getBoundingClientRect();
            dom.objectTooltip.style.left = `${event.clientX - r.left}px`;
            dom.objectTooltip.style.top = `${event.clientY - r.top}px`;
        }
        dom.objectTooltip.classList.remove('hidden');
    }

    function selectObject(obj) {
        state.selectedObject = obj;
        if (!dom.selectedDetailBox) return;
        const conf = Math.round(obj.confidence * 100);
        dom.selectedDetailBox.innerHTML = `
            <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:10px">
                <span style="font-size:1.05rem;font-weight:800;color:#0284c7">${obj.name.toUpperCase()}</span>
                <span style="font-family:var(--font-mono);font-size:.78rem;background:#e0f2fe;color:#0284c7;padding:2px 8px;border-radius:9999px;font-weight:700">${conf}%</span>
            </div>
            <div style="font-size:.84rem;color:#3f3f46;margin-bottom:12px">
                <strong style="color:#09090b">Sector:</strong> ${obj.region_desc}<br>
                <strong style="color:#09090b">Coords:</strong> (${(obj.x*100).toFixed(0)}%, ${(obj.y*100).toFixed(0)}%)
            </div>
            <button id="btn-ask-selected" class="pill-btn solid full-width">
                Ask: "Where is my ${obj.name}?"
            </button>`;
        document.getElementById('btn-ask-selected')?.addEventListener('click', () => {
            switchTab('tab-voice');
            handleUserQuery(`Where is my ${obj.name}?`);
        });
        announceAria(`Selected ${obj.name} in ${obj.region_desc}`);
    }

    function updateSectorCards(sectors) {
        if (!sectors) return;
        const populate = (el, cnt, items) => {
            if (!el || !cnt) return;
            cnt.textContent = `${items.length} items`;
            el.innerHTML = items.length === 0
                ? '<span class="empty-hint">No items</span>'
                : items.map(i => `<span class="object-mini-chip" data-name="${i.name}">${i.name}</span>`).join('');
            el.querySelectorAll('.object-mini-chip').forEach(chip => {
                const item = items.find(o => o.name === chip.dataset.name);
                if (item) chip.addEventListener('click', () => selectObject(item));
            });
        };
        populate(dom.listFar, dom.countFar, sectors.top || []);
        populate(dom.listMid, dom.countMid, sectors.middle || []);
        populate(dom.listNear, dom.countNear, sectors.bottom || []);
    }

    function renderDetectionsTable(objects) {
        if (dom.detectedCounter) dom.detectedCounter.textContent = `${(objects || []).length} items`;
        if (!dom.detectionsTbody) return;
        if (!objects || objects.length === 0) {
            dom.detectionsTbody.innerHTML = '<tr><td colspan="5" class="table-blank">No objects recorded yet.</td></tr>';
            return;
        }
        dom.detectionsTbody.innerHTML = objects.map(obj => `
            <tr>
                <td style="font-weight:700;color:#09090b">${obj.name}</td>
                <td>${obj.region_desc || '—'}</td>
                <td><span style="font-family:var(--font-mono);color:#0284c7;font-weight:700">${Math.round(obj.confidence*100)}%</span></td>
                <td><span style="font-family:var(--font-mono)">${obj.x.toFixed(2)}</span></td>
                <td><span style="font-family:var(--font-mono)">${obj.y.toFixed(2)}</span></td>
            </tr>`).join('');
    }

    // ===================================================================
    // WEBCAM & VISION
    // ===================================================================
    async function startCamera() {
        if (state.cameraActive) return;
        try {
            state.cameraStream = await navigator.mediaDevices.getUserMedia({ video: { facingMode: 'environment', width: { ideal: 1280 }, height: { ideal: 720 } }, audio: false });
            if (dom.webcamStream) dom.webcamStream.srcObject = state.cameraStream;
            state.cameraActive = true;
            if (dom.cameraOfflineMsg) dom.cameraOfflineMsg.classList.add('hidden');
            if (dom.camToggleText) dom.camToggleText.textContent = 'Stop Camera';
        } catch (err) {
            if (dom.cameraOfflineMsg) { dom.cameraOfflineMsg.innerHTML = '<span>⚠️ Webcam unavailable. Use Upload or Demo.</span>'; dom.cameraOfflineMsg.classList.remove('hidden'); }
            if (dom.camToggleText) dom.camToggleText.textContent = 'Start Camera';
        }
    }

    function stopCamera() {
        if (state.cameraStream) { state.cameraStream.getTracks().forEach(t => t.stop()); state.cameraStream = null; }
        state.cameraActive = false;
        if (dom.cameraOfflineMsg) dom.cameraOfflineMsg.classList.remove('hidden');
        if (dom.camToggleText) dom.camToggleText.textContent = 'Start Camera';
    }

    async function captureAndScanWebcam() {
        if (!state.cameraActive) { await startCamera(); if (!state.cameraActive) return; }
        const video = dom.webcamStream, canvas = dom.webcamCanvas;
        if (!video || !canvas) return;
        canvas.width = video.videoWidth || 640;
        canvas.height = video.videoHeight || 480;
        canvas.getContext('2d').drawImage(video, 0, 0, canvas.width, canvas.height);
        const b64 = canvas.toDataURL('image/jpeg', 0.85);
        if (dom.btnCaptureScan) { dom.btnCaptureScan.disabled = true; dom.btnCaptureScan.innerHTML = '<span>Scanning…</span>'; }
        try {
            const res = await fetch('/api/scan/base64', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ image_base64: b64, scene: 'desk' }) });
            const data = await res.json();
            if (!res.ok) throw new Error(data.detail || 'Scan failed');
            speakText(data.message); await loadLatestScanData(); switchTab('tab-map');
        } catch (err) { alert(`Scan Error: ${err.message}`); }
        finally { if (dom.btnCaptureScan) { dom.btnCaptureScan.disabled = false; dom.btnCaptureScan.innerHTML = '<i data-lucide="sparkles"></i><span>Capture with Gemini</span>'; refreshIcons(); } }
    }

    // ===================================================================
    // MOVEMENT DIFF
    // ===================================================================
    async function loadMovementDiff() {
        try {
            const data = await (await fetch('/api/diff')).json();
            if (!data.has_diff) {
                if (dom.diffItemsContainer) dom.diffItemsContainer.innerHTML = '<div class="diff-blank"><i data-lucide="history"></i><p>Need at least 2 scans. Click <strong>Simulate Movement</strong> above.</p></div>';
                ['Same', 'Moved', 'Missing', 'New'].forEach(k => { const el = dom[`metric${k}Count`]; if (el) el.textContent = '0'; });
                refreshIcons(); return;
            }
            if (data.prev_scan && dom.diffPrevTitle) { dom.diffPrevTitle.textContent = `Scan #${data.prev_scan.id}`; dom.diffPrevTime.textContent = new Date(data.prev_scan.created_at).toLocaleTimeString(); }
            if (data.latest_scan && dom.diffLatestTitle) { dom.diffLatestTitle.textContent = `Scan #${data.latest_scan.id}`; dom.diffLatestTime.textContent = new Date(data.latest_scan.created_at).toLocaleTimeString(); }
            let same = 0, moved = 0, missing = 0, added = 0;
            if (dom.diffItemsContainer) {
                dom.diffItemsContainer.innerHTML = '';
                (data.diffs || []).forEach(item => {
                    let pill = 'stationary', label = 'STATIONARY';
                    if (item.status === 'possibly_moved') { moved++; pill = 'moved'; label = 'MOVED'; }
                    else if (item.status === 'not_detected') { missing++; pill = 'missing'; label = 'NOT DETECTED'; }
                    else if (item.status === 'new') { added++; pill = 'new'; label = 'NEW'; }
                    else same++;
                    const card = document.createElement('div');
                    card.className = 'diff-event-card';
                    card.innerHTML = `<span class="diff-status-pill ${pill}">${label}</span><span class="diff-event-desc"><strong>${item.name.toUpperCase()}</strong>: ${item.description}</span>`;
                    dom.diffItemsContainer.appendChild(card);
                });
            }
            if (dom.metricSameCount) dom.metricSameCount.textContent = same;
            if (dom.metricMovedCount) dom.metricMovedCount.textContent = moved;
            if (dom.metricMissingCount) dom.metricMissingCount.textContent = missing;
            if (dom.metricNewCount) dom.metricNewCount.textContent = added;
            refreshIcons();
        } catch (e) { console.error('Diff load error:', e); }
    }

    // ===================================================================
    // CORRECTIONS
    // ===================================================================
    async function loadCorrections() {
        try {
            const data = await (await fetch('/api/corrections')).json();
            const corrs = data.corrections || [];
            if (dom.factsCounter) dom.factsCounter.textContent = `${corrs.length} facts`;
            if (!dom.correctionsTbody) return;
            if (corrs.length === 0) { dom.correctionsTbody.innerHTML = '<tr><td colspan="5" class="table-blank">No tactile facts recorded yet.</td></tr>'; return; }
            dom.correctionsTbody.innerHTML = '';
            corrs.forEach(corr => {
                const tr = document.createElement('tr');
                tr.innerHTML = `<td style="font-weight:700;color:#09090b">${corr.object_name}</td><td><span style="background:#e0f2fe;color:#0284c7;padding:3px 8px;border-radius:9999px;font-size:.75rem;font-weight:700">${corr.relation_type}</span></td><td style="font-weight:600">${corr.reference_object}</td><td style="color:#64748b">${corr.note || '—'}</td><td><button class="pill-btn warning del-btn" data-id="${corr.id}">Remove</button></td>`;
                tr.querySelector('.del-btn').addEventListener('click', async () => {
                    await fetch(`/api/corrections/${corr.id}`, { method: 'DELETE' });
                    loadCorrections();
                });
                dom.correctionsTbody.appendChild(tr);
            });
        } catch (e) { console.error('Corrections load error:', e); }
    }

    async function handleAddCorrection(e) {
        e.preventDefault();
        const obj = dom.factObjName?.value.trim(), rel = dom.factRelation?.value, ref = dom.factRefObj?.value.trim(), note = dom.factNote?.value.trim();
        if (!obj || !ref) return;
        try {
            const res = await fetch('/api/corrections', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ object_name: obj, relation_type: rel, reference_object: ref, note }) });
            if (res.ok) { if (dom.factObjName) dom.factObjName.value = ''; if (dom.factRefObj) dom.factRefObj.value = ''; if (dom.factNote) dom.factNote.value = ''; await loadCorrections(); speakText(`Learned: ${obj} is ${rel} ${ref}.`); }
        } catch (err) { alert(`Error: ${err.message}`); }
    }

    // ===================================================================
    // NAVIGATION
    // ===================================================================
    function switchTab(tabId) {
        if (!tabId) return;
        state.activeTab = tabId;
        const allTabBtns = document.querySelectorAll('.nav-link');
        allTabBtns.forEach(t => { 
            const isMatch = t.getAttribute('data-tab') === tabId; 
            t.classList.toggle('active', isMatch); 
            t.setAttribute('aria-selected', isMatch); 
        });

        const allPanels = document.querySelectorAll('.deck-tab-view');
        allPanels.forEach(p => p.classList.toggle('active', p.id === tabId));

        if (tabId === 'tab-map') loadLatestScanData();
        else if (tabId === 'tab-diff') loadMovementDiff();
        else if (tabId === 'tab-corrections') loadCorrections();
        else if (tabId === 'tab-scan') { if (dom.sourceBtns[0]?.classList.contains('active')) startCamera(); }
        else if (state.cameraActive) stopCamera();

        refreshIcons();
    }

    // ===================================================================
    // DEMO ACTIONS
    // ===================================================================
    async function loadSampleMemory() {
        try {
            const data = await (await fetch('/api/demo/sample', { method: 'POST' })).json();
            const msg = `Loaded ${data.object_count} objects into spatial memory.`;
            displayAnswer(msg); speakText(msg); await loadLatestScanData();
        } catch (err) { alert(`Error: ${err.message}`); }
    }

    async function simulateDiffAction() {
        try {
            await fetch('/api/demo/simulate-diff', { method: 'POST' });
            const msg = 'Simulated movement: keys moved, mug missing, glasses added.';
            displayAnswer(msg); speakText(msg); await loadLatestScanData(); switchTab('tab-diff');
        } catch (err) { alert(`Error: ${err.message}`); }
    }

    async function clearMemoryAction() {
        if (!confirm('Clear all scans and corrections?')) return;
        try { await fetch('/api/demo/clear', { method: 'POST' }); const msg = 'Spatial memory cleared.'; displayAnswer(msg); speakText(msg); await loadLatestScanData(); } catch (err) { alert(`Error: ${err.message}`); }
    }

    // ===================================================================
    // ATTACH EVENT LISTENERS
    // ===================================================================
    function attachEventListeners() {
        // Robust event delegation for tab navigation (works on button or child span clicks)
        document.addEventListener('click', (e) => {
            const tabBtn = e.target.closest('.nav-link');
            if (tabBtn) {
                e.preventDefault();
                const tabId = tabBtn.getAttribute('data-tab');
                if (tabId) switchTab(tabId);
            }
        });

        if (dom.floatRadarPreview) {
            dom.floatRadarPreview.addEventListener('click', () => switchTab('tab-map'));
        }

        if (dom.contrastToggleBtn) dom.contrastToggleBtn.addEventListener('click', () => applyHighContrast(!state.highContrast));

        if (dom.ttsToggleBtn) {
            dom.ttsToggleBtn.addEventListener('click', () => {
                state.voiceEnabled = !state.voiceEnabled;
                localStorage.setItem('echomap_voice', state.voiceEnabled);
                dom.ttsToggleBtn.classList.toggle('active', state.voiceEnabled);
                if (!state.voiceEnabled) stopAllSpeech();
            });
        }

        // Settings Modal Open/Close
        if (dom.btnOpenSettings) dom.btnOpenSettings.addEventListener('click', openSettingsModal);
        if (dom.btnCloseSettings) dom.btnCloseSettings.addEventListener('click', closeSettingsModal);
        if (dom.settingsModal) {
            dom.settingsModal.addEventListener('click', (e) => {
                if (e.target === dom.settingsModal) closeSettingsModal();
            });
        }

        // Settings Key Visibility Toggle
        if (dom.btnToggleKeyVis && dom.settingsApiKey) {
            dom.btnToggleKeyVis.addEventListener('click', () => {
                const isPass = dom.settingsApiKey.type === 'password';
                dom.settingsApiKey.type = isPass ? 'text' : 'password';
                dom.btnToggleKeyVis.innerHTML = isPass ? '<i data-lucide="eye-off"></i>' : '<i data-lucide="eye"></i>';
                refreshIcons();
            });
        }

        // Settings Save & Test
        if (dom.settingsForm) {
            dom.settingsForm.addEventListener('submit', (e) => {
                e.preventDefault();
                handleSaveSettings(false);
            });
        }
        if (dom.btnTestKey) {
            dom.btnTestKey.addEventListener('click', () => handleSaveSettings(true));
        }

        // Test Voice Prosody
        if (dom.btnTestVoice) {
            dom.btnTestVoice.addEventListener('click', () => {
                const testUtterance = "Hello! I am E.D.I.T.H. Your keys are right in the centre, beside your phone. Would you like me to guide your hand?";
                displayAnswer(testUtterance);
                speakWithProsody(testUtterance);
            });
        }

        if (dom.btnLoadSample) dom.btnLoadSample.addEventListener('click', loadSampleMemory);
        if (dom.btnSimulateDiff) dom.btnSimulateDiff.addEventListener('click', simulateDiffAction);
        if (dom.btnClearMemory) dom.btnClearMemory.addEventListener('click', clearMemoryAction);

        dom.queryChips.forEach(chip => chip.addEventListener('click', () => handleUserQuery(chip.getAttribute('data-query'))));

        if (dom.queryForm) dom.queryForm.addEventListener('submit', e => { e.preventDefault(); handleUserQuery(dom.textQueryInput?.value); });
        if (dom.btnSendQuery) dom.btnSendQuery.addEventListener('click', e => { e.preventDefault(); handleUserQuery(dom.textQueryInput?.value); });

        if (dom.btnReplaySpeech) dom.btnReplaySpeech.addEventListener('click', () => speakText(state.lastSpokenText || dom.responseText?.textContent));
        if (dom.btnCopyResponse) dom.btnCopyResponse.addEventListener('click', () => { if (dom.responseText) navigator.clipboard.writeText(dom.responseText.textContent); announceAria('Copied.'); });

        if (dom.btnRadarSweep) {
            dom.btnRadarSweep.addEventListener('click', () => {
                playChime('listen');
                if (dom.radarBeam) { dom.radarBeam.classList.remove('hidden', 'animating'); void dom.radarBeam.offsetWidth; dom.radarBeam.classList.add('animating'); setTimeout(() => dom.radarBeam.classList.add('hidden'), 2100); }
            });
        }
        if (dom.btnRefreshMap) dom.btnRefreshMap.addEventListener('click', loadLatestScanData);

        // Click-to-Talk Mic Trigger
        if (dom.micTriggerBtn) {
            dom.micTriggerBtn.addEventListener('click', (e) => {
                e.preventDefault();
                if (state.isListening) {
                    stopListeningAndQuery();
                } else {
                    startListening();
                }
            });
        }

        dom.sourceBtns.forEach(btn => btn.addEventListener('click', () => {
            dom.sourceBtns.forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            const src = btn.getAttribute('data-source');
            if (dom.webcamPane) dom.webcamPane.classList.toggle('hidden', src !== 'webcam');
            if (dom.uploadPane) dom.uploadPane.classList.toggle('hidden', src !== 'upload');
            if (dom.mockPane) dom.mockPane.classList.toggle('hidden', src !== 'mock');
            src === 'webcam' ? startCamera() : stopCamera();
            refreshIcons();
        }));

        if (dom.btnToggleCam) dom.btnToggleCam.addEventListener('click', () => state.cameraActive ? stopCamera() : startCamera());
        if (dom.btnCaptureScan) dom.btnCaptureScan.addEventListener('click', captureAndScanWebcam);

        if (dom.dropZone && dom.fileInput) {
            dom.dropZone.addEventListener('click', () => dom.fileInput.click());
            dom.dropZone.addEventListener('dragover', e => { e.preventDefault(); dom.dropZone.style.borderColor = '#18181b'; });
            dom.dropZone.addEventListener('dragleave', () => { dom.dropZone.style.borderColor = ''; });
            dom.dropZone.addEventListener('drop', e => { e.preventDefault(); dom.dropZone.style.borderColor = ''; if (e.dataTransfer.files[0]) handleFileUpload(e.dataTransfer.files[0]); });
            dom.fileInput.addEventListener('change', e => { if (e.target.files[0]) handleFileUpload(e.target.files[0]); });
        }

        if (dom.btnLoadSamplePhoto) {
            dom.btnLoadSamplePhoto.addEventListener('click', async () => {
                try {
                    const res = await fetch('/static/images/sample_desk.jpg');
                    const blob = await res.blob();
                    const file = new File([blob], 'sample_desk.jpg', { type: 'image/jpeg' });
                    handleFileUpload(file);
                } catch (e) {
                    console.error('Failed to load sample photo:', e);
                }
            });
        }

        if (dom.btnTriggerMock) dom.btnTriggerMock.addEventListener('click', loadSampleMemory);
        if (dom.btnLoadDiffTest) dom.btnLoadDiffTest.addEventListener('click', simulateDiffAction);
        if (dom.btnRefreshDiff) dom.btnRefreshDiff.addEventListener('click', loadMovementDiff);
        if (dom.correctionForm) dom.correctionForm.addEventListener('submit', handleAddCorrection);

        // PUSH-TO-TALK (HOLD SPACEBAR) & SHORTCUTS
        window.addEventListener('keydown', e => {
            const tag = document.activeElement?.tagName.toLowerCase();
            const inInput = ['input', 'textarea', 'select'].includes(tag);

            if (e.code === 'Space' && !inInput && !e.repeat) {
                e.preventDefault();
                document.activeElement?.blur();
                if (!state.spacebarDown) {
                    state.spacebarDown = true;
                    // Automatically switch to Voice Assistant if on another tab
                    if (state.currentTab !== 'tab-voice') {
                        switchTab('tab-voice');
                    }
                    startListening();
                }
            } else if (e.key === 'Escape') {
                closeSettingsModal();
            } else if ((e.key === 'r' || e.key === 'R') && !inInput) {
                e.preventDefault();
                speakText(state.lastSpokenText || dom.responseText?.textContent);
            } else if ('12345'.includes(e.key) && !inInput && !e.repeat) {
                switchTab(['tab-voice','tab-map','tab-scan','tab-diff','tab-corrections'][+e.key - 1]);
            }
        });

        window.addEventListener('keyup', e => {
            const tag = document.activeElement?.tagName.toLowerCase();
            const inInput = ['input', 'textarea', 'select'].includes(tag);

            if (e.code === 'Space' && !inInput) {
                e.preventDefault();
                if (state.spacebarDown) {
                    state.spacebarDown = false;
                    // Grace window so user speech tail is captured
                    setTimeout(() => {
                        if (state.isListening && !state.spacebarDown) {
                            stopListeningAndQuery();
                        }
                    }, 350);
                }
            }
        });
    }

    async function handleFileUpload(file) {
        if (!dom.uploadPreviewImg || !dom.uploadPreviewContainer) return;
        const reader = new FileReader();
        reader.onload = async (e) => {
            const dataUrl = e.target.result;
            dom.uploadPreviewImg.src = dataUrl;
            dom.uploadPreviewContainer.classList.remove('hidden');
            if (dom.btnScanUpload) {
                dom.btnScanUpload.onclick = async () => {
                    dom.btnScanUpload.disabled = true;
                    dom.btnScanUpload.innerHTML = '<span>Scanning with Gemini…</span>';

                    try {
                        // Normalize any image format (WebP, AVIF, JFIF, etc.) to clean JPEG bytes via Canvas
                        let uploadBlob = null;
                        try {
                            const offscreen = document.createElement('canvas');
                            const w = dom.uploadPreviewImg.naturalWidth || dom.uploadPreviewImg.width || 1024;
                            const h = dom.uploadPreviewImg.naturalHeight || dom.uploadPreviewImg.height || 768;
                            offscreen.width = w;
                            offscreen.height = h;
                            const ctx = offscreen.getContext('2d');
                            ctx.drawImage(dom.uploadPreviewImg, 0, 0, w, h);
                            uploadBlob = await new Promise(resolve => offscreen.toBlob(resolve, 'image/jpeg', 0.95));
                        } catch (cErr) {
                            console.warn('Canvas rasterization fallback to raw file:', cErr);
                        }

                        const formData = new FormData();
                        if (uploadBlob) {
                            formData.append('file', uploadBlob, 'desk_scan.jpg');
                        } else {
                            formData.append('file', file);
                        }

                        const res = await fetch('/api/scan/upload', { method: 'POST', body: formData });
                        const data = await res.json();
                        if (!res.ok) throw new Error(data.detail || 'Upload failed');
                        speakText(data.message);
                        await loadLatestScanData();
                        switchTab('tab-map');
                    } catch (err) {
                        alert(`Upload Error: ${err.message}`);
                    } finally {
                        dom.btnScanUpload.disabled = false;
                        dom.btnScanUpload.innerHTML = '<i data-lucide="sparkles"></i><span>Scan with Gemini</span>';
                        refreshIcons();
                    }
                };
            }
        };
        reader.readAsDataURL(file);
    }

    // ===================================================================
    // BOOT
    // ===================================================================
    function init() {
        applyHighContrast(state.highContrast);
        initVoiceEngine();
        setupVoiceListeners();
        initSpeechRecognition();
        attachEventListeners();
        fetchSystemStatus();
        loadLatestScanData();
        loadCorrections();
        refreshIcons();

        // Logo Click -> Navigate to Home Tab
        const brandLogo = document.querySelector('.nav-brand');
        if (brandLogo) {
            brandLogo.addEventListener('click', (e) => {
                e.preventDefault();
                switchTab('tab-voice');
            });
        }
    }

    document.addEventListener('DOMContentLoaded', init);
})();
