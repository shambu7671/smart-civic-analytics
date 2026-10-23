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

  // Re-evaluate geotag badge whenever the pin moves
  const fileInput = document.getElementById('image');
  if (fileInput && fileInput.files[0]) {
    readExifAndUpdateBadge(fileInput.files[0]);
  }
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

// ── Client-side language detection ──────────────────────────────────────────

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

// ── Client-side EXIF GPS reader ──────────────────────────────────────────────
// Reads GPS EXIF from the selected image file in the browser using
// DataView / ArrayBuffer — no external library required.

function readExifGPS(file) {
  return new Promise((resolve) => {
    const reader = new FileReader();
    reader.onload = function (e) {
      try {
        const gps = parseExifGPS(e.target.result);
        resolve(gps);
      } catch (_) {
        resolve(null);
      }
    };
    reader.onerror = () => resolve(null);
    reader.readAsArrayBuffer(file);
  });
}

function parseExifGPS(buffer) {
  const view = new DataView(buffer);
  // Check JPEG SOI marker
  if (view.getUint16(0) !== 0xFFD8) return null;

  let offset = 2;
  while (offset < view.byteLength - 2) {
    const marker = view.getUint16(offset);
    offset += 2;
    if (marker === 0xFFE1) { // APP1 / EXIF
      const segLen = view.getUint16(offset);
      const exifHeader = String.fromCharCode(
        view.getUint8(offset + 2),
        view.getUint8(offset + 3),
        view.getUint8(offset + 4),
        view.getUint8(offset + 5)
      );
      if (exifHeader === 'Exif') {
        return parseExifBlock(buffer, offset + 8, segLen - 8);
      }
      offset += segLen;
    } else if ((marker & 0xFF00) === 0xFF00) {
      offset += view.getUint16(offset);
    } else {
      break;
    }
  }
  return null;
}

function parseExifBlock(buffer, exifStart, len) {
  const view = new DataView(buffer, exifStart, len);
  // Determine byte order
  const byteOrder = view.getUint16(0);
  const littleEndian = (byteOrder === 0x4949); // II = little endian, MM = big endian

  const ifdOffset = view.getUint32(4, littleEndian);
  const ifdCount = view.getUint16(ifdOffset, littleEndian);

  let gpsIfdOffset = null;
  for (let i = 0; i < ifdCount; i++) {
    const entryOffset = ifdOffset + 2 + i * 12;
    const tag = view.getUint16(entryOffset, littleEndian);
    if (tag === 0x8825) { // GPSInfoIFDPointer
      gpsIfdOffset = view.getUint32(entryOffset + 8, littleEndian);
      break;
    }
  }
  if (gpsIfdOffset === null) return null;

  const gpsCount = view.getUint16(gpsIfdOffset, littleEndian);
  const gpsTags = {};
  for (let i = 0; i < gpsCount; i++) {
    const entryOffset = gpsIfdOffset + 2 + i * 12;
    const tag = view.getUint16(entryOffset, littleEndian);
    const type = view.getUint16(entryOffset + 2, littleEndian);
    const count = view.getUint32(entryOffset + 4, littleEndian);
    const valOffset = entryOffset + 8;

    if (type === 5) { // RATIONAL (used for DMS values)
      const vals = [];
      let dataOffset;
      if (count * 8 > 4) {
        dataOffset = view.getUint32(valOffset, littleEndian);
      } else {
        dataOffset = valOffset;
      }
      for (let j = 0; j < count; j++) {
        const num = view.getUint32(dataOffset + j * 8, littleEndian);
        const den = view.getUint32(dataOffset + j * 8 + 4, littleEndian);
        vals.push(den !== 0 ? num / den : 0);
      }
      gpsTags[tag] = vals;
    } else if (type === 2) { // ASCII
      const dataOffset = count > 4 ? view.getUint32(valOffset, littleEndian) : valOffset;
      let str = '';
      for (let j = 0; j < count - 1; j++) {
        str += String.fromCharCode(view.getUint8(dataOffset + j));
      }
      gpsTags[tag] = str;
    }
  }

  // GPS tag IDs: 1=LatRef, 2=Lat, 3=LonRef, 4=Lon
  const latDMS = gpsTags[2];
  const latRef = gpsTags[1];
  const lonDMS = gpsTags[4];
  const lonRef = gpsTags[3];

  if (!latDMS || !lonDMS) return null;

  const toDecimal = (dms, ref) => {
    const deg = dms[0] + dms[1] / 60 + dms[2] / 3600;
    return (ref === 'S' || ref === 'W') ? -deg : deg;
  };

  return {
    lat: toDecimal(latDMS, latRef),
    lon: toDecimal(lonDMS, lonRef)
  };
}

function haversineMetres(lat1, lon1, lat2, lon2) {
  const R = 6371000;
  const phi1 = lat1 * Math.PI / 180;
  const phi2 = lat2 * Math.PI / 180;
  const dPhi = (lat2 - lat1) * Math.PI / 180;
  const dLam = (lon2 - lon1) * Math.PI / 180;
  const a = Math.sin(dPhi / 2) ** 2 + Math.cos(phi1) * Math.cos(phi2) * Math.sin(dLam / 2) ** 2;
  return 2 * R * Math.asin(Math.sqrt(a));
}

// ── Geotag badge UI ──────────────────────────────────────────────────────────

async function readExifAndUpdateBadge(file) {
  const badge = document.getElementById('geotag-status-badge');
  if (!badge) return;

  // Only attempt EXIF parsing for JPEG files (EXIF is rarely in PNG)
  if (!file.type.includes('jpeg') && !file.type.includes('jpg')) {
    badge.className = 'alert alert-secondary py-2 px-3 small d-flex align-items-center gap-2';
    badge.innerHTML = '<i class="bi bi-image"></i><span><strong>No EXIF GPS:</strong> PNG images do not carry GPS metadata. Coordinates will be accepted from the map pin.</span>';
    return;
  }

  badge.className = 'alert alert-light py-2 px-3 small d-flex align-items-center gap-2';
  badge.innerHTML = '<div class="spinner-border spinner-border-sm text-secondary" role="status"></div><span>Reading photo EXIF GPS…</span>';

  const gps = await readExifGPS(file);

  const latVal = document.getElementById('latitude')?.value;
  const lonVal = document.getElementById('longitude')?.value;
  const submittedLat = latVal ? parseFloat(latVal) : null;
  const submittedLon = lonVal ? parseFloat(lonVal) : null;

  if (!gps) {
    badge.className = 'alert alert-secondary py-2 px-3 small d-flex align-items-center gap-2';
    badge.innerHTML = `
      <i class="bi bi-geo-alt text-muted"></i>
      <span>
        <strong>No EXIF GPS in this photo.</strong>
        Coordinates will be accepted from the map pin below.
        For stronger verification, upload a photo taken with camera GPS enabled.
      </span>`;
    return;
  }

  // EXIF GPS found
  const latStr = gps.lat.toFixed(5);
  const lonStr = gps.lon.toFixed(5);

  if (submittedLat === null) {
    badge.className = 'alert alert-info py-2 px-3 small d-flex align-items-center gap-2';
    badge.innerHTML = `
      <i class="bi bi-geo-fill text-info"></i>
      <span>
        <strong>Photo has EXIF GPS:</strong> ${latStr}, ${lonStr}.<br>
        Please select a location on the map or click <em>Get My Device Location</em> so we can verify it matches the photo.
      </span>`;
    return;
  }

  const dist = haversineMetres(gps.lat, gps.lon, submittedLat, submittedLon);
  const MAX_DIST = 200; // mirrors server default GEOTAG_MAX_DISTANCE_METERS

  if (dist <= MAX_DIST) {
    badge.className = 'alert alert-success py-2 px-3 small d-flex align-items-center gap-2';
    badge.innerHTML = `
      <i class="bi bi-check-circle-fill text-success fs-5"></i>
      <span>
        <strong>Photo GPS Verified ✓</strong> — EXIF coordinates (${latStr}, ${lonStr}) match
        your selected map pin within <strong>${dist.toFixed(0)} m</strong>.
      </span>`;
  } else {
    badge.className = 'alert alert-warning py-2 px-3 small d-flex align-items-center gap-2';
    badge.innerHTML = `
      <i class="bi bi-exclamation-triangle-fill text-warning fs-5"></i>
      <span>
        <strong>Location Mismatch ⚠</strong> — Photo EXIF GPS (${latStr}, ${lonStr}) is
        <strong>${dist.toFixed(0)} m</strong> away from your map pin. 
        The server will flag this for manual review. For best results, move the pin to match the photo location
        or upload a photo taken at the pinned location.
      </span>`;
  }
}

// ── DOMContentLoaded ─────────────────────────────────────────────────────────

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

  // Image preview + client-side EXIF geotag check
  const imageInput = document.getElementById('image');
  if (imageInput) {
    imageInput.onchange = async (e) => {
      const f = e.target.files[0];
      if (!f) return;
      const img = document.getElementById('image-preview');
      if (img) {
        img.src = URL.createObjectURL(f);
        img.classList.remove('d-none');
      }
      // Trigger EXIF-based geotag preview immediately on file selection
      await readExifAndUpdateBadge(f);
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

  // Voice Complaint Recording Button
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
        // Show geotag result if server returned a mismatch warning
        const gt = r.data?.geotag;
        if (gt && gt.status === 'MISMATCH') {
          showAlert(
            `Report submitted (Geotag warning: ${gt.message || 'location mismatch'})`,
            'warning'
          );
        } else {
          showAlert(window.t('alert_submit_success', 'Report submitted successfully. Redirecting to analysis...'), 'success');
        }
        setTimeout(() => location.href = `/citizen/reports/${r.data.id}`, 800);
      } catch (err) {
        showAlert(err.message, 'danger');
        if (submitBtn) submitBtn.disabled = false;
      }
    };
  }
});
