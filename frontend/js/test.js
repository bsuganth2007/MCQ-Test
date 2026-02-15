// Simple but robust API URL determination
let API_URL = '/api';

// If we're on a different port (like VS Code Live Server 5500), we must point to the backend
if (window.location.port !== '5002' && (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1')) {
    API_URL = `${window.location.protocol}//${window.location.hostname}:5002/api`;
}

console.log('🌐 App running at:', window.location.href);
console.log('🔌 API Base URL:', API_URL);

let currentSubject = '';
let questions = [];
let currentPageIndex = 0;
const QUESTIONS_PER_PAGE = 5;
let userAnswers = [];

window.onload = function() {
    console.log('=== TEST PAGE LOADED ===');
    console.log('API_URL:', API_URL);
    
    // Check if subject is selected
    currentSubject = (sessionStorage.getItem('currentSubject') || '').trim();
    console.log('currentSubject:', currentSubject);
    
    if (!currentSubject) {
        alert('No subject selected. Please select a subject from home page.');
        window.location.href = 'index.html';
        return;
    }
    
    // Check if user is identified
    const userId = localStorage.getItem('userId');
    const userName = localStorage.getItem('userName');
    console.log('User:', userId, userName);
    
    if (!userId) {
        alert('Please identify yourself first.');
        window.location.href = 'index.html';
        return;
    }
    
    document.getElementById('subject-title').textContent = `${currentSubject} Test`;
    loadQuestions();
};

async function loadQuestions() {
    try {
        const loadingElement = document.getElementById('loading');
        loadingElement.textContent = 'Loading questions...';
        
        const source = sessionStorage.getItem('questionSource') || 'database';
        console.log('Mode:', source);
        
        // Save source to ensure results page knows where questions came from
        if (source === 'genai') {
            sessionStorage.setItem('testSource', 'ai_live_generation');
        } else {
            sessionStorage.setItem('testSource', 'database');
        }
        
        let apiUrl = "";
        
        // Show AI disclaimer if in GenAI mode
        const disclaimer = document.getElementById('ai-disclaimer');
        if (source === 'genai' && disclaimer) {
            disclaimer.style.display = 'flex';
        }
        
        apiUrl = `${API_URL}/questions/${currentSubject}`;
        if (source === 'genai') {
            apiUrl = `${API_URL}/questions/ai-live/${currentSubject}`;
            loadingElement.innerHTML = `
                <div style="text-align: center;">
                    <div class="spinner-small" style="width: 40px; height: 40px; margin-bottom: 15px;"></div>
                    <p>🤖 AI is generating fresh questions for you...</p>
                    <p style="font-size: 0.8em; color: #666;">This usually takes 10-20 seconds</p>
                </div>
            `;
        }
        
        console.log('🔍 Fetching from:', apiUrl);
        console.log('📝 Question Source:', source);
        
        const response = await fetch(apiUrl);
        
        if (!response.ok) {
            let errorText = "";
            try {
                const errorData = await response.json();
                errorText = errorData.error;
            } catch (e) {
                errorText = await response.text();
            }
            
            console.error('❌ Response error:', errorText);
            
            if (errorText.includes('<!doctype html>') || errorText.includes('<!DOCTYPE html>')) {
                throw new Error(`The server at ${apiUrl} returned an HTML page instead of questions. This usually means the Backend (Python) is not running on port 5002, or the URL is incorrect.`);
            }
            throw new Error(errorText || `HTTP ${response.status}`);
        }
        
        const contentType = response.headers.get('content-type');
        console.log('🔍 Content-Type:', contentType);
        
        if (!contentType || !contentType.includes('application/json')) {
            const text = await response.text();
            console.error('❌ Not JSON response:', text);
            throw new Error('Server returned non-JSON response');
        }
        
        const data = await response.json();
        console.log('✅ Data received:', data);
        const questionCount = Array.isArray(data.questions) ? data.questions.length : 0;
        console.log('✅ Parsed questions count:', questionCount);
        
        if (data.error) {
            alert(data.error);
            window.location.href = 'index.html';
            return;
        }
        
        if (!data.questions || data.questions.length === 0) {
            alert('No questions available for this subject.');
            window.location.href = 'index.html';
            return;
        }
        
        questions = data.questions;
        userAnswers = new Array(questions.length).fill(null);
        
        console.log('✅ Loaded', questions.length, 'questions');

        loadingElement.textContent = 'Rendering questions...';
        loadingElement.style.display = 'none';
        document.getElementById('test-container').style.display = 'block';
        
        // Record start time
        sessionStorage.setItem('testStartTime', Date.now());
        
        try {
            displayQuestionsPage();
        } catch (renderError) {
            console.error('❌ Error rendering questions:', renderError);
            loadingElement.style.display = 'block';
            loadingElement.textContent = 'Failed to render questions. Check console for details.';
        }
        
    } catch (error) {
        console.error('❌ ERROR in loadQuestions:', error);
        
        if (error.message.includes("Quota Exceeded")) {
            alert("⚠️ AI Service Limit Reached\n\n" + error.message + "\n\nStandard questions from the database will be used instead.");
            window.location.href = 'index.html';
            return;
        }
        
        const errorMsg = `Error loading questions: ${error.message}\n\nPlease check:\n1. Is Flask running?\n2. Copy this URL to a new tab to test: ${apiUrl}\n3. Check if your Gemini API key is correct in backend/.env`;
        
        alert(errorMsg);
        
        // Don't redirect so user can see console
        console.log('Staying on page for debugging. Check console above.');
    }
}

function displayQuestionsPage() {
    const questionsContainer = document.getElementById('questions-page-container');
    questionsContainer.innerHTML = '';
    
    const startIndex = currentPageIndex * QUESTIONS_PER_PAGE;
    const endIndex = Math.min(startIndex + QUESTIONS_PER_PAGE, questions.length);
    
    // Update counter: "Questions 1-5 of 20"
    document.getElementById('question-counter').textContent = 
        `Questions ${startIndex + 1}-${endIndex} of ${questions.length}`;
    
    const progressPercent = (endIndex / questions.length) * 100;
    document.getElementById('progress').style.width = `${progressPercent}%`;
    
    for (let i = startIndex; i < endIndex; i++) {
        const question = questions[i];
        const questionText = normalizeDisplayText(question.question || '');
        
        // Ensure options array exists (Safety check)
        if (!question.options || !Array.isArray(question.options)) {
            question.options = [
                question.option_a || 'Option A',
                question.option_b || 'Option B',
                question.option_c || 'Option C',
                question.option_d || 'Option D'
            ];
        }

        const questionDiv = document.createElement('div');
        questionDiv.className = 'question-card';
        
        const optionLabels = ['A', 'B', 'C', 'D'];
        let optionsHtml = '';
        
        question.options.forEach((option, optIndex) => {
            const label = optionLabels[optIndex];
            const isSelected = userAnswers[i] === label;
            const optionText = normalizeDisplayText(option || '');
            optionsHtml += `
                <label class="radio-option ${isSelected ? 'selected' : ''}" data-q-index="${i}">
                    <input type="radio" name="option-${i}" value="${label}" ${isSelected ? 'checked' : ''} onchange="selectOption(${i}, '${label}')">
                    <span class="option-text">${label}. ${optionText}</span>
                </label>
            `;
        });

        questionDiv.innerHTML = `
            <h2 class="question-text">
                <span class="question-number">Question ${i + 1}:</span> ${questionText}
            </h2>
            <div class="options-container">
                ${optionsHtml}
            </div>
        `;
        questionsContainer.appendChild(questionDiv);
    }
    
    // Smooth scroll to top when page changes
    window.scrollTo({ top: 0, behavior: 'smooth' });
    
    document.getElementById('prev-btn').disabled = currentPageIndex === 0;
    
    const totalPages = Math.ceil(questions.length / QUESTIONS_PER_PAGE);
    if (currentPageIndex === totalPages - 1) {
        document.getElementById('next-btn').style.display = 'none';
        document.getElementById('submit-btn').style.display = 'block';
    } else {
        document.getElementById('next-btn').style.display = 'block';
        document.getElementById('submit-btn').style.display = 'none';
    }

    renderMath();
}

function normalizeDisplayText(text) {
    if (typeof text !== 'string') {
        return text;
    }

    const trimmed = text.trim();
    if (!trimmed) {
        return text;
    }

    // If KaTeX delimiters exist, leave as-is.
    if (trimmed.includes('$')) {
        return text;
    }

    // Wrap common LaTeX patterns in inline math to ensure rendering.
    const latexPattern = /(\\,|\\circ|\\frac|\\text|\\alpha|\\beta|\\gamma|\\delta|\\theta|\\pi|\\times|\\div|\\leq|\\geq|\\sqrt|\\rightarrow|\\cdot|_[0-9]|\^[0-9])/;
    if (latexPattern.test(trimmed)) {
        return `$${trimmed}$`;
    }

    // Fallback cleanup for raw degree tokens outside math mode.
    return trimmed.replace(/\\circ/g, '°');
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

function selectOption(questionIndex, optionLetter) {
    userAnswers[questionIndex] = optionLetter;
    
    // Update local UI for that specific question
    const options = document.querySelectorAll(`label[data-q-index="${questionIndex}"]`);
    options.forEach((opt) => {
        const radio = opt.querySelector('input');
        if (radio.value === optionLetter) {
            opt.classList.add('selected');
            radio.checked = true;
        } else {
            opt.classList.remove('selected');
            radio.checked = false;
        }
    });
}

function nextQuestion() {
    const totalPages = Math.ceil(questions.length / QUESTIONS_PER_PAGE);
    if (currentPageIndex < totalPages - 1) {
        currentPageIndex++;
        displayQuestionsPage();
    }
}

function previousQuestion() {
    if (currentPageIndex > 0) {
        currentPageIndex--;
        displayQuestionsPage();
    }
}

async function submitTest() {
    const unanswered = userAnswers.filter(a => a === null).length;
    if (unanswered > 0) {
        if (!confirm(`You have ${unanswered} unanswered questions. Do you want to submit anyway?`)) {
            return;
        }
    }
    
    // Get user info
    const userId = localStorage.getItem('userId');
    const userName = localStorage.getItem('userName');
    
    // Calculate duration
    const startTime = parseInt(sessionStorage.getItem('testStartTime') || Date.now());
    const durationSeconds = Math.floor((Date.now() - startTime) / 1000);
    
    console.log('📤 Submitting test...');
    console.log('User:', userId, userName);
    console.log('Duration:', durationSeconds, 'seconds');
    
    const answers = questions.map((q, index) => ({
        question: q.question,
        question_type: q.question_type || q.type || 'Standard',
        user_answer: userAnswers[index] || 'Not Answered',
        correct_answer: q.correct_answer || q.option_a, // Fallback, will be fixed by backend if needed
        question_data: {
            options: q.options,
            correct_option: q.correct_option // Pass this for AI-live questions
        }
    }));
    
    try {
        const response = await fetch(`${API_URL}/submit`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                subject: currentSubject,
                answers: answers,
                user_id: userId,
                user_name: userName,
                duration_seconds: durationSeconds,
                source: sessionStorage.getItem('testSource') // Pass the source
            })
        });
        
        console.log('Submit response status:', response.status);
        
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }
        
        const result = await response.json();
        console.log('✅ Test submitted successfully');
        
        sessionStorage.setItem('testResults', JSON.stringify(result));
        window.location.href = 'results.html';
        
    } catch (error) {
        console.error('❌ Error submitting test:', error);
        alert('Error submitting test. Please try again.');
    }
}