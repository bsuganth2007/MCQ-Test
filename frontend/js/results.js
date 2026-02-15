// Simple but robust API URL determination
let API_URL = '/api';

// If we're on a different port (like VS Code Live Server 5500), we must point to the backend
if (window.location.port !== '5002' && (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1')) {
    API_URL = `${window.location.protocol}//${window.location.hostname}:5002/api`;
}

let allResultsData = null;

window.onload = function() {
    const resultsData = sessionStorage.getItem('testResults');
    
    if (!resultsData) {
        alert('No test results found. Please take a test first.');
        window.location.href = 'index.html';
        return;
    }
    
    allResultsData = JSON.parse(resultsData);
    
    // Show AI disclaimer if this was an AI generated test
    const disclaimer = document.getElementById('ai-disclaimer');
    if (disclaimer && allResultsData.source === 'ai_live_generation') {
        disclaimer.style.display = 'block';
    } else if (disclaimer) {
        disclaimer.style.display = 'none';
    }

    displayResults(allResultsData);
};

function filterResults(type) {
    if (!allResultsData) return;
    
    // Update active state in UI
    document.querySelectorAll('.score-item').forEach(item => {
        item.style.backgroundColor = 'rgba(255, 255, 255, 0.2)';
        item.style.transform = 'scale(1)';
    });

    if (type === 'all') {
        const totalCard = document.getElementById('total-count').closest('.score-item');
        totalCard.style.backgroundColor = 'rgba(255, 255, 255, 0.4)';
        renderReviewList(allResultsData.results);
        document.getElementById('review-heading-text').textContent = '📝 Detailed Review';
    } else if (type === 'correct') {
        const correctCard = document.getElementById('correct-count').closest('.score-item');
        correctCard.style.backgroundColor = 'rgba(40, 167, 69, 0.4)';
        const filtered = allResultsData.results.filter(r => r.is_correct);
        renderReviewList(filtered);
        document.getElementById('review-heading-text').textContent = `✅ Correct Answers (${filtered.length})`;
    } else if (type === 'incorrect') {
        const incorrectCard = document.getElementById('incorrect-count').closest('.score-item');
        incorrectCard.style.backgroundColor = 'rgba(220, 53, 69, 0.4)';
        const filtered = allResultsData.results.filter(r => !r.is_correct);
        renderReviewList(filtered);
        document.getElementById('review-heading-text').textContent = `✗ Incorrect Answers (${filtered.length})`;
    }
}

function displayResults(results) {
    // Display score
    document.getElementById('score').textContent = `${results.score.toFixed(1)}%`;
    document.getElementById('correct-count').textContent = results.correct_answers;
    document.getElementById('total-count').textContent = results.total_questions;
    
    const incorrect = results.total_questions - results.correct_answers;
    document.getElementById('incorrect-count').textContent = incorrect;
    
    // Set score color (using bright shades for visibility on dark gradient)
    const scoreElement = document.getElementById('score');
    if (results.score >= 80) {
        scoreElement.style.color = '#27ae60'; // Vibrant green
    } else if (results.score >= 60) {
        scoreElement.style.color = '#ffce00'; // Bright yellow
    } else {
        scoreElement.style.color = '#ff4d4d'; // Bright vibrant red
    }
    
    // Display detailed answers
    renderReviewList(results.results);
}

function renderReviewList(resultsArray) {
    const container = document.getElementById('answers-review');
    container.innerHTML = '';
    
    if (resultsArray.length === 0) {
        container.innerHTML = '<p style="text-align: center; padding: 20px; color: #666;">No questions to show in this filter.</p>';
        return;
    }
    
    resultsArray.forEach((result, index) => {
        const answerCard = document.createElement('div');
        answerCard.className = `answer-card ${result.is_correct ? 'correct' : 'incorrect'}`;
        
        // Find original index for question numbering
        const originalIndex = allResultsData.results.findIndex(r => r === result);
        
        // Format user answer
        let userAnswerDisplay = '';
        if (result.user_answer_letter === 'Not Answered') {
            userAnswerDisplay = `
                <div class="answer-display">
                    <span class="answer-text" style="color: #999; font-style: italic;">Not Answered</span>
                </div>
            `;
        } else {
            userAnswerDisplay = `
                <div class="answer-display">
                    <span class="answer-letter">${result.user_answer_letter})</span>
                    <span class="answer-text">${result.user_answer_text}</span>
                </div>
            `;
        }
        
        // Format correct answer
        const correctAnswerDisplay = `
            <div class="answer-display">
                <span class="answer-letter">${result.correct_answer_letter})</span>
                <span class="answer-text">${result.correct_answer_text}</span>
            </div>
        `;
        
        answerCard.innerHTML = `
            <div class="answer-header">
                <span class="question-number">Question ${originalIndex + 1}</span>
                <span class="answer-status ${result.is_correct ? 'status-correct' : 'status-incorrect'}">
                    ${result.is_correct ? '✓ Correct' : '✗ Incorrect'}
                </span>
            </div>
            
            <div class="question-text">${result.question}</div>
            
            <div class="answer-section">
                <div class="answer-row user-answer-row">
                    <span class="answer-label">Your Answer:</span>
                    ${userAnswerDisplay}
                </div>
                
                ${!result.is_correct ? `
                    <div class="answer-row correct-answer-row">
                        <span class="answer-label">Correct Answer:</span>
                        ${correctAnswerDisplay}
                    </div>
                ` : ''}
            </div>
        `;
        
        container.appendChild(answerCard);
    });

    renderMath();
}

function renderMath() {
    if (typeof renderMathInElement === 'function') {
        renderMathInElement(document.body, {
            delimiters: [
                {left: '$$', right: '$$', display: true},
                {left: '$', right: '$', display: false},
                {left: '\\(', right: '\\)', display: false},
                {left: '\\[', right: '\\]', display: true}
            ],
            throwOnError: false
        });
    }
}


function goHome() {
    sessionStorage.removeItem('testResults');
    window.location.href = 'index.html';
}

function viewHistory() {
    window.location.href = 'history.html';
}