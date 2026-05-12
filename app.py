
import os
import sqlite3
import hashlib
import traceback
from datetime import datetime
import uuid # Used for generating unique image filenames

from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import joblib
import pandas as pd
import pytesseract
import cv2
import base64
import numpy as np
import json
import re
import requests
import fitz  # PyMuPDF for handling PDF uploads

# 🔧 CONFIGURATION
pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
GROQ_API_KEY = "" # Add your Groq API key here
GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"

# 🔔 WEBHOOK URL (Change this to your n8n Production URL!)
N8N_WEBHOOK_URL = "http://localhost:5678/webhook-test/08a904c5-f9c8-49cf-b08d-37499ee82428"

# 🚀 FLASK SETUP
app = Flask(__name__, static_folder='static', static_url_path='')
CORS(app) 

# 📁 FOLDER SETUP FOR IMAGES
UPLOAD_FOLDER = os.path.join('static', 'reports')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# 🤖 LOAD HISTGRADIENT MODEL
model = joblib.load('risk_engine_model.joblib')

# 🗄️ DATABASE SETUP
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
        category TEXT,
        assigned_to TEXT,
        image_file_path TEXT 
    )''')

# 🛡️ BULLETPROOF SANITIZER
def safe_float(val):
    if val in [None, "", 0, "0", "null", "None"]: return None
    try:
        cleaned = re.sub(r'[^\d.]', '', str(val))
        return float(cleaned) if cleaned else None
    except:
        return None

def extract_val(pattern, text):
    m = re.search(pattern, text, re.I)
    return float(m.group(1)) if m else None

def extract_str(pattern, text):
    m = re.search(pattern, text, re.I)
    return m.group(1).strip() if m else None

def generate_patient_id(name, age):
    return hashlib.sha256(f"{name}_{age}".encode()).hexdigest()

# 🔔 NOTIFICATION SYSTEM LOGIC
def trigger_doctor_alert(patient_id, name, score, category, features):
    """Sends an alert to n8n for ALL cases. n8n will handle the routing."""
    
    payload = {
        "patient_id": patient_id,
        "name": name,
        "score": round(score, 1),
        "category": category,
        "timestamp": datetime.now().isoformat(),
        # Passing raw features in case you want to use them in n8n emails/messages later
        "clinical_data": features 
    }

    try:
        # 5-second timeout so it doesn't freeze your API if n8n is slow
        response = requests.post(N8N_WEBHOOK_URL, json=payload, timeout=5) 
        if response.status_code == 200:
            print(f"[Alert Success] {category} payload sent to n8n for {patient_id}")
        else:
            print(f"[Alert Failed] n8n returned status: {response.status_code}")
    except Exception as e:
        print(f"[Alert Error] Connection to n8n webhook failed: {e}")

@app.route('/')
def serve():
    return send_from_directory(app.static_folder, 'index.html')

# 🔀 DASHBOARD ENDPOINTS
@app.route('/api/intern-dashboard', methods=['GET'])
def get_intern_cases():
    try:
        with get_db_connection() as conn:
            cursor = conn.execute("SELECT patient_id, name, age, time, score, image_file_path FROM reports WHERE assigned_to = 'Intern Dashboard' ORDER BY time DESC")
            cases = [{"patient_id": row[0], "name": row[1], "age": row[2], "time": row[3], "score": row[4], "image_file_path": row[5]} for row in cursor.fetchall()]
        return jsonify({"cases": cases})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/senior-dashboard', methods=['GET'])
def get_senior_cases():
    try:
        with get_db_connection() as conn:
            cursor = conn.execute("SELECT patient_id, name, age, time, score, category, image_file_path FROM reports WHERE assigned_to = 'Senior Physician' ORDER BY score DESC")
            cases = [{"patient_id": row[0], "name": row[1], "age": row[2], "time": row[3], "score": row[4], "category": row[5], "image_file_path": row[6]} for row in cursor.fetchall()]
        return jsonify({"cases": cases})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/predict', methods=['POST'])
def predict():
    try:
        data = request.json
        name = data.get("patientName", "unknown")
        age = data.get("patientAge", 0)
        
        pid = data.get("patientId") or generate_patient_id(name, age)
        cbc = data.get("cbc", {})
        cmp = data.get("cmp", {})
        
        image_file_path = data.get("image_file_path", None)

        # 1. Clean Extraction (Explicitly mapped for 12-parameter NaN model)
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

        # 📊 2. DATA CONFIDENCE CALCULATOR
        present_params = sum(1 for v in features.values() if v is not None)
        confidence = round((present_params / 12) * 100)

        # 3. Unit Normalization
        if features["wbc"] is not None and features["wbc"] > 100: features["wbc"] /= 1000.0
        if features["platelets"] is not None and features["platelets"] > 2000: features["platelets"] /= 1000.0

        # 4. Model Prediction
        df_input = pd.DataFrame([features], dtype=float)
        score = model.predict(df_input)[0]
        category = "Critical" if score >= 70 else "Moderate" if score >= 40 else "Normal"

        # 🔀 5. TRIAGE ROUTING
        assigned_to = "Intern Dashboard" if category == "Normal" else "Senior Physician"

        # 🔔 5.5 FIRE ALERT TO N8N BEFORE DATABASE UPDATE
        trigger_doctor_alert(pid, name, score, category, features)

        # 6. Database Upsert 
        with get_db_connection() as conn:
            conn.execute('''
                INSERT INTO reports (patient_id, name, age, time, score, category, assigned_to, image_file_path)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(patient_id) DO UPDATE SET
                    time = excluded.time,
                    score = excluded.score,
                    category = excluded.category,
                    assigned_to = excluded.assigned_to,
                    image_file_path = excluded.image_file_path
            ''', (pid, name, age, datetime.now().isoformat(), round(score, 1), category, assigned_to, image_file_path))

        return jsonify({
            "score": round(score, 1), 
            "category": category, 
            "confidence": confidence,
            "assigned_to": assigned_to
        })

    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@app.route('/api/extract', methods=['POST'])
def extract():
    try:
        data = request.json
        raw_b64 = data.get('file_base64', '')
        
        if ',' in raw_b64:
            raw_b64 = raw_b64.split(',')[1]
            
        img_bytes = base64.b64decode(raw_b64)

        # 🖼️ DECODE IMAGE OR PDF
        np_arr = np.frombuffer(img_bytes, np.uint8)
        img = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)

        if img is None:
            doc = fitz.open(stream=img_bytes, filetype="pdf")
            page = doc.load_page(0)
            pix = page.get_pixmap(dpi=300)
            img = cv2.imdecode(np.frombuffer(pix.tobytes("png"), np.uint8), cv2.IMREAD_COLOR)

        if img is None:
            return jsonify({"error": "Failed to decode the uploaded file."}), 400

        # Save the decoded image to disk before running OCR
        unique_filename = f"report_{uuid.uuid4().hex[:8]}.png"
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
        cv2.imwrite(filepath, img)
        db_image_path = f"reports/{unique_filename}" 

        # 🔬 Pre-processing & OCR
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        gray = cv2.resize(gray, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)
        _, img_p = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        text = pytesseract.image_to_string(img_p, config=r'--oem 3 --psm 6')[:2500]

        # 🔥 AI EXTRACTION
        prompt = f"Extract medical data from this text into JSON. Format: {{'patientId': null, 'patientName': null, 'patientAge': null, 'cbc': {{'hemoglobin': null, 'wbc': null, 'platelets': null}}, 'cmp': {{'creatinine': null, 'glucose': null, 'urea': null, 'sodium': null, 'potassium': null, 'chloride': null, 'calcium': null, 'albumin': null, 'bilirubin': null}}}}. TEXT: {text}"

        res = requests.post(GROQ_API_URL, json={
            "model": "llama-3.1-8b-instant",
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0,
            "response_format": { "type": "json_object" }
        }, headers={"Authorization": f"Bearer {GROQ_API_KEY}"})

        parsed = res.json()['choices'][0]['message']['content']
        parsed = json.loads(parsed)

        # 🔁 FALLBACKS
        if not parsed.get("patientName") or "Drlogy" in str(parsed.get("patientName")):
            m = re.search(r'(?:Name|Patient|Mr|Ms|Mrs)\.?\s*:?\s*([A-Za-z\s.]+)', text, re.I)
            if m: parsed["patientName"] = m.group(1).strip()

        return jsonify({
            "extracted": parsed,
            "image_file_path": db_image_path 
        })

    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True, use_reloader=False)
