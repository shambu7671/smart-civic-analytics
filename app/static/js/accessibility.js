/**
 * SmartCivic AI — Voice Assistant, Speech-to-Text, Text-to-Speech, & A11y Engine
 * Implements WCAG 2.1 AA accessibility, Web Speech API, Voice Commands & Synthesis
 */

const A11Y = {
  settings: {
    voiceControl: localStorage.getItem('a11y_voice_control') === 'true',
    readAloud: localStorage.getItem('a11y_read_aloud') === 'true',
    highContrast: localStorage.getItem('a11y_high_contrast') === 'true',
    largeText: localStorage.getItem('a11y_large_text') === 'true',
    reduceMotion: localStorage.getItem('a11y_reduce_motion') === 'true',
    keyboardFocus: localStorage.getItem('a11y_keyboard_focus') === 'true'
  },

  recognition: null,
  isRecording: false,
  isVoiceAssistantActive: false,
  synth: window.speechSynthesis || null,
  currentUtterance: null,
  isSpeaking: false,
  isPaused: false,

  init() {
    this.applySettings();
    this.setupSpeechRecognition();
    this.setupLiveRegion();
    this.renderAccessibilityMenu();

    // Listen for language changes to adjust speech synthesis & recognition
    window.addEventListener('languageChanged', (e) => {
      if (this.recognition && this.isRecording) {
        this.stopSpeechRecognition();
      }
      this.cancelSpeech();
    });

    if (this.settings.voiceControl) {
      this.startVoiceAssistant();
    }
  },

  applySettings() {
    const b = document.body;
    b.classList.toggle('a11y-high-contrast', this.settings.highContrast);
    b.classList.toggle('a11y-large-text', this.settings.largeText);
    b.classList.toggle('a11y-reduce-motion', this.settings.reduceMotion);
    b.classList.toggle('a11y-keyboard-focus', this.settings.keyboardFocus);
  },

  saveSetting(key, val) {
    this.settings[key] = val;
    localStorage.setItem(`a11y_${key}`, String(val));
    this.applySettings();
    this.renderAccessibilityMenu();
  },

  setupLiveRegion() {
    let region = document.getElementById('a11y-live-region');
    if (!region) {
      region = document.createElement('div');
      region.id = 'a11y-live-region';
      region.setAttribute('aria-live', 'polite');
      region.setAttribute('aria-atomic', 'true');
      region.className = 'visually-hidden';
      document.body.appendChild(region);
    }
    window.a11yAnnounce = (msg) => {
      if (region) {
        region.textContent = '';
        setTimeout(() => { region.textContent = msg; }, 50);
      }
    };
  },

  /* -------------------------------------------------------------
   * 1. Speech-to-Text (Voice Complaint Input)
   * ----------------------------------------------------------- */
  setupSpeechRecognition() {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRecognition) {
      console.info('[A11y] Web Speech Recognition is not supported in this browser.');
      return;
    }
    this.recognition = new SpeechRecognition();
    this.recognition.continuous = true;
    this.recognition.interimResults = true;

    this.recognition.onstart = () => {
      this.isRecording = true;
      this.updateVoiceUI(true);
      window.a11yAnnounce(window.t('voice_recording_active', 'Microphone active. Speak your complaint.'));
    };

    this.recognition.onresult = (event) => {
      let interim = '';
      let final = '';

      for (let i = event.resultIndex; i < event.results.length; ++i) {
        if (event.results[i].isFinal) {
          final += event.results[i][0].transcript;
        } else {
          interim += event.results[i][0].transcript;
        }
      }

      if (this.onSpeechResultCallback) {
        this.onSpeechResultCallback(final, interim);
      }

      // If voice assistant mode is active, parse voice command from final result
      if (this.isVoiceAssistantActive && final) {
        this.handleVoiceCommand(final.trim());
      }
    };

    this.recognition.onerror = (event) => {
      console.warn('[A11y] Speech recognition event:', event.error);
      this.isRecording = false;
      this.updateVoiceUI(false);

      if (event.error === 'not-allowed') {
        window.showAlert?.(window.t('voice_permission_denied', 'Microphone permission denied.'), 'warning');
      } else if (event.error === 'no-speech') {
        // Silent timeout or no speech
      } else {
        window.showAlert?.(`Voice error: ${event.error}`, 'warning');
      }
    };

    this.recognition.onend = () => {
      this.isRecording = false;
      this.updateVoiceUI(false);
      // Auto-restart if voice assistant mode is toggled ON
      if (this.isVoiceAssistantActive) {
        try { this.recognition.start(); } catch (_) {}
      }
    };
  },

  startVoiceComplaint(targetTextarea, onUpdate) {
    if (!this.recognition) {
      window.showAlert?.(window.t('voice_not_supported', 'Voice recognition is not supported in this browser. Please use text input.'), 'warning');
      return;
    }

    const locale = window.I18N ? window.I18N.getSpeechLocale() : 'en-IN';
    this.recognition.lang = locale;

    let initialText = targetTextarea ? targetTextarea.value : '';

    this.onSpeechResultCallback = (final, interim) => {
      if (targetTextarea) {
        const separator = initialText && !initialText.endsWith(' ') ? ' ' : '';
        targetTextarea.value = initialText + (final ? separator + final : '') + (interim ? ' ' + interim : '');
        // Trigger input event for automatic language detection / validation
        targetTextarea.dispatchEvent(new Event('input', { bubbles: true }));
      }
      if (onUpdate) onUpdate(final, interim);
    };

    try {
      this.recognition.start();
    } catch (err) {
      console.warn('[A11y] Could not start speech recognition:', err);
    }
  },

  stopVoiceComplaint() {
    if (this.recognition && this.isRecording) {
      try { this.recognition.stop(); } catch (_) {}
    }
    this.isRecording = false;
    this.updateVoiceUI(false);
  },

  updateVoiceUI(active) {
    const btn = document.getElementById('btn-voice-record');
    const badge = document.getElementById('voice-status-indicator');
    if (btn) {
      if (active) {
        btn.classList.remove('btn-outline-primary');
        btn.classList.add('btn-danger', 'pulse-recording');
        btn.innerHTML = `<i class="bi bi-mic-fill me-1"></i><span>${window.t('voice_btn_stop', 'Stop Recording')}</span>`;
      } else {
        btn.classList.remove('btn-danger', 'pulse-recording');
        btn.classList.add('btn-outline-primary');
        btn.innerHTML = `<i class="bi bi-mic me-1"></i><span>${window.t('voice_btn_speak', 'Speak Your Complaint')}</span>`;
      }
    }
    if (badge) {
      badge.classList.toggle('d-none', !active);
    }
  },

  /* -------------------------------------------------------------
   * 2. Voice Control / Voice Assistant Commands
   * ----------------------------------------------------------- */
  toggleVoiceAssistant() {
    this.isVoiceAssistantActive = !this.isVoiceAssistantActive;
    this.saveSetting('voiceControl', this.isVoiceAssistantActive);
    if (this.isVoiceAssistantActive) {
      this.startVoiceAssistant();
    } else {
      this.stopVoiceAssistant();
    }
  },

  startVoiceAssistant() {
    if (!this.recognition) return;
    this.isVoiceAssistantActive = true;
    try {
      this.recognition.lang = window.I18N ? window.I18N.getSpeechLocale() : 'en-IN';
      this.recognition.start();
      window.showAlert?.(window.t('voice_control_enabled', 'Voice Assistant active. Say commands like "Open complaint form" or "Change language to Marathi".'), 'info');
      this.showVoiceBanner(true);
    } catch (_) {}
  },

  stopVoiceAssistant() {
    this.isVoiceAssistantActive = false;
    try { this.recognition.stop(); } catch (_) {}
    this.showVoiceBanner(false);
  },

  showVoiceBanner(show) {
    let banner = document.getElementById('voice-assistant-banner');
    if (!banner && show) {
      banner = document.createElement('div');
      banner.id = 'voice-assistant-banner';
      banner.className = 'voice-assistant-bar shadow-sm d-flex align-items-center justify-content-between px-3 py-2';
      banner.innerHTML = `
        <div class="d-flex align-items-center gap-2">
          <span class="pulse-dot"></span>
          <span class="small fw-semibold" id="voice-banner-text">${window.t('voice_listening_cmd', 'Voice Assistant Active...')}</span>
        </div>
        <div class="d-flex align-items-center gap-2">
          <button class="btn btn-sm btn-link text-white text-decoration-none p-0" onclick="window.A11Y.toggleVoiceAssistant()">
            <i class="bi bi-x-circle"></i>
          </button>
        </div>
      `;
      document.body.appendChild(banner);
    }
    if (banner) banner.style.display = show ? 'flex' : 'none';
  },

  handleVoiceCommand(rawText) {
    const text = rawText.toLowerCase();
    console.log('[Voice Command Received]:', text);

    const bannerText = document.getElementById('voice-banner-text');
    if (bannerText) bannerText.textContent = `"${text}"`;

    // 1. OPEN_COMPLAINT_FORM
    if (text.includes('open complaint') || text.includes('report issue') || text.includes('तक्रार नोंदवा') || text.includes('शिकायत दर्ज')) {
      this.executeCommand('OPEN_COMPLAINT_FORM', () => location.href = '/citizen/report');
      return;
    }

    // 2. OPEN_DASHBOARD / SHOW_COMPLAINTS
    if (text.includes('dashboard') || text.includes('डॅशबोर्ड') || text.includes('डैशबोर्ड') || text.includes('my reports') || text.includes('माझ्या तक्रारी')) {
      this.executeCommand('OPEN_DASHBOARD', () => location.href = '/citizen/dashboard');
      return;
    }

    // 3. MAP
    if (text.includes('map') || text.includes('नकाशा') || text.includes('मानचित्र')) {
      this.executeCommand('OPEN_MAP', () => location.href = '/map');
      return;
    }

    // 4. SUBMIT_COMPLAINT
    if (text.includes('submit complaint') || text.includes('submit report') || text.includes('सबमिट करा') || text.includes('जमा करें')) {
      const form = document.getElementById('report-form');
      if (form) {
        this.executeCommand('SUBMIT_COMPLAINT', () => form.requestSubmit());
      }
      return;
    }

    // 5. START_RECORDING / STOP_RECORDING
    if (text.includes('start recording') || text.includes('बोलना शुरू') || text.includes('रेकॉर्डिंग सुरू')) {
      const btn = document.getElementById('btn-voice-record');
      if (btn && !this.isRecording) {
        this.executeCommand('START_RECORDING', () => btn.click());
      }
      return;
    }
    if (text.includes('stop recording') || text.includes('बोलना बंद') || text.includes('रेकॉर्डिंग थांबवा')) {
      const btn = document.getElementById('btn-voice-record');
      if (btn && this.isRecording) {
        this.executeCommand('STOP_RECORDING', () => btn.click());
      }
      return;
    }

    // 6. CLEAR_COMPLAINT
    if (text.includes('clear complaint') || text.includes('clear text') || text.includes('साफ करा') || text.includes('साफ करें')) {
      const desc = document.getElementById('description');
      if (desc) {
        this.executeCommand('CLEAR_COMPLAINT', () => { desc.value = ''; desc.dispatchEvent(new Event('input')); });
      }
      return;
    }

    // 7. CHANGE_LANGUAGE
    if (text.includes('marathi') || text.includes('मराठी')) {
      this.executeCommand('CHANGE_LANGUAGE_MR', () => window.I18N.setLanguage('mr'));
      return;
    }
    if (text.includes('hindi') || text.includes('हिन्दी') || text.includes('हिंदी')) {
      this.executeCommand('CHANGE_LANGUAGE_HI', () => window.I18N.setLanguage('hi'));
      return;
    }
    if (text.includes('english') || text.includes('इंग्रजी') || text.includes('अंग्रेजी')) {
      this.executeCommand('CHANGE_LANGUAGE_EN', () => window.I18N.setLanguage('en'));
      return;
    }

    // 8. READ_ANALYSIS / READ_COMPLAINT
    if (text.includes('read analysis') || text.includes('विश्लेषण वाचा') || text.includes('read complaint') || text.includes('तक्रार वाचा')) {
      this.executeCommand('READ_ANALYSIS', () => this.readCurrentPageContext());
      return;
    }

    // 9. GO_BACK
    if (text.includes('go back') || text.includes('मागे जा') || text.includes('पीछे जाएं')) {
      this.executeCommand('GO_BACK', () => history.back());
      return;
    }
  },

  executeCommand(intent, action) {
    window.showAlert?.(`${window.t('voice_cmd_executed', 'Voice Command')}: ${intent}`, 'success');
    window.a11yAnnounce(`Command ${intent} executed`);
    if (action) action();
  },

  /* -------------------------------------------------------------
   * 3. Text-to-Speech (Read Aloud)
   * ----------------------------------------------------------- */
  speak(text) {
    if (!this.synth) {
      window.showAlert?.('Text-to-Speech is not supported in this browser.', 'warning');
      return;
    }

    this.cancelSpeech();

    const utterance = new SpeechSynthesisUtterance(text);
    const lang = window.I18N ? window.I18N.currentLang : 'en';
    const speechLocale = window.I18N ? window.I18N.getSpeechLocale() : 'en-IN';
    utterance.lang = speechLocale;
    utterance.rate = 0.95;

    // Try finding matching voice
    const voices = this.synth.getVoices();
    const voice = voices.find(v => v.lang === speechLocale || v.lang.startsWith(lang));
    if (voice) utterance.voice = voice;

    utterance.onstart = () => {
      this.isSpeaking = true;
      this.isPaused = false;
      this.updateTTSControlsUI('speaking');
    };

    utterance.onend = () => {
      this.isSpeaking = false;
      this.isPaused = false;
      this.updateTTSControlsUI('idle');
    };

    utterance.onerror = (e) => {
      console.warn('[TTS] Error:', e);
      this.isSpeaking = false;
      this.isPaused = false;
      this.updateTTSControlsUI('idle');
    };

    this.currentUtterance = utterance;
    this.synth.speak(utterance);
  },

  pauseSpeech() {
    if (this.synth && this.isSpeaking) {
      this.synth.pause();
      this.isPaused = true;
      this.updateTTSControlsUI('paused');
    }
  },

  resumeSpeech() {
    if (this.synth && this.isPaused) {
      this.synth.resume();
      this.isPaused = false;
      this.updateTTSControlsUI('speaking');
    }
  },

  cancelSpeech() {
    if (this.synth) {
      this.synth.cancel();
    }
    this.isSpeaking = false;
    this.isPaused = false;
    this.updateTTSControlsUI('idle');
  },

  updateTTSControlsUI(state) {
    const playBtn = document.getElementById('btn-tts-play');
    const pauseBtn = document.getElementById('btn-tts-pause');
    const stopBtn = document.getElementById('btn-tts-stop');

    if (playBtn) playBtn.classList.toggle('active', state === 'speaking');
    if (pauseBtn) pauseBtn.style.display = state === 'speaking' ? 'inline-block' : 'none';
    if (stopBtn) stopBtn.style.display = (state === 'speaking' || state === 'paused') ? 'inline-block' : 'none';
  },

  readCurrentPageContext() {
    // Read the primary heading and content of the page
    const heading = document.querySelector('h1')?.textContent || '';
    const desc = document.getElementById('description')?.value || '';
    const alert = document.getElementById('global-alert')?.textContent || '';
    const reportDetail = document.getElementById('report-detail')?.textContent || '';

    const textToRead = [heading, alert, desc, reportDetail].filter(Boolean).join('. ');
    if (textToRead) {
      this.speak(textToRead);
    } else {
      this.speak(window.t('hero_title', 'Smart Civic AI Platform'));
    }
  },

  /* -------------------------------------------------------------
   * 4. Accessibility Modal / Dropdown Menu
   * ----------------------------------------------------------- */
  renderAccessibilityMenu() {
    const container = document.getElementById('a11y-menu-container');
    if (!container) return;

    container.innerHTML = `
      <div class="dropdown" id="a11y-dropdown">
        <button class="btn btn-sm btn-light border dropdown-toggle d-flex align-items-center gap-1 px-2 py-1 shadow-sm"
                type="button" data-bs-toggle="dropdown" aria-expanded="false"
                aria-label="${window.t('accessibility_title', 'Accessibility & Voice Settings')}">
          <i class="bi bi-universal-access-circle text-primary"></i>
          <span class="small fw-semibold d-none d-md-inline" data-i18n="accessibility_menu_btn">Accessibility ⚙</span>
        </button>
        <div class="dropdown-menu dropdown-menu-end shadow border-0 p-3" style="min-width: 280px; z-index: 1060;">
          <h3 class="h6 mb-3 fw-bold d-flex align-items-center gap-2 border-bottom pb-2">
            <i class="bi bi-gear-wide-connected text-primary"></i>
            <span data-i18n="accessibility_title">Accessibility & Voice</span>
          </h3>

          <!-- Voice Assistant Switch -->
          <div class="form-check form-switch mb-2">
            <input class="form-check-input" type="checkbox" id="switch-voice-control" 
                   ${this.settings.voiceControl ? 'checked' : ''} 
                   onchange="window.A11Y.toggleVoiceAssistant()">
            <label class="form-check-label small fw-semibold" for="switch-voice-control" data-i18n="a11y_voice_control">Voice Assistant & Commands</label>
          </div>

          <!-- High Contrast -->
          <div class="form-check form-switch mb-2">
            <input class="form-check-input" type="checkbox" id="switch-high-contrast" 
                   ${this.settings.highContrast ? 'checked' : ''} 
                   onchange="window.A11Y.saveSetting('highContrast', this.checked)">
            <label class="form-check-label small fw-semibold" for="switch-high-contrast" data-i18n="a11y_high_contrast">High Contrast Mode</label>
          </div>

          <!-- Large Text -->
          <div class="form-check form-switch mb-2">
            <input class="form-check-input" type="checkbox" id="switch-large-text" 
                   ${this.settings.largeText ? 'checked' : ''} 
                   onchange="window.A11Y.saveSetting('largeText', this.checked)">
            <label class="form-check-label small fw-semibold" for="switch-large-text" data-i18n="a11y_large_text">Large Text (+25%)</label>
          </div>

          <!-- Reduced Animation -->
          <div class="form-check form-switch mb-2">
            <input class="form-check-input" type="checkbox" id="switch-reduce-motion" 
                   ${this.settings.reduceMotion ? 'checked' : ''} 
                   onchange="window.A11Y.saveSetting('reduceMotion', this.checked)">
            <label class="form-check-label small fw-semibold" for="switch-reduce-motion" data-i18n="a11y_reduce_motion">Reduce Animations</label>
          </div>

          <!-- Keyboard Focus Mode -->
          <div class="form-check form-switch mb-3">
            <input class="form-check-input" type="checkbox" id="switch-keyboard-focus" 
                   ${this.settings.keyboardFocus ? 'checked' : ''} 
                   onchange="window.A11Y.saveSetting('keyboardFocus', this.checked)">
            <label class="form-check-label small fw-semibold" for="switch-keyboard-focus" data-i18n="a11y_keyboard_focus">Keyboard Focus Highlight</label>
          </div>

          <!-- Quick Read Aloud Controls -->
          <div class="border-top pt-2 mt-2">
            <div class="small fw-bold text-muted mb-2" data-i18n="a11y_read_aloud">Text-to-Speech (Read Aloud)</div>
            <div class="d-flex gap-2">
              <button class="btn btn-sm btn-outline-primary flex-fill" id="btn-tts-play" onclick="window.A11Y.readCurrentPageContext()">
                <i class="bi bi-volume-up-fill me-1"></i><span data-i18n="read_aloud_btn">Read Page</span>
              </button>
              <button class="btn btn-sm btn-outline-secondary" id="btn-tts-pause" style="display:none;" onclick="window.A11Y.pauseSpeech()">
                <i class="bi bi-pause-fill"></i>
              </button>
              <button class="btn btn-sm btn-outline-danger" id="btn-tts-stop" style="display:none;" onclick="window.A11Y.cancelSpeech()">
                <i class="bi bi-stop-fill"></i>
              </button>
            </div>
          </div>
        </div>
      </div>
    `;
  }
};

window.A11Y = A11Y;

document.addEventListener('DOMContentLoaded', () => {
  A11Y.init();
});
