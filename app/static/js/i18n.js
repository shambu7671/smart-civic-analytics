/**
 * SmartCivic AI — Multilingual Internationalization (i18n) Engine
 * Supports en, hi, mr with expandable Indian language architecture.
 */

const I18N = {
  currentLang: localStorage.getItem('smartcivic_lang') || 'en',
  localesCache: {},
  languages: [
    { code: 'en', name: 'English', native: 'English', speechLocale: 'en-IN' },
    { code: 'hi', name: 'Hindi', native: 'हिन्दी', speechLocale: 'hi-IN' },
    { code: 'mr', name: 'Marathi', native: 'मराठी', speechLocale: 'mr-IN' },
    { code: 'gu', name: 'Gujarati', native: 'ગુજરાતી', speechLocale: 'gu-IN' },
    { code: 'bn', name: 'Bengali', native: 'বাংলা', speechLocale: 'bn-IN' },
    { code: 'ta', name: 'Tamil', native: 'தமிழ்', speechLocale: 'ta-IN' },
    { code: 'te', name: 'Telugu', native: 'తెలుగు', speechLocale: 'te-IN' },
    { code: 'kn', name: 'Kannada', native: 'ಕನ್ನಡ', speechLocale: 'kn-IN' },
    { code: 'ml', name: 'Malayalam', native: 'മലയാളം', speechLocale: 'ml-IN' },
    { code: 'pa', name: 'Punjabi', native: 'ਪੰਜਾਬੀ', speechLocale: 'pa-IN' }
  ],

  async init() {
    await this.loadLocale(this.currentLang);
    this.translatePage();
    this.renderLanguageSelector();
    document.documentElement.lang = this.currentLang;
  },

  async loadLocale(lang) {
    if (this.localesCache[lang]) return this.localesCache[lang];
    try {
      const res = await fetch(`/static/locales/${lang}.json`);
      if (!res.ok) {
        // Fallback to English if file not yet translated
        if (lang !== 'en') return await this.loadLocale('en');
        throw new Error('Locale load error');
      }
      const data = await res.json();
      this.localesCache[lang] = data;
      return data;
    } catch (err) {
      console.warn(`[i18n] Failed to load locale for ${lang}, falling back to English.`, err);
      if (lang !== 'en') return await this.loadLocale('en');
      return {};
    }
  },

  t(key, fallback = '') {
    const dict = this.localesCache[this.currentLang] || this.localesCache['en'] || {};
    return dict[key] || fallback || key;
  },

  getSpeechLocale() {
    const langObj = this.languages.find(l => l.code === this.currentLang);
    return langObj ? langObj.speechLocale : 'en-IN';
  },

  async setLanguage(lang) {
    if (!lang) return;
    this.currentLang = lang;
    localStorage.setItem('smartcivic_lang', lang);
    document.documentElement.lang = lang;
    await this.loadLocale(lang);
    this.translatePage();
    this.renderLanguageSelector();

    // Trigger global event so reactive views (report-form, map, charts) refresh
    window.dispatchEvent(new CustomEvent('languageChanged', {
      detail: { lang, locale: this.getSpeechLocale() }
    }));

    // Announce to screen readers
    const langName = this.languages.find(l => l.code === lang)?.native || lang;
    if (window.a11yAnnounce) {
      window.a11yAnnounce(this.t('language_changed', `Language switched to ${langName}`));
    }
  },

  translatePage() {
    // 1. Text Content
    document.querySelectorAll('[data-i18n]').forEach(el => {
      const key = el.getAttribute('data-i18n');
      const val = this.t(key);
      if (val) {
        // Preserve nested icon tags if any
        const icon = el.querySelector('i.bi');
        if (icon) {
          el.innerHTML = '';
          el.appendChild(icon);
          el.appendChild(document.createTextNode(' ' + val));
        } else {
          el.textContent = val;
        }
      }
    });

    // 2. Placeholders
    document.querySelectorAll('[data-i18n-placeholder]').forEach(el => {
      const key = el.getAttribute('data-i18n-placeholder');
      const val = this.t(key);
      if (val) el.placeholder = val;
    });

    // 3. Titles / Tooltips
    document.querySelectorAll('[data-i18n-title]').forEach(el => {
      const key = el.getAttribute('data-i18n-title');
      const val = this.t(key);
      if (val) el.title = val;
    });

    // 4. ARIA Labels
    document.querySelectorAll('[data-i18n-aria]').forEach(el => {
      const key = el.getAttribute('data-i18n-aria');
      const val = this.t(key);
      if (val) el.setAttribute('aria-label', val);
    });
  },

  renderLanguageSelector() {
    const container = document.getElementById('lang-selector-container');
    if (!container) return;

    const current = this.languages.find(l => l.code === this.currentLang) || this.languages[0];
    
    container.innerHTML = `
      <div class="dropdown" id="lang-dropdown">
        <button class="btn btn-sm btn-light border dropdown-toggle d-flex align-items-center gap-1 px-2 py-1 shadow-sm" 
                type="button" data-bs-toggle="dropdown" aria-expanded="false" 
                aria-label="${this.t('language_selector_label', 'Language')}: ${current.native}">
          <i class="bi bi-translate text-primary"></i>
          <span class="fw-semibold small">${current.native}</span>
        </button>
        <ul class="dropdown-menu dropdown-menu-end shadow-sm border-0 py-1" style="min-width: 170px;">
          ${this.languages.map(l => `
            <li>
              <button class="dropdown-item d-flex align-items-center justify-content-between py-2 ${l.code === this.currentLang ? 'active fw-bold' : ''}" 
                      type="button" onclick="window.I18N.setLanguage('${l.code}')">
                <span>${l.native}</span>
                <span class="small text-muted ms-2">${l.name}</span>
              </button>
            </li>
          `).join('')}
        </ul>
      </div>
    `;
  }
};

window.I18N = I18N;
window.t = I18N.t.bind(I18N);

document.addEventListener('DOMContentLoaded', () => {
  I18N.init();
});
