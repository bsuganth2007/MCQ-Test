# ICSE Grade 10 - MCQ Test Application

A web-based Multiple Choice Questions (MCQ) test application for ICSE Grade 10 students covering Physics, Chemistry, Mathematics, and Biology.

## 🚀 Quick Links

- **[Cloud Deployment Guide](RENDER_DEPLOYMENT.md)** - Fix database reset issues on Render/cloud platforms
- **[Environment Template](.env.template)** - Configure PostgreSQL connection
- **[Setup Verification](verify_setup.py)** - Run `python verify_setup.py` to check your database configuration

## Features

- ✅ Subject selection (Physics, Chemistry, Maths, Biology)
- ✅ Random selection of 20 questions per test
- ✅ Interactive test interface with progress tracking
- ✅ Instant results with answer review
- ✅ Test history tracking
- ✅ Score calculation and performance feedback
- ✅ Responsive design
- ✅ PostgreSQL support for cloud deployment with persistent storage

## Technology Stack

- **Frontend**: HTML, CSS, JavaScript
- **Backend**: Python, Flask
- **Database**: SQLite (local development) / PostgreSQL (production), CSV (for questions)

## Project Structure

```
mcq-test-app/
├── backend/
│   ├── app.py                 # Flask application
│   ├── requirements.txt       # Python dependencies
│   ├── data/
│   │   ├── questions.xlsx     # Excel file with questions
│   │   └── history.db         # SQLite database (auto-created)
│   └── utils/
│       └── db_helper.py       # Database helper functions
├── frontend/
│   ├── index.html             # Landing page
│   ├── test.html              # Test page
│   ├── results.html           # Results page
│   ├── history.html           # History page
│   ├── css/
│   │   └── style.css          # Styling
│   └── js/
│       ├── app.js             # Main JavaScript
│       ├── test.js            # Test logic
│       └── results.js         # Results logic
└── README.md
```

## Setup Instructions

### Prerequisites

- Python 3.8 or higher
- pip (Python package manager)
- Modern web browser
- PostgreSQL (optional, for production deployment)

### Local Development Setup

1. **Navigate to the backend directory:**
   ```bash
   cd backend
   ```

2. **Create a virtual environment (recommended):**
   ```bash
   python -m venv venv
   
   # On Windows
   venv\Scripts\activate
   
   # On macOS/Linux
   source venv/bin/activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Prepare the questions Excel file:**
   
   Create a file named `questions.xlsx` in the `backend/data/` directory with the following structure:

   | Subject   | Question                          | Option1 | Option2 | Option3 | Option4 | CorrectOption |
   |-----------|-----------------------------------|---------|---------|---------|---------|---------------|
   | Physics   | What is Newton's first law?       | ...     | ...     | ...     | ...     | Option1       |
   | Chemistry | What is H2O?                      | ...     | ...     | ...     | ...     | Option2       |
   | Maths     | What is 2+2?                      | ...     | ...     | ...     | ...     | Option4       |
   | Biology   | What is photosynthesis?           | ...     | ...     | ...     | ...     | Option3       |

   **Important:** 
   - The `CorrectOption` column should contain exactly one of: "Option1", "Option2", "Option3", or "Option4"
   - Make sure you have at least 20 questions per subject

5. **Run the Flask application:**
   ```bash
   python app.py
   ```

   The backend server will start at `http://localhost:5000`

### Frontend Setup

1. **Navigate to the frontend directory:**
   ```bash
   cd frontend
   ```

2. **Serve the frontend:**
   
   You can use any of these methods:

   **Option A: Python's built-in server**
   ```bash
   python -m http.server 8000
   ```

   **Option B: Node.js http-server**
   ```bash
   npx http-server -p 8000
   ```

   **Option C: VS Code Live Server**
   - Right-click on `index.html` and select "Open with Live Server"

3. **Access the application:**
   
   Open your browser and navigate to:
   ```
   http://localhost:8000
   ```

## Usage Guide

### Taking a Test

1. **Select a Subject**: Click on one of the four subject cards (Physics, Chemistry, Maths, Biology)
2. **Answer Questions**: 
   - Read each question carefully
   - Click on your chosen answer option
   - Use "Next" to move to the next question
   - Use "Previous" to go back and review answers
3. **Submit**: Click "Submit Test" on the last question
4. **View Results**: Review your score and see correct answers

### Viewing History

1. Click "View Test History" on the home page
2. See all your past test attempts with scores
3. Click "View Details" on any test to see the full answer review

## API Endpoints

### Get Available Subjects
```
GET /api/subjects
```

### Get Questions for a Subject
```
GET /api/questions/<subject>
```

### Submit Test
```
POST /api/submit
Body: {
  "subject": "Physics",
  "answers": [...]
}
```

### Get Test History
```
GET /api/history
```

### Get Test Details
```
GET /api/history/<test_id>
```

## Excel File Format

The questions Excel file must have the following columns:

- **Subject**: The subject name (Physics, Chemistry, Maths, Biology)
- **Question**: The question text
- **Option1**: First option
- **Option2**: Second option
- **Option3**: Third option
- **Option4**: Fourth option
- **CorrectOption**: The correct answer (must be "Option1", "Option2", "Option3", or "Option4")

## Database Schema

### test_history table
- `id`: Primary key
- `subject`: Subject name
- `total_questions`: Total number of questions
- `correct_answers`: Number of correct answers
- `score`: Percentage score
- `timestamp`: Test completion time

### question_history table
- `id`: Primary key
- `test_id`: Foreign key to test_history
- `question`: Question text
- `user_answer`: User's answer
- `correct_answer`: Correct answer
- `is_correct`: Boolean flag

## Customization

### Adding More Questions

Simply add more rows to the `questions.xlsx` file following the same format.

### Changing Number of Questions

In `backend/app.py`, modify this line:
```python
selected_questions = random.sample(questions, min(20, len(questions)))
```

### Styling

Edit `frontend/css/style.css` to customize the appearance.

### Adding Features

Some ideas for enhancement:
- Timer for tests
- User authentication
- Question difficulty levels
- Subject-wise analytics
- Export results to PDF
- Question bookmarking

## Troubleshooting

### CORS Errors

If you see CORS errors in the browser console:
- Make sure Flask-CORS is installed: `pip install flask-cors`
- Check that the backend is running on port 5000
- Verify the API_URL in JavaScript files matches your backend URL

### Excel File Not Found

- Ensure `questions.xlsx` is in the `backend/data/` directory
- Check file name spelling and extension

### Database Errors

- The database is created automatically on first run
- If you see database errors, delete `backend/data/history.db` and restart the backend

## Cloud Deployment (Render, Heroku, etc.)

### ⚠️ Important: Database Persistence Issue

**Problem**: When deploying on cloud platforms like Render, the SQLite database (`data/history.db`) gets reset on every redeploy because it's stored in ephemeral container storage. This means user history and test data are lost.

**Solution**: Use PostgreSQL for persistent storage in production.

### Quick Deployment Guide

1. **Set up PostgreSQL database** on your cloud platform (Render, Heroku, etc.)
2. **Set environment variable**: `DATABASE_URL=postgresql://...`
3. **Deploy your application** - the app will automatically use PostgreSQL
4. **Migrate existing data** (optional): Run `python backend/migrate_sqlite_to_postgres.py`

📖 **Detailed deployment guide**: See [RENDER_DEPLOYMENT.md](RENDER_DEPLOYMENT.md) for complete step-by-step instructions for deploying on Render with PostgreSQL.

### Database Support

The application automatically detects which database to use:
- **Local Development**: SQLite (`data/history.db`) - data stored locally
- **Production** (with `DATABASE_URL` set): PostgreSQL - persistent cloud storage

No code changes needed - just set the `DATABASE_URL` environment variable!

## Contributing

Feel free to submit issues and enhancement requests!

## License

This project is open-source and available for educational purposes.

## References

- ICSE Grade 10 Syllabi:
  - [Physics](https://static.pw.live/5eb393ee95fab7468a79d189/GLOBAL_CMS_BLOGS/7bd8b48d-69a8-4fae-8774-f372c27bc340.pdf)
  - [Chemistry](https://static.pw.live/5eb393ee95fab7468a79d189/GLOBAL_CMS_BLOGS/2414ba1a-c26e-4878-90e2-ad9a05018a22.pdf)
  - [Mathematics](https://static.pw.live/5eb393ee95fab7468a79d189/GLOBAL_CMS_BLOGS/272712d7-228f-4e81-a75e-f14742c28416.pdf)
  - [Biology](https://static.pw.live/5eb393ee95fab7468a79d189/GLOBAL_CMS_BLOGS/0211119d-9a94-4bd0-9b7b-a69b8ee8f557.pdf)