# MCQ Test Application - Setup Complete! ✅

## 🔐 Security Update - API Key Configuration Required

**IMPORTANT:** The Gemini API key has been removed for security reasons. You need to configure your own API key before using AI features.

### Setting Up Your API Key:

1. **Get your Gemini API key:**
   - Visit: https://aistudio.google.com/app/apikey
   - Sign in with your Google account
   - Create a new API key

2. **Configure the key:**
   ```bash
   cd backend
   cp .env.example .env
   # Edit .env and add your API key
   ```

3. **Test your setup:**
   ```bash
   python backend/check_gemini.py
   ```

For detailed instructions, see [SECURITY_SETUP.md](SECURITY_SETUP.md)

---

## Your Question Bank
- **File**: `backend/data/questions.csv`
- **Total Questions**: 1,500
  - Physics: 500 questions
  - Maths: 1,000 questions

## How to Run

### Option 1: Quick Start
1. Double-click `start_server.bat` to start the backend server
2. Open `frontend/index.html` in your web browser
3. Select a subject and start testing!

### Option 2: Manual Start
1. Open terminal in the `backend` directory
2. Run: `D:\Suganthi\Projects\academic-generator\venv\Scripts\python.exe app.py`
3. Server will start at http://localhost:5000
4. Open `frontend/index.html` in your browser

## Features
✅ Random 20 questions per test  
✅ Instant scoring and feedback  
✅ Test history tracking  
✅ Answer review after test  
✅ Progress tracking during test  

## Files Structure
```
mcq-test-app/
├── backend/
│   ├── app.py                    # Flask backend
│   ├── requirements.txt          # Dependencies (already installed in venv)
│   └── data/
│       ├── questions.csv         # Your 1,500 question bank
│       └── history.db            # Auto-created test history database
├── frontend/
│   ├── index.html                # Landing/subject selection page
│   ├── test.html                 # Test interface
│   ├── results.html              # Results page
│   ├── history.html              # Test history page
│   ├── css/style.css             # Styling
│   └── js/
│       ├── app.js                # Main app logic
│       ├── test.js               # Test page logic
│       └── results.js            # Results page logic
└── start_server.bat              # Quick start script
```

## API Endpoints

### Backend (http://localhost:5000)
- `GET /api/subjects` - Get available subjects
- `GET /api/questions/<subject>` - Get 20 random questions
- `POST /api/submit` - Submit test answers
- `GET /api/history` - Get test history
- `GET /api/history/<test_id>` - Get specific test details

## Dependencies (Already Installed)
- Flask 3.0.0
- Flask-CORS 4.0.0
- Pandas 3.0.0
- openpyxl 3.1.5

## Notes
- Backend uses existing venv at: `D:\Suganthi\Projects\academic-generator\venv`
- Questions are loaded from CSV with columns: Subject, Question, Option A, Option B, Option C, Option D, Correct Option, Difficulty
- Test history is saved in SQLite database (auto-created)
- Currently available subjects: Physics, Maths

## Adding More Subjects
To add Chemistry or Biology questions:
1. Open `backend/data/questions.csv`
2. Add rows with Subject = "Chemistry" or "Biology"
3. Ensure columns match: Subject, Question, Option A, Option B, Option C, Option D, Correct Option, Difficulty
4. Restart the server

## Troubleshooting
- **Port 5000 already in use**: Close other Flask apps or change port in backend/app.py
- **CSV not found error**: Ensure questions.csv is in backend/data/ folder
- **CORS errors**: Make sure Flask-CORS is installed and enabled in app.py
