import re
from typing import Tuple, Dict, Any

# ISO 639-1 Language Definitions
LANGUAGES = {
    "en": {"name": "English", "locale": "en-IN", "label": "English"},
    "hi": {"name": "Hindi", "locale": "hi-IN", "label": "हिन्दी"},
    "mr": {"name": "Marathi", "locale": "mr-IN", "label": "मराठी"},
    "gu": {"name": "Gujarati", "locale": "gu-IN", "label": "ગુજરાતી"},
    "bn": {"name": "Bengali", "locale": "bn-IN", "label": "বাংলা"},
    "ta": {"name": "Tamil", "locale": "ta-IN", "label": "தமிழ்"},
    "te": {"name": "Telugu", "locale": "te-IN", "label": "తెలుగు"},
    "kn": {"name": "Kannada", "locale": "kn-IN", "label": "ಕನ್ನಡ"},
    "ml": {"name": "Malayalam", "locale": "ml-IN", "label": "മലയാളം"},
    "pa": {"name": "Punjabi", "locale": "pa-IN", "label": "ਪੰਜਾਬੀ"}
}

# Distinguishing markers for Devanagari (Marathi vs Hindi)
MARATHI_MARKERS = {
    'आहे', 'आहेत', 'नाही', 'नाहीत', 'खड्डा', 'खड्डे', 'रस्ता', 'रस्त्यावर', 'पाणी',
    'कचरा', 'घराजवळ', 'झाले', 'झाला', 'झाली', 'पडला', 'पडली', 'येथे', 'माझ्या', 'आमच्या',
    'करून', 'द्यावे', 'लवकर', 'दुरुस्ती', 'नळ', 'गटार', 'दिवा', 'पथदिवा', 'विद्युत',
    'वाहतूक', 'तक्रार', 'चौक', 'अडचण', 'खराब', 'तातडीने', 'नागरिक', 'विभाग', 'स्थानिक'
}

HINDI_MARKERS = {
    'है', 'हैं', 'नहीं', 'गड्ढा', 'गड्ढे', 'सड़क', 'रास्ता', 'पानी', 'कचरा', 'घर',
    'के पास', 'हुआ', 'हुई', 'हुए', 'गिरा', 'यहाँ', 'मेरा', 'हमारा', 'करें', 'दीजिए',
    'जल्दी', 'मरम्मत', 'नाली', 'लाइट', 'स्ट्रीट लाइट', 'बिजली', 'यातायात', 'शिकायत',
    'समस्या', 'चौराहा', 'तुरंत', 'कष्ट', 'खराब'
}

# Domain-specific civic phrase dictionary for English translation/normalization
CIVIC_DICTIONARY = [
    # Marathi phrases to English
    (r'(?i)माझ्या\s+घराजवळ', 'near my residence'),
    (r'(?i)घराजवळ', 'near residence'),
    (r'(?i)रस्त्यावर\s+मोठा\s+खड्डा', 'large pothole on the road'),
    (r'(?i)रस्त्यावर\s+खड्डा', 'pothole on the road'),
    (r'(?i)मोठा\s+खड्डा\s+आहे', 'there is a large pothole'),
    (r'(?i)मोठा\s+खड्डा', 'large pothole'),
    (r'(?i)खड्डे\s+पडले\s+आहेत', 'potholes formed on roadway'),
    (r'(?i)खड्डा\s+पडला\s+आहे', 'pothole formed on road'),
    (r'(?i)खड्डा|खड्डे', 'pothole'),
    (r'(?i)रस्ता\s+खराब\s+झाला\s+आहे', 'road surface is badly damaged'),
    (r'(?i)रस्ता\s+खराब', 'road damage'),
    (r'(?i)रस्त्यावर\s+तडे', 'cracks on road surface'),
    (r'(?i)रस्त्यावर|रस्ता', 'on the road'),
    (r'(?i)कचरा\s+साचला\s+आहे', 'garbage accumulation'),
    (r'(?i)कचरा\s+पडला\s+आहे', 'garbage dumped'),
    (r'(?i)कचरा', 'garbage'),
    (r'(?i)पाणी\s+तुंबले\s+आहे|पाणी\s+साचले\s+आहे', 'waterlogging on road'),
    (r'(?i)पाणी\s+गळती', 'water pipe leakage'),
    (r'(?i)पाणी', 'water'),
    (r'(?i)गटार\s+तुंबले\s+आहे|गटाराचे\s+पाणी', 'overflowing sewage drain'),
    (r'(?i)गटार', 'drainage'),
    (r'(?i)पथदिवा\s+बंद\s+आहे|स्ट्रीट\s+लाइट\s+बंद', 'broken streetlight not working'),
    (r'(?i)पथदिवा|दिवा', 'streetlight'),
    (r'(?i)वाहतूक\s+अडकली\s+आहे|वाहतूक\s+कोंडी', 'traffic congestion'),
    (r'(?i)अपघात\s+होऊ\s+शकतो', 'hazard risk of accidents'),
    (r'(?i)दुरुस्ती\s+करावी|दुरुस्त\s+करा', 'repair urgently required'),
    (r'(?i)लवकर|तातडीने', 'urgently'),

    # Hindi phrases to English
    (r'(?i)मेरे\s+घर\s+के\s+पास', 'near my residence'),
    (r'(?i)घर\s+के\s+पास', 'near residence'),
    (r'(?i)सड़क\s+पर\s+बड़ा\s+गड्ढा\s+है', 'large pothole on the road'),
    (r'(?i)सड़क\s+पर\s+गड्ढा', 'pothole on the road'),
    (r'(?i)बड़ा\s+गड्ढा', 'large pothole'),
    (r'(?i)गड्ढा\s+है|गड्ढे\s+हैं', 'potholes exist'),
    (r'(?i)गड्ढा|गड्ढे', 'pothole'),
    (r'(?i)सड़क\s+खराब\s+है', 'road surface is damaged'),
    (r'(?i)सड़क\s+टूट\s+गई\s+है', 'road broken and damaged'),
    (r'(?i)सड़क\s+पर\s+दरारें', 'cracks on road surface'),
    (r'(?i)सड़क|रास्ता', 'road'),
    (r'(?i)कचरा\s+पड़ा\s+है|कचरा\s+जमा\s+है', 'garbage accumulation'),
    (r'(?i)कचरा', 'garbage'),
    (r'(?i)पानी\s+भरा\s+हुआ\s+है|पानी\s+भर\s+गया\s+है', 'waterlogging on road'),
    (r'(?i)पानी\s+लीक\s+हो\s+रहा\s+है', 'water pipe leakage'),
    (r'(?i)पानी', 'water'),
    (r'(?i)नाली\s+चोक\s+है|नाली\s+का\s+पानी', 'blocked drainage overflow'),
    (r'(?i)नाली', 'drainage'),
    (r'(?i)स्ट्रीट\s+लाइट\s+खराब\s+है|लाइट\s+बंद\s+है', 'broken streetlight not functioning'),
    (r'(?i)स्ट्रीट\s+लाइट|बिजली\s+का\s+खंभा', 'streetlight pole'),
    (r'(?i)दुर्घटना\s+हो\s+सकती\s+है', 'accident hazard'),
    (r'(?i)जल्दी\s+मरम्मत\s+करें|कृपया\s+ठीक\s+करें', 'please repair urgently'),
    (r'(?i)जल्दी|तुरंत', 'immediately')
]

DEPARTMENT_MAP = {
    "Pothole": {
        "en": "Road Infrastructure & Maintenance Dept",
        "hi": "सड़क अवसंरचना एवं अनुरक्षण विभाग",
        "mr": "रस्ता पायाभूत सुविधा व दुरुस्ती विभाग"
    },
    "Road Damage": {
        "en": "Public Works Department (Civil Roads Division)",
        "hi": "लोक निर्माण विभाग (सड़क प्रभाग)",
        "mr": "सार्वजनिक बांधकाम विभाग (रस्ते विभाग)"
    },
    "Road Crack": {
        "en": "Highway & Pavement Engineering Wing",
        "hi": "राजमार्ग एवं फुटपाथ इंजीनियरिंग शाखा",
        "mr": "महामार्ग व डांबरीकरण अभियांत्रिकी शाखा"
    },
    "Garbage Accumulation": {
        "en": "Solid Waste Management & Sanitation Dept",
        "hi": "ठोस अपशिष्ट प्रबंधन एवं स्वच्छता विभाग",
        "mr": "घनकचरा व्यवस्थापन व स्वच्छता विभाग"
    },
    "Broken Streetlight": {
        "en": "Municipal Electrical Maintenance Division",
        "hi": "नगर निगम विद्युत अनुरक्षण प्रभाग",
        "mr": "महानगरपालिका विद्युत देखभाल विभाग"
    },
    "Waterlogging": {
        "en": "Stormwater Drainage & Flood Response Team",
        "hi": "वर्षा जल निकासी एवं बाढ़ निवारण दल",
        "mr": "पावसाळी गटार व जलउपसा नियंत्रण पथक"
    },
    "Damaged Footpath": {
        "en": "Pedestrian Infrastructure & Walkways Dept",
        "hi": "पैदल यात्री अवसंरचना विभाग",
        "mr": "पादचारी सुविधा व पदपथ विभाग"
    },
    "Drainage Problem": {
        "en": "Underground Drainage & Sewerage Board",
        "hi": "भूमिगत जल निकासी एवं सीवरेज बोर्ड",
        "mr": "भूमिगत गटारे व मलनिस्सारण मंडळ"
    },
    "Other / Manual Review": {
        "en": "Municipal Grievance Redressal & Field Cell",
        "hi": "नागरिक शिकायत निवारण एवं फील्ड सेल",
        "mr": "नागरी तक्रार निवारण व क्षेत्रीय पथक"
    }
}

SUGGESTED_ACTIONS = {
    "Pothole": {
        "en": "Deploy rapid response road repair crew with cold asphalt mix. Place cautionary cones and seal depression.",
        "hi": "कोल्ड डामर मिश्रण के साथ त्वरित प्रतिक्रिया सड़क मरम्मत दल भेजें। चेतावनी शंकु लगाएं और गड्ढा भरें।",
        "mr": "तात्काळ डांबर मिश्रणासह रस्ता दुरुस्ती पथक पाठवावे. धोक्याचे फलक लावून खड्डा तात्काळ बुजवण्यात यावा."
    },
    "Road Damage": {
        "en": "Conduct structural road inspection, mill uneven sub-base, and resurface affected section within 48 hours.",
        "hi": "संरचनात्मक सड़क निरीक्षण करें, असमान सतह को समतल करें और 48 घंटे के भीतर पुन: डामरीकरण करें।",
        "mr": "रस्त्याची तांत्रिक पाहणी करून खराब झालेला भाग समतल करावा आणि ४८ तासांच्या आत पुनर्पृष्टीकरण करावे."
    },
    "Road Crack": {
        "en": "Clean joints and apply bitumen polymer crack-sealant to prevent water seepage and foundation breakdown.",
        "hi": "दरारों की सफाई कर बिटुमेन पॉलीमर सीलेंट लगाएं ताकि पानी के रिसाव और सड़क धंसने से बचाव हो सके।",
        "mr": "तड्यांची स्वच्छता करून बिटुमन पॉलीमर सीलंट भरावे, ज्यामुळे पाण्याचा निचरा रोखून रस्ता खचणे टाळता येईल."
    },
    "Other / Manual Review": {
        "en": "Municipal supervisor inspection scheduled for on-site assessment and department assignment.",
        "hi": "मौके पर मूल्यांकन और संबंधित विभाग को सौंपने के लिए पर्यवेक्षक निरीक्षण निर्धारित किया गया है।",
        "mr": "प्रत्यक्ष पाहणी आणि संबंधित विभागाकडे हस्तांतरित करण्यासाठी पर्यवेक्षक तपासणी नियोजित केली आहे."
    }
}

CATEGORY_TRANSLATIONS = {
    "Pothole": {"en": "Pothole", "hi": "सड़क का गड्ढा", "mr": "रस्त्यावरील खड्डा"},
    "Road Damage": {"en": "Road Damage", "hi": "क्षतिग्रस्त सड़क", "mr": "खराब रस्ता / दुरावस्था"},
    "Road Crack": {"en": "Road Crack", "hi": "सड़क की दरार", "mr": "रस्त्यावरील तडे"},
    "Garbage Accumulation": {"en": "Garbage Accumulation", "hi": "कचरे का ढेर", "mr": "कचरा साचणे"},
    "Broken Streetlight": {"en": "Broken Streetlight", "hi": "खराब स्ट्रीट लाइट", "mr": "बंद पथदिवा"},
    "Waterlogging": {"en": "Waterlogging", "hi": "जलभराव", "mr": "पाणी साचणे / जलजमाव"},
    "Damaged Footpath": {"en": "Damaged Footpath", "hi": "टूटा फुटपाथ", "mr": "खराब पदपथ / फुटपाथ"},
    "Drainage Problem": {"en": "Drainage Problem", "hi": "नाली की समस्या", "mr": "गटाराची समस्या"},
    "Other / Manual Review": {"en": "Other / Manual Review", "hi": "अन्य / मैन्युअल समीक्षा", "mr": "इतर / मानवी तपासणी"}
}

PRIORITY_TRANSLATIONS = {
    "HIGH": {"en": "High", "hi": "उच्च", "mr": "उच्च (तातडीचे)"},
    "MEDIUM": {"en": "Medium", "hi": "मध्यम", "mr": "मध्यम"},
    "LOW": {"en": "Low", "hi": "Low", "mr": "कमी"}
}

STATUS_TRANSLATIONS = {
    "SUBMITTED": {"en": "Submitted", "hi": "दर्ज किया गया", "mr": "नोंदवले गेले"},
    "UNDER_REVIEW": {"en": "Under Review", "hi": "समीक्षाधीन", "mr": "तपासणी सुरू"},
    "REPORTED": {"en": "Reported", "hi": "रिपोर्ट किया गया", "mr": "नोंदवलेले"},
    "VERIFIED": {"en": "Verified", "hi": "सत्यापित", "mr": "सत्यापित"},
    "ASSIGNED": {"en": "Assigned", "hi": "सौंपा गया", "mr": "नियुक्त केले"},
    "IN_PROGRESS": {"en": "In Progress", "hi": "प्रगति पर", "mr": "प्रगतीपथावर"},
    "RESOLVED": {"en": "Resolved", "hi": "निराकृत", "mr": "निवारण झाले"},
    "REJECTED": {"en": "Rejected", "hi": "अस्वीकृत", "mr": "नाकारले"}
}


def detect_language(text: str, fallback: str = "en") -> str:
    """
    Detects language based on script and vocabulary.
    Supports Marathi ('mr'), Hindi ('hi'), and English ('en').
    """
    if not text or not text.strip():
        return fallback

    cleaned = text.strip()

    # Check for character 'ळ' (U+0933) which is uniquely Marathi among Devangari civic inputs
    if '\u0933' in cleaned:
        return 'mr'

    # Check for Devanagari range
    devanagari_chars = len(re.findall(r'[\u0900-\u097F]', cleaned))
    latin_chars = len(re.findall(r'[A-Za-z]', cleaned))

    if devanagari_chars > latin_chars:
        # Check Marathi markers vs Hindi markers
        words = set(re.findall(r'[\u0900-\u097F]+', cleaned))
        mr_matches = len(words.intersection(MARATHI_MARKERS))
        hi_matches = len(words.intersection(HINDI_MARKERS))

        if mr_matches > hi_matches:
            return 'mr'
        elif hi_matches > mr_matches:
            return 'hi'
        else:
            # Fallback heuristic: check verb endings
            if any(w.endswith(('आहे', 'आहेत', 'झाला', 'पडला', 'करावी')) for w in words):
                return 'mr'
            if any(w.endswith(('है', 'हैं', 'गया', 'हुआ', 'करें')) for w in words):
                return 'hi'
            # Default Devanagari fallback
            return 'mr' if fallback == 'mr' else 'hi'

    return 'en'


def translate_to_english(text: str, source_lang: str = None) -> Tuple[str, str]:
    """
    Translates/normalizes civic complaint text to English for AI analysis and PostGIS clustering.
    Returns (normalized_english_text, detected_language).
    """
    if not text:
        return "", "en"

    detected_lang = source_lang or detect_language(text)

    # If already predominantly English, keep it
    if detected_lang == "en" and not re.search(r'[\u0900-\u097F]', text):
        return text.strip(), "en"

    normalized = text
    # Apply civic terminology translation
    for pattern, replacement in CIVIC_DICTIONARY:
        normalized = re.sub(pattern, replacement, normalized)

    # Clean up excess spaces or untranslated boilerplate
    normalized = re.sub(r'[\u0900-\u097F]+', '', normalized) # remove remaining untranslated script
    normalized = re.sub(r'\s+', ' ', normalized).strip()

    if not normalized:
        # Fallback if text couldn't be parsed
        normalized = f"Civic issue reported in {LANGUAGES.get(detected_lang, {}).get('name', 'regional language')}: {text[:80]}"

    return normalized, detected_lang


def get_department_and_action(category_name: str, severity: int = 3, lang: str = "en") -> Dict[str, str]:
    """
    Returns the recommended municipal department and suggested remediation action
    localized to the specified language.
    """
    target_lang = lang if lang in ("en", "hi", "mr") else "en"

    dept_entry = DEPARTMENT_MAP.get(category_name, DEPARTMENT_MAP["Other / Manual Review"])
    dept = dept_entry.get(target_lang, dept_entry["en"])

    action_entry = SUGGESTED_ACTIONS.get(category_name, SUGGESTED_ACTIONS["Other / Manual Review"])
    action = action_entry.get(target_lang, action_entry["en"])

    return {
        "department": dept,
        "action": action,
        "department_en": dept_entry["en"],
        "action_en": action_entry["en"]
    }


def localize_metadata(data: Dict[str, Any], lang: str = "en") -> Dict[str, Any]:
    """
    Localizes category, priority, status, department, and actions inside serialized dict.
    """
    target_lang = lang if lang in ("en", "hi", "mr") else "en"

    result = dict(data)
    cat = result.get("category")
    if cat and cat in CATEGORY_TRANSLATIONS:
        result["category_localized"] = CATEGORY_TRANSLATIONS[cat].get(target_lang, cat)
    else:
        result["category_localized"] = cat

    prio = result.get("issue_priority_level") or (result.get("ai", {}) or {}).get("priority_level")
    if prio:
        prio_upper = str(prio).upper()
        if prio_upper in PRIORITY_TRANSLATIONS:
            result["priority_localized"] = PRIORITY_TRANSLATIONS[prio_upper].get(target_lang, prio)

    status = result.get("issue_status") or result.get("submission_status")
    if status:
        status_upper = str(status).upper()
        if status_upper in STATUS_TRANSLATIONS:
            result["status_localized"] = STATUS_TRANSLATIONS[status_upper].get(target_lang, status)

    dept_info = get_department_and_action(cat or "Other / Manual Review", result.get("severity", 3), target_lang)
    result["recommended_department"] = dept_info["department"]
    result["suggested_action"] = dept_info["action"]

    return result
