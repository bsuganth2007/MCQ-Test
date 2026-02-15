const API_URL = 'http://localhost:5001/api';

window.onload = function() {
    const urlParams = new URLSearchParams(window.location.search);
    const testId = urlParams.get('testId');
    
    if (testId) {
        // Load from history
        loadTestDetails(testId);
    } else {
        // Load from session storage (just submitted)
        const results = sessionStorage.getItem('testResults');
        if (!results) {
            window.location.href = 'index.html';
            return;
        }
        displayResults(JSON.parse(results));
    }
};

async function loadTestDetails(testId) {
    try {
        const response = await fetch(`${API_URL}/history/${testId}`);
        const data = await response.json();
        
        if (data.error) {
            alert(data.error);
            window.location.href = 'index.html';
            return;
        }
        
        // Format data to match displayResults format
        const results = {
            total_questions: data.test_info.total_questions,
            correct_answers: data.test_info.correct_answers,
            score: data.test_info.score,
            results: data.questions
        };
        
        displayResults(results);
    } catch (error) {
        console.error('Error loading test details:', error);
        alert('Error loading test details.');
        window.location.href = 'index.html';
    }
}

function displayResults(results) {
    document.getElementById('loading').style.display = 'none';
    document.getElementById('results-container').style.display = 'block';
    
    // Display score
    document.getElementById('score-percentage').textContent = `${results.score.toFixed(1)}%`;
    document.getElementById('score-details').textContent = 
        `${results.correct_answers}/${results.total_questions} Correct`;
    
    // Score message
    let message = '';
    if (results.score >= 90) {
        message = '🎉 Outstanding! Excellent work!';
    } else if (results.score >= 70) {
        message = '👏 Great job! Well done!';
    } else if (results.score >= 50) {
        message = '👍 Good effort! Keep practicing!';
    } else {
        message = '📚 Keep studying! You can do better!';
    }
    document.getElementById('score-message').textContent = message;
    
    // Display answer review
    const answersList = document.getElementById('answers-list');
    answersList.innerHTML = results.results.map((answer, index) => `
        <div class="answer-item ${answer.is_correct ? 'correct' : 'incorrect'}">
            <h3>Question ${index + 1}: ${answer.question}</h3>
            <div class="answer-detail">
                <span><strong>Your Answer:</strong></span>
                <span class="${answer.is_correct ? 'correct-answer' : 'incorrect-answer'}">
                    ${answer.user_answer}
                </span>
            </div>
            ${!answer.is_correct ? `
                <div class="answer-detail">
                    <span><strong>Correct Answer:</strong></span>
                    <span class="correct-answer">${answer.correct_answer}</span>
                </div>
            ` : ''}
            <div class="answer-detail">
                <span><strong>Result:</strong></span>
                <span>${answer.is_correct ? '✓ Correct' : '✗ Incorrect'}</span>
            </div>
        </div>
    `).join('');
}

function goHome() {
    sessionStorage.clear();
    window.location.href = 'index.html';
}

function viewHistory() {
    window.location.href = 'history.html';
}