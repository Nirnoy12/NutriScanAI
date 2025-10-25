import os
import logging
from datetime import datetime, UTC
from flask import Flask, render_template, request, jsonify, redirect, url_for, flash
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from PIL import Image
from flask_sqlalchemy import SQLAlchemy
from transformers import TrOCRProcessor, VisionEncoderDecoderModel, AutoImageProcessor, AutoModelForImageClassification, AutoTokenizer, AutoModelForCausalLM
from huggingface_hub import InferenceClient
from openai import OpenAI
from config import Config

# --- Logging Setup ---
logging.basicConfig(level=logging.DEBUG)

# --- App Setup ---
app = Flask(__name__)
app.config.from_object(Config)

# --- Database Setup ---
db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = "You must be logged in to access this page."

# --- AI Client Setup ---
# Check if HF_TOKEN is set
if not app.config['HF_TOKEN']:
    raise ValueError("HF_TOKEN is not set. Please add it to your .env file.")

# Initialize Hugging Face Inference Client for food recognition
FOOD_MODEL = "nateraw/food"
try:
    food_client = InferenceClient(token=app.config['HF_TOKEN'])
    logging.info("Hugging Face Inference Client for food initialized successfully.")
except Exception as e:
    logging.error(f"Hugging Face Inference Client initialization FAILED: {repr(e)}")
    food_client = None

# Initialize OpenAI client for chat
CHAT_MODEL = "meta-llama/Llama-3.1-8B-Instruct:novita"
try:
    chat_client = OpenAI(
        base_url="https://router.huggingface.co/v1",
        api_key=app.config['HF_TOKEN'],
    )
    logging.info("OpenAI client for chat initialized successfully.")
except Exception as e:
    logging.error(f"OpenAI client initialization FAILED: {repr(e)}")
    chat_client = None

# ==================================
# --- DATABASE MODELS ---
# ==================================
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    scans = db.relationship('Scan', backref='user', lazy=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class Scan(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(200), nullable=False)
    timestamp = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(UTC))
    scan_type = db.Column(db.String(50), nullable=False)
    quick_verdict = db.Column(db.String(300), nullable=False)
    ocr_text = db.Column(db.Text, nullable=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

# ==================================
# --- AI HELPER FUNCTIONS ---
# ==================================
def extract_text(image_path):
    """Uses local TrOCR model to read text from images."""
    OCR_MODEL = "microsoft/trocr-small-printed"
    try:
        logging.debug(f"Loading OCR model: {OCR_MODEL}")
        # Force slow tokenizer to avoid SentencePiece to Tiktoken conversion
        ocr_processor = TrOCRProcessor.from_pretrained(OCR_MODEL, token=app.config['HF_TOKEN'], use_fast=False)
        ocr_model = VisionEncoderDecoderModel.from_pretrained(OCR_MODEL, token=app.config['HF_TOKEN'])
        logging.debug(f"Processing image with OCR model: {image_path}")
        image = Image.open(image_path).convert("RGB")
        pixel_values = ocr_processor(image, return_tensors="pt").pixel_values
        generated_ids = ocr_model.generate(pixel_values)
        text = ocr_processor.batch_decode(generated_ids, skip_special_tokens=True)[0]
        if text and text.strip():
            logging.debug(f"OCR extracted text: {text}")
            return text.strip()
        else:
            logging.warning("OCR model returned empty text.")
            return "OCR model returned empty text. Image may be unclear."
    except Exception as e:
        logging.error(f"Local OCR Error: {repr(e)}")
        return f"Error: Could not read text from image. (Reason: {repr(e)})"

def recognize_food(image_path):
    """Uses Hugging Face Inference API for food recognition with local fallback."""
    # Try Inference API first
    if food_client:
        try:
            logging.debug(f"Trying Inference API with food model: {FOOD_MODEL}")
            results = food_client.image_classification(image_path, model=FOOD_MODEL)
            if results and len(results) > 0:
                best_guess = results[0]
                food_name = best_guess['label'].replace('_', ' ').title()
                confidence = best_guess['score']
                quick_verdict = f"Food: {food_name} ({confidence:.1%})"
                report_data = [{"nutrient": item['label'].replace('_', ' ').title(), "impact": f"{item['score']:.1%}"} for item in results[:5]]
                logging.debug(f"Food recognition successful: {quick_verdict}")
                return quick_verdict, report_data
            else:
                logging.warning("Food API returned empty results.")
                return "Could not identify food in this image.", []
        except Exception as e:
            logging.error(f"HF Food API Error: {repr(e)}")
    
    # Fallback to local model
    try:
        logging.debug(f"Falling back to local food model: {FOOD_MODEL}")
        food_processor = AutoImageProcessor.from_pretrained(FOOD_MODEL, token=app.config['HF_TOKEN'])
        food_model = AutoModelForImageClassification.from_pretrained(FOOD_MODEL, token=app.config['HF_TOKEN'])
        image = Image.open(image_path).convert("RGB")
        inputs = food_processor(image, return_tensors="pt")
        outputs = food_model(**inputs)
        logits = outputs.logits
        probs = logits.softmax(dim=-1)
        top_result = probs[0].argmax()
        food_name = food_model.config.id2label[top_result.item()].replace('_', ' ').title()
        confidence = probs[0][top_result].item()
        quick_verdict = f"Food: {food_name} ({confidence:.1%})"
        report_data = [
            {"nutrient": food_model.config.id2label[i].replace('_', ' ').title(), "impact": f"{probs[0][i].item():.1%}"}
            for i in probs[0].topk(5).indices
        ]
        logging.debug(f"Local food recognition successful: {quick_verdict}")
        return quick_verdict, report_data
    except Exception as e:
        logging.error(f"Local Food Model Error: {repr(e)}")
        return f"Error: Could not identify food. (Reason: {repr(e)})", []

def chat_with_bot_local(message):
    """Uses local DistilGPT-2 model for chatbot conversation."""
    CHAT_FALLBACK_MODEL = "distilgpt2"
    try:
        logging.debug(f"Loading local chat model: {CHAT_FALLBACK_MODEL}")
        chat_tokenizer = AutoTokenizer.from_pretrained(CHAT_FALLBACK_MODEL, token=app.config['HF_TOKEN'])
        chat_model = AutoModelForCausalLM.from_pretrained(CHAT_FALLBACK_MODEL, token=app.config['HF_TOKEN'])
        user_scans = Scan.query.filter_by(user_id=current_user.id).order_by(Scan.timestamp.desc()).limit(10).all()
        eaten_foods = [scan.quick_verdict for scan in user_scans]
        system_prompt = f"You are NutriBot, a helpful AI nutrition assistant. The user's recent scans: {', '.join(eaten_foods)}. Be concise and helpful."
        prompt = f"{system_prompt}\n\nUser: {message}"
        logging.debug(f"Chat prompt: {prompt}")
        inputs = chat_tokenizer(prompt, return_tensors="pt", truncation=True, max_length=512)
        outputs = chat_model.generate(
            inputs["input_ids"],
            max_new_tokens=250,
            temperature=0.7,
            pad_token_id=chat_tokenizer.eos_token_id
        )
        response = chat_tokenizer.decode(outputs[0], skip_special_tokens=True)
        response = response[len(prompt):].strip()
        logging.debug(f"Chat response: {response}")
        return response
    except Exception as e:
        logging.error(f"Local Chat Model Error: {repr(e)}")
        return f"Error: Chatbot failed. (Reason: {repr(e)})"

# ==================================
# --- AUTHENTICATION ROUTES ---
# ==================================
@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    if request.method == 'POST':
        user = User.query.filter_by(username=request.form['username']).first()
        if user and user.check_password(request.form['password']):
            login_user(user)
            return redirect(url_for('home'))
        else:
            flash("Invalid username or password.")
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    if request.method == 'POST':
        if User.query.filter_by(username=request.form['username']).first():
            flash("Username already exists.")
        else:
            new_user = User(username=request.form['username'])
            new_user.set_password(request.form['password'])
            db.session.add(new_user)
            db.session.commit()
            login_user(new_user)
            return redirect(url_for('home'))
    return render_template('register.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

# ==================================
# --- PROTECTED APP ROUTES ---
# ==================================
@app.route('/')
@login_required
def home():
    return render_template('index.html', username=current_user.username)

@app.route('/history', methods=['GET'])
@login_required
def get_history():
    """Fetches personalized history from the database."""
    try:
        user_scans = Scan.query.filter_by(user_id=current_user.id).order_by(Scan.timestamp.desc()).limit(30).all()
        history_list = [{
            "filename": scan.filename,
            "timestamp": scan.timestamp.strftime("%Y-%m-%d %H:%M"),
            "quick_verdict": scan.quick_verdict,
            "ocr_text": scan.ocr_text
        } for scan in user_scans]
        logging.debug(f"History fetched for user {current_user.id}: {len(history_list)} scans")
        return jsonify(history_list)
    except Exception as e:
        logging.error(f"History Error: {repr(e)}")
        return jsonify({'error': f'Failed to fetch history: {repr(e)}'}), 500

@app.route('/analyze', methods=['POST'])
@login_required
def analyze_image():
    """Analyzes an image (OCR or Food) and saves to DB."""
    logging.debug(f"Received /analyze request: {request.form}, files: {request.files}")
    
    if 'file' not in request.files:
        logging.error("No file part in the request")
        return jsonify({'error': 'No file part in the request'}), 400
    
    file = request.files['file']
    scan_type = request.form.get('scan_type', 'label')

    if file.filename == '':
        logging.error("No file selected")
        return jsonify({'error': 'No file selected'}), 400
    
    allowed_extensions = {'png', 'jpg', 'jpeg', 'webp'}
    if not ('.' in file.filename and file.filename.rsplit('.', 1)[1].lower() in allowed_extensions):
        logging.error(f"Invalid file type: {file.filename}")
        return jsonify({'error': f"Invalid file type. Please upload a (png, jpg, jpeg, webp) file. Got: {file.filename}"}), 400
    
    file.seek(0, 2)
    file_size = file.tell()
    file.seek(0)
    if file_size > 10 * 1024 * 1024:  # 10MB
        logging.error(f"File too large: {file_size} bytes")
        return jsonify({'error': f'File too large (Max 10MB). Got: {file_size} bytes'}), 400
    
    if scan_type not in ['label', 'food']:
        logging.error(f"Invalid scan_type: {scan_type}")
        return jsonify({'error': f"Invalid scan_type. Must be 'label' or 'food'. Got: {scan_type}"}), 400

    original_filename = secure_filename(file.filename)
    timestamp_str = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
    filename = f"{current_user.id}_{timestamp_str}_{original_filename}"
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    
    try:
        os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
        file.save(filepath)
        logging.debug(f"File saved: {filepath}")
    except Exception as e:
        logging.error(f"Failed to save file: {repr(e)}")
        return jsonify({'error': f'Failed to save file: {repr(e)}'}), 500

    ocr_text = ""
    detailed_report = []

    try:
        if scan_type == 'label':
            ocr_text = extract_text(filepath)
            if "Error:" in ocr_text:
                logging.error(f"OCR failed: {ocr_text}")
                return jsonify({'error': ocr_text}), 400
            quick_verdict = "Label: " + (ocr_text.split('\n')[0] if ocr_text else "No text detected")
            detailed_report = [{"nutrient": "From OCR", "impact": "See text"}]
            logging.debug(f"OCR result: {quick_verdict}")
            
        elif scan_type == 'food':
            quick_verdict, report_data = recognize_food(filepath)
            if "Error:" in quick_verdict:
                logging.error(f"Food recognition failed: {quick_verdict}")
                return jsonify({'error': quick_verdict}), 400
            ocr_text = quick_verdict
            detailed_report = report_data
            logging.debug(f"Food recognition result: {quick_verdict}")

        new_scan = Scan(
            filename=filename,
            scan_type=scan_type,
            quick_verdict=quick_verdict,
            ocr_text=ocr_text,
            user_id=current_user.id
        )
        db.session.add(new_scan)
        db.session.commit()
        logging.debug(f"Scan saved to DB: {filename}, type: {scan_type}")

        return jsonify({
            "timestamp": new_scan.timestamp.strftime("%Y-%m-%d %H:%M"),
            "filename": new_scan.filename,
            "ocr_text": new_scan.ocr_text,
            "quick_verdict": new_scan.quick_verdict,
            "detailed_report": detailed_report,
            "type": new_scan.scan_type
        })
    except Exception as e:
        logging.error(f"Analyze Error: {repr(e)}")
        return jsonify({'error': f'An unexpected error occurred: {repr(e)}'}), 500

@app.route('/chat', methods=['POST'])
@login_required
def chat_with_bot():
    """Handles chatbot conversation using HF Inference API with local fallback."""
    logging.debug(f"Received /chat request: {request.json}")
    
    if not request.json or 'message' not in request.json:
        logging.error("No message provided in request")
        return jsonify({'error': 'No message provided'}), 400
    
    user_message = request.json['message'].strip()
    if not user_message:
        logging.error("Message cannot be empty")
        return jsonify({'error': 'Message cannot be empty'}), 400
    
    try:
        user_scans = Scan.query.filter_by(user_id=current_user.id).order_by(Scan.timestamp.desc()).limit(10).all()
        eaten_foods = [scan.quick_verdict for scan in user_scans]
        system_prompt = f"You are NutriBot, a helpful AI nutrition assistant. The user's recent scans: {', '.join(eaten_foods)}. Be concise and helpful."
        
        # Try OpenAI-compatible Inference API
        if chat_client:
            try:
                logging.debug(f"Trying Inference API with chat model: {CHAT_MODEL}")
                completion = chat_client.chat.completions.create(
                    model=CHAT_MODEL,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_message}
                    ],
                    max_tokens=250,
                    temperature=0.7,
                )
                response = completion.choices[0].message.content
                logging.debug(f"Chat API response: {response}")
                return jsonify({'reply': response})
            except Exception as e:
                logging.error(f"HF Chat API Error: {repr(e)}")
        
        # Fallback to local DistilGPT-2
        response = chat_with_bot_local(user_message)
        if "Error:" in response:
            logging.error(f"Chat fallback failed: {response}")
            return jsonify({'error': response}), 500
        logging.debug(f"Chat fallback response: {response}")
        return jsonify({'reply': response})
    except Exception as e:
        logging.error(f"Chat Error: {repr(e)}")
        return jsonify({'error': f"Chatbot error: {repr(e)}"}), 500

# ==================================
# --- APP INITIALIZATION ---
# ==================================
if __name__ == '__main__':
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    with app.app_context():
        db.create_all()
    app.run(debug=True)