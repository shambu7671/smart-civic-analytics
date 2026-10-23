let reportMap, reportMarker, categories = [];

const CATEGORY_I18N_MAP = {
  "Pothole": "cat_pothole",
  "Road Damage": "cat_road_damage",
  "Road Crack": "cat_road_crack",
  "Garbage Accumulation": "cat_garbage",
  "Broken Streetlight": "cat_streetlight",
  "Waterlogging": "cat_waterlogging",
  "Damaged Footpath": "cat_footpath",
  "Drainage Problem": "cat_drainage",
  "Other / Manual Review": "cat_manual_review"
};

function getTranslatedCategoryName(name) {
  const key = CATEGORY_I18N_MAP[name];
  return key && window.t ? window.t(key, name) : name;
}

function renderCategories() {
  const sel = document.getElementById('category_id');
  if (!sel || !categories.length) return;
  const currentVal = sel.value;
  sel.innerHTML = categories.map(c => `
    <option value="${c.id}" ${String(c.id) === String(currentVal) ? 'selected' : ''}>
      ${esc(getTranslatedCategoryName(c.name))}
    </option>
  `).join('');
}

function setLocation(lat, lon) {
  const latEl = document.getElementById('latitude');
  const lonEl = document.getElementById('longitude');
  if (latEl) latEl.value = Number(lat).toFixed(6);
  if (lonEl) lonEl.value = Number(lon).toFixed(6);

  if (reportMarker) {
    reportMarker.setLatLng([lat, lon]);
  } else if (reportMap) {
    reportMarker = L.marker([lat, lon], { draggable: true }).addTo(reportMap);
    reportMarker.on('dragend', () => {
      const p = reportMarker.getLatLng();
      setLocation(p.lat, p.lng);
    });
  }
  if (reportMap) reportMap.setView([lat, lon], 16);
}

async function loadCategories() {
  try {
    const r = await api('/api/categories');
    categories = r.data || [];
    renderCategories();
  } catch (err) {
    console.error('Failed to load categories:', err);
  }
}

// Client-side quick script/language detection
function detectInputLanguage(text) {
  if (!text || !text.trim()) return 'en';
  if (text.includes('\u0933')) return 'mr'; // Marathi specific letter
  const devanagariCount = (text.match(/[\u0900-\u097F]/g) || []).length;
  const latinCount = (text.match(/[A-Za-z]/g) || []).length;

  if (devanagariCount > latinCount) {
    const mrWords = ['आहे', 'आहेत', 'नाही', 'खड्डा', 'रस्ता', 'पाणी', 'कचरा', 'पडला', 'माझ्या', 'झाला'];
    const hiWords = ['है', 'हैं', 'नहीं', 'गड्ढा', 'सड़क', 'पानी', 'कचरा', 'हुआ', 'मेरा', 'गया'];
    let mrScore = 0, hiScore = 0;
    mrWords.forEach(w => { if (text.includes(w)) mrScore++; });
    hiWords.forEach(w => { if (text.includes(w)) hiScore++; });
    if (mrScore > hiScore) return 'mr';
    if (hiScore > mrScore) return 'hi';
    return window.I18N?.currentLang === 'mr' ? 'mr' : 'hi';
  }
  return 'en';
}

function updateDetectedLanguageBadge(text) {
  const pillText = document.getElementById('detected-lang-text');
  if (!pillText) return;

  const detected = detectInputLanguage(text);
  const langMap = {
    'en': 'English',
    'hi': 'Hindi (हिन्दी)',
    'mr': 'Marathi (मराठी)'
  };
  const label = langMap[detected] || detected.toUpperCase();
  pillText.textContent = `${window.t('ai_detected_language', 'Detected Language')}: ${label}`;
}

document.addEventListener('DOMContentLoaded', async () => {
  // Leaflet Map Init
  const mapContainer = document.getElementById('report-map');
  if (mapContainer) {
    reportMap = L.map('report-map').setView([18.5204, 73.8567], 13);
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
      attribution: '© OpenStreetMap contributors'
    }).addTo(reportMap);
    reportMap.on('click', e => setLocation(e.latlng.lat, e.latlng.lng));
  }

  await loadCategories();

  // Listen for language changes to update categories
  window.addEventListener('languageChanged', () => {
    renderCategories();
    const voiceTag = document.getElementById('voice-lang-tag');
    if (voiceTag && window.I18N) voiceTag.textContent = window.I18N.getSpeechLocale();
  });

  // Geolocation buttons
  const getLocBtn = document.getElementById('get-location');
  if (getLocBtn) {
    getLocBtn.onclick = () => navigator.geolocation?.getCurrentPosition(
      p => setLocation(p.coords.latitude, p.coords.longitude),
      e => showAlert(`${window.t('alert_location_unavailable', 'Location unavailable')}: ${e.message}`, 'warning'),
      { enableHighAccuracy: true, timeout: 10000 }
    );
  }

  const mapPickBtn = document.getElementById('map-pick');
  if (mapPickBtn) {
    mapPickBtn.onclick = () => showAlert(window.t('map_help_text', 'Click anywhere on the map to choose a location.'), 'info');
  }

  // Image preview
  const imageInput = document.getElementById('image');
  if (imageInput) {
    imageInput.onchange = e => {
      const f = e.target.files[0];
      if (!f) return;
      const img = document.getElementById('image-preview');
      if (img) {
        img.src = URL.createObjectURL(f);
        img.classList.remove('d-none');
      }
    };
  }

  // Description input listener for live language detection
  const descInput = document.getElementById('description');
  if (descInput) {
    descInput.addEventListener('input', () => {
      updateDetectedLanguageBadge(descInput.value);
    });
  }

  // Clear description button
  const clearBtn = document.getElementById('btn-clear-desc');
  if (clearBtn && descInput) {
    clearBtn.onclick = () => {
      descInput.value = '';
      updateDetectedLanguageBadge('');
      descInput.focus();
    };
  }

  // Voice Complaint Recording Button (Requirement 4)
  const voiceBtn = document.getElementById('btn-voice-record');
  if (voiceBtn && descInput) {
    voiceBtn.onclick = () => {
      if (window.A11Y?.isRecording) {
        window.A11Y.stopVoiceComplaint();
      } else {
        window.A11Y.startVoiceComplaint(descInput, () => {
          updateDetectedLanguageBadge(descInput.value);
        });
      }
    };
  }

  // Report Submission Handler
  const reportForm = document.getElementById('report-form');
  if (reportForm) {
    reportForm.onsubmit = async (e) => {
      e.preventDefault();
      const submitBtn = document.getElementById('btn-submit-report');
      if (submitBtn) submitBtn.disabled = true;

      const currentLang = window.I18N ? window.I18N.currentLang : 'en';
      const form = new FormData();
      form.append('category_id', document.getElementById('category_id').value);
      form.append('description', document.getElementById('description').value.trim());
      form.append('severity', document.getElementById('severity').value);
      form.append('latitude', document.getElementById('latitude').value);
      form.append('longitude', document.getElementById('longitude').value);
      form.append('selected_language', currentLang);

      const fileField = document.getElementById('image');
      if (fileField && fileField.files[0]) {
        form.append('image', fileField.files[0]);
      }

      if (!form.get('image') || !form.get('description') || !form.get('latitude')) {
        if (submitBtn) submitBtn.disabled = false;
        return showAlert(window.t('alert_fill_required', 'Image, description and GPS location are required.'), 'warning');
      }

      try {
        showAlert(window.t('submitting_report', 'Analyzing complaint & uploading evidence...'), 'info');
        const r = await api('/api/reports', { method: 'POST', body: form });
        showAlert(window.t('alert_submit_success', 'Report submitted successfully. Redirecting to analysis...'), 'success');
        setTimeout(() => location.href = `/citizen/reports/${r.data.id}`, 600);
      } catch (err) {
        showAlert(err.message, 'danger');
        if (submitBtn) submitBtn.disabled = false;
      }
    };
  }
});
