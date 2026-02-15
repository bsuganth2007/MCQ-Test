CD# MCQ Test Application - ICSE Grade 10

A standalone web-based Multiple Choice Questions (MCQ) test application for ICSE Grade 10 students.

## 🎯 Features
- Random selection of 20 questions per test
- Multiple subjects supported (Physics, Maths, etc.)
- Interactive test interface with progress tracking
- Instant results with detailed answer review
- Test history tracking
- Score calculation and performance feedback
- Responsive design

## 📁 Project Location
**D:\Suganthi\Projects\MCQ-Test-App**

## 📊 Question Bank
- **File**: `backend/data/questions.csv`
- **Total Questions**: 1,500
  - Physics: 500 questions
  - Maths: 1,000 questions
- **Format**: CSV with columns: Subject, Question, Option A, Option B, Option C, Option D, Correct Option, Difficulty

## 🚀 Quick Start

### Method 1: Double-click to Run
1. Double-click **`start_server.bat`**
2. Wait for the message: "Running on http://localhost:5001"
3. Open **`frontend/index.html`** in your web browser
4. Select a subject and start testing!

### Method 2: Manual Start
```bash
# Navigate to MCQ-Test-App folder
cd D:\Suganthi\Projects\MCQ-Test-App

# Activate virtual environment
venv\Scripts\activate

# Start backend server
cd backend
python app.py
```
- Server runs on: **http://localhost:5001**
- Then open `frontend/index.html` in your browser

## 📂 Project Structure
```
MCQ-Test-App/
├── backend/
│   ├── app.py                    # Flask backend (Port 5001)
│   ├── requirements.txt          # Python dependencies
│   └── data/
│       ├── questions.csv         # 1,500 question bank
│       └── history.db            # Auto-created test history database
├── frontend/
│   ├── index.html                # Landing page / Subject selection
│   ├── test.html                 # Test interface
│   ├── results.html              # Results page
│   ├── history.html              # Test history page
│   ├── css/
│   │   └── style.css             # Application styles
│   └── js/
│       ├── app.js                # Main application logic
│       ├── test.js               # Test page functionality
│       └── results.js            # Results page functionality
├── venv/                         # Python virtual environment
├── start_server.bat              # Quick start script
└── README.md                     # This file
```

## 🔧 Technical Details

### Backend (Flask API)
- **Port**: 5001 (to avoid conflicts with other applications)
- **Framework**: Flask with CORS enabled
- **Database**: SQLite for history tracking

### API Endpoints
- `GET /api/subjects` - Get available subjects
- `GET /api/questions/<subject>` - Get 20 random questions for a subject
- `POST /api/submit` - Submit test answers and get results
- `GET /api/history` - Get all test history
- `GET /api/history/<test_id>` - Get detailed results for a specific test

### Frontend
- Pure HTML, CSS, JavaScript
- No build tools required
- Communicates with backend on port 5001

## 📦 Dependencies (Already Installed)
```
flask==3.1.2
flask-cors==6.0.2
pandas==3.0.0
openpyxl==3.1.5
```

## ✏️ Adding More Questions

1. Open `backend/data/questions.csv`
2. Add new rows with the following columns:
   - **Subject**: Physics, Maths, Chemistry, Biology, etc.
   - **Question**: The question text
   - **Option A**: First option
   - **Option B**: Second option
   - **Option C**: Third option
   - **Option D**: Fourth option
   - **Correct Option**: A, B, C, or D
   - **Difficulty**: Easy, Medium, Hard
3. Save the file
4. Restart the server

## 🎮 How to Use

1. **Start the server**: Run `start_server.bat`
2. **Open the app**: Open `frontend/index.html` in a web browser
3. **Select a subject**: Click on Physics or Maths
4. **Take the test**: Answer 20 randomly selected questions
5. **Submit**: Review your results with correct answers
6. **View history**: Check past test scores and performance

## 🛠️ Troubleshooting

### Server won't start
- Check if port 5001 is available
- Ensure Python is installed (3.8+)
- Verify virtual environment is set up correctly

### No questions loading
- Verify `backend/data/questions.csv` exists
- Check CSV format matches expected columns
- Look for errors in the server console

### Frontend can't connect to backend
- Ensure backend server is running on port 5001
- Check browser console for CORS errors
- Verify API_URL in JavaScript files points to localhost:5001

## 🔒 Note
This application is completely standalone and separate from the academic-generator project. It uses its own:
- Virtual environment
- Port (5001 instead of 5000)
- Database
- Dependencies

---

**Version**: 1.0  
**Last Updated**: February 9, 2026  
**Location**: D:\Suganthi\Projects\MCQ-Test-App
