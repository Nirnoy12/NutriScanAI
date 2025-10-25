# app.py
from flask import (
    Flask, render_template, request, jsonify, redirect, url_for, flash
)
from flask_login import (
    LoginManager, UserMixin, login_user, logout_user, login_required, current_user
)
from werkzeug.security import generate_password_hash, check_password_hash
import pytesseract
from PIL import Image
import os
import json
from datetime import datetime
from werkzeug.utils import secure_filename

# --- App Setup ---
app = Flask(__name__)
# A secret key is required for sessions
app.config['SECRET_KEY'] = 'your_super_secret_key_change_this' 
app.config['UPLOAD_FOLDER'] = 'static/uploads'

# --- Database Files (Using JSON for simplicity) ---
USERS_FILE = 'users.json'
HISTORIES_FILE = 'histories.json'

# --- Flask-Login Setup ---
login_manager = LoginManager()
login_manager.init_app(app)
# If a user tries to access a protected page, redirect them to '/login'
login_manager.login_view = 'login' 
login_manager.login_message = "You must be logged in to view this page."

# --- User Model ---
class User(UserMixin):
    def __init__(self, id, username, password_hash):
        self.id = id
        self.username = username
        self.password_hash = password_hash

# --- User Storage Helper Functions (JSON) ---
def load_users():
    if not os.path.exists(USERS_FILE):
        return {}
    with open(USERS_FILE, 'r') as f:
        return json.load(f)

def save_users(users_db):
    with open(USERS_FILE, 'w') as f:
        json.dump(users_db, f)

def get_user_by_username(username):
    users_db = load_users()
    user_data = users_db.get(username)
    if user_data:
        return User(id=username, username=username, password_hash=user_data['password_hash'])
    return None

# --- History Storage Helper Functions (JSON) ---
def load_histories():
    if not os.path.exists(HISTORIES_FILE):
        return {}
    with open(HISTORIES_FILE, 'r') as f:
        return json.load(f)

def save_histories(histories_db):
    with open(HISTORIES_FILE, 'w') as f:
        json.dump(histories_db, f)

# --- Flask-Login User Loader ---
@login_manager.user_loader
def load_user(user_id):
    # user_id is the username in our case
    return get_user_by_username(user_id)

# --- Helper: OCR function ---
def extract_text(image_path):
    try:
        img = Image.open(image_path)
        text = pytesseract.image_to_string(img)
        return text.strip()
    except Exception as e:
        print(f"Error during OCR: {e}")
        return "Error: Could not extract text."

# ==================================
# --- AUTHENTICATION ROUTES ---
# ==================================

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('home')) # Already logged in

    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = get_user_by_username(username)

        # Check if user exists and password is correct
        if user and check_password_hash(user.password_hash, password):
            login_user(user) # This creates the session
            return redirect(url_for('home'))
        else:
            flash("Invalid username or password.")
    
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('home'))

    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        users_db = load_users()

        if username in users_db:
            flash("Username already exists.")
        else:
            # Create new user
            new_user = {
                'password_hash': generate_password_hash(password)
            }
            users_db[username] = new_user
            save_users(users_db)
            
            # Log the new user in
            user_obj = User(id=username, username=username, password_hash=new_user['password_hash'])
            login_user(user_obj)
            return redirect(url_for('home'))

    return render_template('register.html')

@app.route('/logout')
@login_required # Must be logged in to log out
def logout():
    logout_user()
    return redirect(url_for('login'))

# ==================================
# --- PROTECTED APP ROUTES ---
# ==================================

@app.route('/')
@login_required # <-- PROTECTS the main app page
def home():
    # Pass the username to the template
    return render_template('index.html', username=current_user.username)

@app.route('/history', methods=['GET'])
@login_required # <-- PROTECTS the history API
def get_history():
    histories_db = load_histories()
    # Get history for the SPECIFIC logged-in user
    user_history = histories_db.get(current_user.id, [])
    return jsonify(user_history)

@app.route('/analyze', methods=['POST'])
@login_required # <-- PROTECTS the analyze API
def analyze_image():
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400

    original_filename = secure_filename(file.filename)
    timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{current_user.id}_{timestamp_str}_{original_filename}"
    
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    file.save(filepath)

    text = extract_text(filepath)

    quick_verdict = "✅ Appears safe for general consumption"
    detailed_report = [
        {"nutrient": "Sugar", "impact": "Moderate"},
        {"nutrient": "Sodium", "impact": "Normal"},
    ]

    scan_data = {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "filename": filename,  
        "ocr_text": text,
        "quick_verdict": quick_verdict,
        "detailed_report": detailed_report,
    }
    
    # --- ADD TO PERSONALIZED HISTORY ---
    histories_db = load_histories()
    user_history = histories_db.get(current_user.id, [])
    user_history.insert(0, scan_data)
    user_history = user_history[:30] # Keep last 30
    
    histories_db[current_user.id] = user_history
    save_histories(histories_db)
    # ----------------------------------

    return jsonify(scan_data)

if __name__ == '__main__':
    os.makedirs('static/uploads', exist_ok=True)
    app.run(debug=True)