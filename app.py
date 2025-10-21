# app.py
from flask import Flask, render_template, request, jsonify
import pytesseract
from PIL import Image
import os
from datetime import datetime

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'static/uploads'

# --- Helper: OCR function ---
def extract_text(image_path):
    img = Image.open(image_path)
    text = pytesseract.image_to_string(img)
    return text.strip()

# --- Routes ---
@app.route('/')
def home():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_image():
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400

    filepath = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
    file.save(filepath)

    text = extract_text(filepath)

    # Very basic placeholder logic
    quick_verdict = "✅ Appears safe for general consumption"
    detailed_report = [
        {"nutrient": "Sugar", "impact": "Moderate — safe for non-diabetics"},
        {"nutrient": "Sodium", "impact": "Within normal range"},
    ]

    # Example of where scan logs could be stored later
    scan_data = {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "filename": file.filename,
        "ocr_text": text,
        "quick_verdict": quick_verdict,
        "detailed_report": detailed_report,
    }

    return jsonify(scan_data)

if __name__ == '__main__':
    os.makedirs('static/uploads', exist_ok=True)
    app.run(debug=True)
