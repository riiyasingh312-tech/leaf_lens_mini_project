from flask import Flask, request, jsonify, render_template, redirect, session, send_from_directory
import requests
import base64
import os
import json
from datetime import datetime

app = Flask(__name__, static_folder='.', template_folder='.')
app.secret_key = 'leaflens_secret_2025'

# ─── CONFIG ─────────────────────────────────────────────────────────────────
# Get your FREE API key from https://plant.id (sign up, then go to API keys)
PLANT_ID_API_KEY = "YOUR_PLANT_ID_API_KEY_HERE"

# Demo users (in real app, use a database)
USERS = {
    "admin": "admin123",
    "riya": "password123",
    "demo": "demo"
}

# Simple file-based history storage
HISTORY_FILE = "history.json"

# ─── HELPERS ─────────────────────────────────────────────────────────────────
def load_history():
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, 'r') as f:
            return json.load(f)
    return []

def save_history(history):
    with open(HISTORY_FILE, 'w') as f:
        json.dump(history, f, indent=2)

# ─── ROUTES ──────────────────────────────────────────────────────────────────

@app.route('/')
def index():
    return send_from_directory('.', 'login.html')

@app.route('/dashboard')
def dashboard():
    return send_from_directory('.', 'dashboard.html')

@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    username = data.get('username', '').strip()
    password = data.get('password', '').strip()

    if username in USERS and USERS[username] == password:
        session['user'] = username
        return jsonify({'success': True, 'message': 'Login successful', 'username': username})
    else:
        return jsonify({'success': False, 'message': 'Invalid username or password'}), 401

@app.route('/logout', methods=['POST'])
def logout():
    session.pop('user', None)
    return jsonify({'success': True})

@app.route('/analyze', methods=['POST'])
def analyze():
    if 'image' not in request.files:
        return jsonify({'error': 'No image provided'}), 400

    image_file = request.files['image']
    image_bytes = image_file.read()
    image_base64 = base64.b64encode(image_bytes).decode('utf-8')

    # ── Call Plant.id API ──
    if PLANT_ID_API_KEY == "YOUR_PLANT_ID_API_KEY_HERE":
        # Demo mode — return mock data
        result = demo_analysis()
    else:
        result = call_plant_id_api(image_base64)

    # Save to history
    history = load_history()
    history.insert(0, {
        'id': int(datetime.now().timestamp()),
        'filename': image_file.filename,
        'date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        **result
    })
    save_history(history[:100])  # Keep last 100

    return jsonify(result)

def call_plant_id_api(image_base64):
    """Calls Plant.id Health Assessment API"""
    url = "https://api.plant.id/v2/health_assessment"
    headers = {
        "Content-Type": "application/json",
        "Api-Key": PLANT_ID_API_KEY
    }
    payload = {
        "images": [image_base64],
        "modifiers": {"crops_fast": True, "similar_images": False},
        "language": "en",
        "disease_details": ["cause", "description", "treatment"]
    }

    try:
        response = requests.post(url, headers=headers, json=payload, timeout=30)
        response.raise_for_status()
        data = response.json()

        # Parse response
        health = data.get('health_assessment', {})
        is_healthy = health.get('is_healthy', True)
        diseases = health.get('diseases', [])

        plant_name = "Unknown"
        # Try to get plant name from suggestions
        suggestions = data.get('suggestions', [])
        if suggestions:
            plant_name = suggestions[0].get('plant_name', 'Unknown')

        if is_healthy or not diseases:
            return {
                'plant': plant_name.title(),
                'status': 'Healthy',
                'disease': 'None',
                'confidence': str(round(health.get('is_healthy_probability', 0.9) * 100, 1)) + '%',
                'suggestion': 'Your plant looks healthy! Keep up the good care. 🌱'
            }
        else:
            top_disease = diseases[0]
            disease_name = top_disease.get('name', 'Unknown Disease')
            confidence = round(top_disease.get('probability', 0) * 100, 1)
            treatment = top_disease.get('disease_details', {}).get('treatment', {})
            treatment_text = treatment.get('chemical', ['Apply appropriate treatment'])[0] if treatment else 'Consult an agronomist.'

            return {
                'plant': plant_name.title(),
                'status': 'Diseased',
                'disease': disease_name,
                'confidence': str(confidence) + '%',
                'suggestion': treatment_text
            }

    except requests.exceptions.RequestException as e:
        return {'error': str(e), 'plant': 'Error', 'status': 'Error', 'disease': '—', 'confidence': '—', 'suggestion': 'API call failed. Check your API key and internet connection.'}

def demo_analysis():
    """Returns a random demo result when no API key is set"""
    import random
    demos = [
        {
            'plant': 'Tomato',
            'status': 'Healthy',
            'disease': 'None',
            'confidence': '94.2%',
            'suggestion': 'Plant looks great! Continue regular watering and sunlight exposure. 🌱'
        },
        {
            'plant': 'Rose',
            'status': 'Diseased',
            'disease': 'Black Spot (Diplocarpon rosae)',
            'confidence': '87.5%',
            'suggestion': 'Apply a fungicide containing myclobutanil. Remove and dispose of infected leaves.'
        },
        {
            'plant': 'Potato',
            'status': 'Diseased',
            'disease': 'Late Blight (Phytophthora infestans)',
            'confidence': '91.0%',
            'suggestion': 'Use copper-based fungicide immediately. Avoid overhead watering. Destroy infected plants.'
        },
        {
            'plant': 'Mango',
            'status': 'Healthy',
            'disease': 'None',
            'confidence': '89.3%',
            'suggestion': 'Healthy leaf detected! Ensure proper drainage and balanced fertilization. 🥭'
        }
    ]
    return random.choice(demos)

@app.route('/history', methods=['GET'])
def get_history():
    return jsonify(load_history())

@app.route('/history/clear', methods=['DELETE'])
def clear_history():
    save_history([])
    return jsonify({'success': True})

# ─── RUN ─────────────────────────────────────────────────────────────────────
if __name__ == '__main__':
    print("\n🌿 Leaf Lens Server Starting...")
    print("=" * 40)
    print("  Open in browser: http://localhost:5000")
    print("  Demo login:  admin / admin123")
    if PLANT_ID_API_KEY == "YOUR_PLANT_ID_API_KEY_HERE":
        print("\n  ⚠️  API KEY NOT SET — Running in DEMO mode")
        print("  Get free key: https://plant.id")
        print("  Then replace YOUR_PLANT_ID_API_KEY_HERE in app.py")
    print("=" * 40 + "\n")
    app.run(debug=True, port=5000)