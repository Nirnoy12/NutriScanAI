# NutriScanAI

A Flask-based web application that uses AI to analyze food items through image scanning. Users can scan food labels for OCR text extraction or identify food items using computer vision.

## Features

- **User Authentication**: Secure login/registration system
- **Image Scanning**: Camera-based and file upload scanning
- **AI-Powered Analysis**: 
  - OCR text extraction from food labels
  - Food recognition and classification
  - Intelligent chatbot for nutrition advice
- **Scan History**: Personalized history tracking
- **Modern UI**: Responsive design with loading states and error handling

## Technology Stack

- **Backend**: Flask, Flask-SQLAlchemy, Flask-Login
- **Database**: SQLite
- **AI/ML**: Hugging Face API (OCR, Food Recognition, Chat)
- **Frontend**: HTML5, CSS3, JavaScript (Vanilla)
- **Image Processing**: Pillow (PIL)

## Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd NutriScanAI
   ```

2. **Create and activate virtual environment**
   ```bash
   python -m venv venv
   # Windows
   venv\Scripts\activate
   # macOS/Linux
   source venv/bin/activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up environment variables**
   Create a `.env` file in the root directory:
   ```
   SECRET_KEY=your_secret_key_here
   HF_TOKEN=your_huggingface_token_here
   DATABASE_URL=sqlite:///nutriscanai.db
   ```

5. **Run the application**
   ```bash
   python app.py
   ```

6. **Access the application**
   Open your browser and go to `http://localhost:5000`

## Usage

1. **Register/Login**: Create an account or login with existing credentials
2. **Choose Scan Type**: Select between "Read Label" (OCR) or "Identify Food" (classification)
3. **Scan**: Use your camera or upload an image file
4. **View Results**: See the analysis results and detailed reports
5. **Chat**: Ask the AI chatbot questions about your scanned items
6. **History**: View your scan history and interact with previous results

## API Endpoints

- `GET /` - Home page (requires authentication)
- `GET /login` - Login page
- `POST /login` - Login form submission
- `GET /register` - Registration page
- `POST /register` - Registration form submission
- `GET /logout` - Logout user
- `GET /history` - Get user's scan history
- `POST /analyze` - Analyze uploaded image
- `POST /chat` - Chat with AI bot

## Configuration

The application uses environment variables for configuration:

- `SECRET_KEY`: Flask secret key for sessions
- `HF_TOKEN`: Hugging Face API token
- `DATABASE_URL`: Database connection string

## Security Features

- Password hashing with Werkzeug
- Secure file uploads with filename sanitization
- User session management
- Input validation and error handling
- Environment variable configuration

## Development

The application is structured as follows:

```
NutriScanAI/
├── app.py              # Main Flask application
├── config.py           # Configuration management
├── requirements.txt    # Python dependencies
├── .env               # Environment variables (not in git)
├── .gitignore         # Git ignore rules
├── templates/         # HTML templates
├── static/           # Static assets (CSS, JS, images)
└── README.md         # This file
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## License

This project is licensed under the MIT License.

## Support

For support or questions, please open an issue in the repository.
