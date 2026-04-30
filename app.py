
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import joblib
import pandas as pd
import traceback
import sqlite3
import hashlib
from datetime import datetime
import pytesseract
import cv2
import base64
import numpy as np
import json
import re
import requests
import fitz  # PyMuPDF for handling PDF uploads
import os

# 🔧 CONFIGURATION
pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
GROQ_API_KEY="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"
GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"

app = Flask(__name__, static_folder='static', static_url_path='')
CORS(app) # 🌉 Allows Live Server to talk to this Flask backend

# 🤖 LOAD HISTGRADIENT MODEL
model = joblib.load('risk_engine_model.joblib')

# 🗄️ DATABASE SETUP (Now with UNIQUE patient_id)
def get_db_connection():
    return sqlite3.connect('patients.db', check_same_thread=False)

with get_db_connection() as conn:
    conn.execute('''
    CREATE TABLE IF NOT EXISTS reports (
        id INTEGER PRIMARY KEY AUTOINCREMENT, 
        patient_id TEXT UNIQUE, 
        name TEXT, 
        age INTEGER, 
        time TEXT, 
        score REAL, 
        category TEXT
    )''')

# 🛡️ BULLETPROOF SANITIZER
def safe_float(val):
    if val in [None, "", 0, "0", "null", "None"]: return None
    try:
        cleaned = re.sub(r'[^\d.]', '', str(val))
        return float(cleaned) if cleaned else None
    except:
        return None

# 🔁 NUMBER REGEX HELPER
def extract_val(pattern, text):
    m = re.search(pattern, text, re.I)
    return float(m.group(1)) if m else None

# 🔁 STRING REGEX HELPER (For Patient IDs and Names)
def extract_str(pattern, text):
    m = re.search(pattern, text, re.I)
    return m.group(1).strip() if m else None

def generate_patient_id(name, age):
    return hashlib.sha256(f"{name}_{age}".encode()).hexdigest()

@app.route('/')
def serve():
    return send_from_directory(app.static_folder, 'index.html')

@app.route('/api/predict', methods=['POST'])
def predict():
    try:
        data = request.json
        name = data.get("patientName", "unknown")
        age = data.get("patientAge", 0)
        
        # 👇 Prefer the real Patient ID from the report, fallback to Hash if missing
        pid = data.get("patientId")
        if not pid:
            pid = generate_patient_id(name, age)

        cbc = data.get("cbc", {})
        cmp = data.get("cmp", {})

        # 1. Clean Extraction (All 12 Parameters)
        features = {
            "hemoglobin": safe_float(cbc.get("hemoglobin")),
            "wbc": safe_float(cbc.get("wbc")),
            "platelets": safe_float(cbc.get("platelets")),
            "creatinine": safe_float(cmp.get("creatinine")),
            "bloodSugar": safe_float(cmp.get("glucose")),
            "urea": safe_float(cmp.get("urea")),
            "sodium": safe_float(cmp.get("sodium")),
            "potassium": safe_float(cmp.get("potassium")),
            "chloride": safe_float(cmp.get("chloride")),
            "calcium": safe_float(cmp.get("calcium")),
            "albumin": safe_float(cmp.get("albumin")),
            "bilirubin": safe_float(cmp.get("bilirubin"))
        }

        # 2. Automatic Unit Normalization
        if features["wbc"] is not None and features["wbc"] > 100:
            features["wbc"] = features["wbc"] / 1000.0
        if features["platelets"] is not None and features["platelets"] > 2000:
            features["platelets"] = features["platelets"] / 1000.0

        # 3. Model Prediction (dtype=float safely handles missing data as NaN)
        df_input = pd.DataFrame([features], dtype=float)
        score = model.predict(df_input)[0]
        category = "Critical" if score >= 70 else "Moderate" if score >= 40 else "Normal"

        # 4. Save to Database (THE UPSERT FIX)
        with get_db_connection() as conn:
            conn.execute('''
                INSERT INTO reports (patient_id, name, age, time, score, category)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(patient_id) DO UPDATE SET
                    time = excluded.time,
                    score = excluded.score,
                    category = excluded.category
            ''', (pid, name, age, datetime.now().isoformat(), round(score, 1), category))

        return jsonify({"score": round(score, 1), "category": category})

    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


@app.route('/api/extract', methods=['POST'])


def extract():
    try:
        data = request.json
        raw_b64 = data.get('file_base64', '')
        
        print("\n=== 🔍 NEW UPLOAD DIAGNOSTIC ===")
        print(f"1. Raw B64 Length from Frontend: {len(raw_b64)}")

        # 🧹 STRIP HTML5 PREFIX
        if ',' in raw_b64:
            raw_b64 = raw_b64.split(',')[1]
            
        img_bytes = base64.b64decode(raw_b64)
        print(f"2. Decoded File Size: {len(img_bytes)} bytes")

        # 🖼️ ATTEMPT IMAGE DECODING
        np_arr = np.frombuffer(img_bytes, np.uint8)
        img = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)

        if img is not None:
            print("3. ✅ Successfully read as standard Image.")
        else:
            print("3. ❌ OpenCV rejected it as an image. Trying PyMuPDF (PDF)...")
            import fitz  # PyMuPDF
            doc = fitz.open(stream=img_bytes, filetype="pdf")
            print(f"   -> PDF successfully opened! Total Pages: {len(doc)}")
            
            page = doc.load_page(0)
            pix = page.get_pixmap(dpi=300)
            
            # 🛡️ THE BULLETPROOF CONVERSION
            png_bytes = pix.tobytes("png")
            img = cv2.imdecode(np.frombuffer(png_bytes, np.uint8), cv2.IMREAD_COLOR)
            
            if img is not None:
                print("   -> ✅ PDF successfully converted to OpenCV Image!")
            else:
                print("   -> ❌ CRITICAL: PDF converted to bytes, but OpenCV failed to read it.")

        if img is None:
            return jsonify({"error": "Failed to decode the uploaded file."}), 400

        print("4. Proceeding to Tesseract OCR...")
        
        # 🔬 Pre-processing
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        
        # ... [KEEP THE REST OF YOUR OCR AND AI LOGIC HERE] ...
        
        gray = cv2.resize(gray, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)
        _, img_p = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        kernel = np.ones((1, 1), np.uint8)
        img_p = cv2.dilate(img_p, kernel, iterations=1)

        custom_config = r'--oem 3 --psm 6'
        text = pytesseract.image_to_string(img_p, config=custom_config)[:2500]

        print("\n" + "="*50)
        print("RAW OCR TEXT DETECTED:")
        print(text[:500]) 
        print("="*50 + "\n")

        # 🔥 ANTI-HALLUCINATION PROMPT
        prompt = f"""
        You are a Medical Data Specialist. Extract data from this OCR text.
        
        STRICT EXTRACTION RULES:
        1. FIND THE PATIENT ID: Look for "Patient ID", "PID", or similar. 
        2. FIND THE PATIENT NAME: Look specifically for text following "Patient Name:", "Name:", or "Patient:". 
        3. IGNORE LOGOS: Do NOT extract names from the laboratory header (ignore "Drlogy", "Pathology Lab").
        4. FIND THE AGE: Look for "Age:" or "Yrs". If not found, output null. DO NOT GUESS.
        5. NO SUBSTITUTIONS: If the CURRENT result is unreadable, garbled (e.g. "isi' Sl"), or missing, YOU MUST OUTPUT null. DO NOT grab the "Previous" result. DO NOT grab the reference range. 
        6. Return ONLY valid JSON.
        
        TEXT: {text}
        
        FORMAT:
        {{
          "patientId": null,
          "patientName": null, "patientAge": null,
          "cbc": {{ "hemoglobin": null, "wbc": null, "platelets": null }},
          "cmp": {{ "creatinine": null, "glucose": null, "urea": null, "sodium": null, "potassium": null, "chloride": null, "calcium": null, "albumin": null, "bilirubin": null }}
        }}
        """

        res = requests.post(GROQ_API_URL, json={
            "model": "llama-3.1-8b-instant",
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0,
            "response_format": { "type": "json_object" }
        }, headers={"Authorization": f"Bearer {GROQ_API_KEY}"})

        # 🛡️ API RESPONSE SAFETY CHECK
        res_data = res.json()
        if 'choices' not in res_data:
            print("❌ GROQ API ERROR:", res_data)
            return jsonify({"error": "AI Provider Error", "details": res_data}), 500

        output = res_data['choices'][0]['message']['content']
        output = output.replace("```json", "").replace("```", "").strip()

        # 🛡️ JSON SAFETY PARSING
        match = re.search(r'\{.*\}', output, re.DOTALL)
        if not match: 
            return jsonify({"error": "No JSON found in AI response"}), 500
            
        json_str = match.group(0)
        parsed = json.loads(json_str)

        # ---------------------------------------------------------
        # 🔁 REDUNDANT REGEX FALLBACK SYSTEM
        # ---------------------------------------------------------
        
        # 0. Patient ID Fallback
        if not parsed.get("patientId"):
            parsed["patientId"] = extract_str(r"Patient ID[^\w]*([A-Za-z0-9]+)", text)

        # 1. Name Fallback (Bypasses the "Drlogy" hallucination)
        if not parsed.get("patientName") or "Drlogy" in str(parsed.get("patientName")):
            name_match = re.search(r'(?:Name|Patient|Mr|Ms|Mrs)\.?\s*:?\s*([A-Za-z\s.]+)', text, re.I)
            if name_match:
                parsed["patientName"] = name_match.group(1).strip()

        # 2. Values Fallback (Locked to the SAME LINE using [^\d\n])
        parsed["cbc"]["hemoglobin"] = safe_float(parsed["cbc"].get("hemoglobin")) or extract_val(r"hemoglobin[^\d\n]{0,40}?([\d.]+)", text)
        parsed["cbc"]["wbc"] = safe_float(parsed["cbc"].get("wbc")) or extract_val(r"wbc[^\d\n]{0,40}?([\d.]+)", text)
        parsed["cmp"]["glucose"] = safe_float(parsed["cmp"].get("glucose")) or extract_val(r"(glucose|sugar)[^\d\n]{0,40}?([\d.]+)", text)

        return jsonify({"extracted": parsed})

    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True, use_reloader=False)