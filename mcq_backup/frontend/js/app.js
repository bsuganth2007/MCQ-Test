const API_URL = 'http://localhost:5001/api';

let selectedMode = 'database'; // Default to database mode

function selectMode(mode) {
    selectedMode = mode;
    
    // Update button styles
    document.getElementById('db-mode-btn').classList.remove('active');
    document.getElementById('genai-mode-btn').classList.remove('active');
    
    if (mode === 'database') {
        document.getElementById('db-mode-btn').classList.add('active');
    } else {
        document.getElementById('genai-mode-btn').classList.add('active');
    }
}

function startTest(subject) {
    // Store subject and mode in session storage and navigate to test page
    sessionStorage.setItem('currentSubject', subject);
    sessionStorage.setItem('testMode', selectedMode);
    window.location.href = 'test.html';
}

function viewHistory() {
    window.location.href = 'history.html';
}