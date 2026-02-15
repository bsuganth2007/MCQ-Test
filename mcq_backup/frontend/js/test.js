const API_URL = 'http://localhost:5001/api';

const QUESTIONS_PER_PAGE = 5;
let currentSubject = '';
let testMode = '';
let questions = [];
let currentPageIndex = 0;
let userAnswers = [];

// Initialize test on page load
window.onload = function() {
    currentSubject = sessionStorage.getItem('currentSubject');
    testMode = sessionStorage.getItem('testMode') || 'database';
    
    if (!currentSubject) {
        window.location.href = 'index.html';
        return;
    }
    
    const modeLabel = testMode === 'genai' ? '🤖 AI Generated' : '📚 Question Bank';
    document.getElementById('subject-title').textContent = `${currentSubject} Test - ${modeLabel}`;
    loadQuestions();
};

async function loadQuestions() {
    try {
        // Show loading message based on mode
        const loadingEl = document.getElementById('loading');
        if (testMode === 'genai') {
            loadingEl.textContent = '🤖 Generating questions with AI... This may take 10-15 seconds...';
        } else {
            loadingEl.textContent = 'Loading questions...';
        }
        
        // Choose endpoint based on mode
        const endpoint = testMode === 'genai' 
            ? `${API_URL}/questions/genai/${currentSubject}`
            : `${API_URL}/questions/${currentSubject}`;
        
        const response = await fetch(endpoint);
        const data = await response.json();
        
        if (!response.ok) {
            // Handle HTTP errors
            if (response.status === 429 && data.suggestion) {
                alert(`${data.error}\\n\\n${data.message}\\n\\n💡 ${data.suggestion}`);
            } else {
                alert(data.error || 'Failed to load questions');
            }
            window.location.href = 'index.html';
            return;
        }
        
        if (data.error) {
            alert(data.error);
            window.location.href = 'index.html';
            return;
        }
        
        questions = data.questions;
        userAnswers = new Array(questions.length).fill(null);
        
        document.getElementById('loading').style.display = 'none';
        document.getElementById('test-container').style.display = 'block';
        
        displayPage();
    } catch (error) {
        console.error('Error loading questions:', error);
        alert('Error loading questions. Please try again.');
        window.location.href = 'index.html';
    }
}

function displayPage() {
    const startIdx = currentPageIndex * QUESTIONS_PER_PAGE;
    const endIdx = Math.min(startIdx + QUESTIONS_PER_PAGE, questions.length);
    const totalPages = Math.ceil(questions.length / QUESTIONS_PER_PAGE);
    
    // Update progress and counter
    document.getElementById('question-counter').textContent = 
        `Questions ${startIdx + 1}-${endIdx} of ${questions.length} (Page ${currentPageIndex + 1}/${totalPages})`;
    document.getElementById('progress').style.width = 
        `${((endIdx) / questions.length) * 100}%`;
    
    // Clear and display questions
    const container = document.getElementById('questions-container');
    container.innerHTML = '';
    
    for (let i = startIdx; i < endIdx; i++) {
        const question = questions[i];
        const questionCard = createQuestionCard(question, i);
        container.appendChild(questionCard);
    }
    
    // Update navigation buttons
    document.getElementById('prev-btn').disabled = currentPageIndex === 0;
    
    if (currentPageIndex === totalPages - 1) {
        document.getElementById('next-btn').style.display = 'none';
        document.getElementById('submit-btn').style.display = 'block';
    } else {
        document.getElementById('next-btn').style.display = 'block';
        document.getElementById('submit-btn').style.display = 'none';
    }
}

function createQuestionCard(question, questionIndex) {
    const card = document.createElement('div');
    card.className = 'question-card';
    
    // Question number and text
    const questionNumber = document.createElement('div');
    questionNumber.className = 'question-number';
    questionNumber.textContent = `Question ${questionIndex + 1}`;
    card.appendChild(questionNumber);
    
    const questionText = document.createElement('h2');
    questionText.id = `question-text-${questionIndex}`;
    questionText.textContent = question.question;
    card.appendChild(questionText);
    
    // Options container
    const optionsContainer = document.createElement('div');
    optionsContainer.className = 'options-container';
    
    question.options.forEach((option, optionIndex) => {
        const radioLabel = document.createElement('label');
        radioLabel.className = 'radio-option';
        
        const radioInput = document.createElement('input');
        radioInput.type = 'radio';
        radioInput.name = `question-${questionIndex}`;
        radioInput.value = option;
        radioInput.onchange = () => selectOption(questionIndex, optionIndex);
        
        // Check if previously selected
        if (userAnswers[questionIndex] === option) {
            radioInput.checked = true;
        }
        
        radioLabel.appendChild(radioInput);
        radioLabel.appendChild(document.createTextNode(option));
        optionsContainer.appendChild(radioLabel);
    });
    
    card.appendChild(optionsContainer);
    return card;
}

function selectOption(questionIndex, optionIndex) {
    const question = questions[questionIndex];
    userAnswers[questionIndex] = question.options[optionIndex];
    
    // Update UI - refresh the current page to show selection
    displayPage();
}

function nextPage() {
    const totalPages = Math.ceil(questions.length / QUESTIONS_PER_PAGE);
    if (currentPageIndex < totalPages - 1) {
        currentPageIndex++;
        displayPage();
        window.scrollTo(0, 0); // Scroll to top when changing pages
    }
}

function previousPage() {
    if (currentPageIndex > 0) {
        currentPageIndex--;
        displayPage();
        window.scrollTo(0, 0); // Scroll to top when changing pages
    }
}

async function submitTest() {
    // Check if all questions are answered
    const unanswered = userAnswers.filter(a => a === null).length;
    if (unanswered > 0) {
        if (!confirm(`You have ${unanswered} unanswered questions. Do you want to submit anyway?`)) {
            return;
        }
    }
    
    // Prepare submission data
    const answers = questions.map((q, index) => ({
        question: q.question,
        user_answer: userAnswers[index] || 'Not Answered',
        correct_answer: q.correct_answer
    }));
    
    try {
        const response = await fetch(`${API_URL}/submit`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                subject: currentSubject,
                answers: answers
            })
        });
        
        const result = await response.json();
        
        // Store results and navigate to results page
        sessionStorage.setItem('testResults', JSON.stringify(result));
        window.location.href = 'results.html';
    } catch (error) {
        console.error('Error submitting test:', error);
        alert('Error submitting test. Please try again.');
    }
}