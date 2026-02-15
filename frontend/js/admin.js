window.onload = function() {
    // Check authorization
    const userEmail = localStorage.getItem('userEmail');
    const ADMIN_EMAIL = 'bsuganth@gmail.com';

    if (userEmail !== ADMIN_EMAIL) {
        alert('Unauthorized access. Only user bsuganth@gmail.com is allowed to access the admin panel.');
        window.location.href = 'index.html';
        return;
    }
    
    // Continue with normal loading
    loadStats();
    loadPendingQuestions();
};

// Simple but robust API URL determination
let API_URL = '/api';

// If we're on a different port (like VS Code Live Server 5500), we must point to the backend
if (window.location.port !== '5002' && (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1')) {
    API_URL = `${window.location.protocol}//${window.location.hostname}:5002/api`;
}

let currentEditQuestionId = null;
let selectedQuestions = new Set();
let pendingQuestions = [];

async function loadStats() {
    try {
        const response = await fetch(`${API_URL}/admin/stats`);
        const data = await response.json();
        
        const statsGrid = document.getElementById('stats-grid');
        statsGrid.innerHTML = '';
        
        for (const [subject, stats] of Object.entries(data.stats)) {
            statsGrid.innerHTML += `
                <div class="stat-card">
                    <h3>${subject}</h3>
                    <div class="stat-numbers">
                        <div class="stat-item">
                            <span class="stat-value pending">${stats.pending}</span>
                            <span class="stat-label">Pending</span>
                        </div>
                        <div class="stat-item">
                            <span class="stat-value approved">${stats.approved}</span>
                            <span class="stat-label">Approved</span>
                        </div>
                    </div>
                </div>
            `;
        }
    } catch (error) {
        console.error('Error loading stats:', error);
    }
}

async function loadPendingQuestions() {
    const subject = document.getElementById('subject-select').value;
    const url = subject ? 
        `${API_URL}/admin/pending-questions?subject=${subject}` :
        `${API_URL}/admin/pending-questions`;
    
    try {
        const response = await fetch(url);
        const data = await response.json();
        pendingQuestions = data.pending_questions;
        
        document.getElementById('pending-count').textContent = data.count;
        
        const questionsList = document.getElementById('pending-questions-list');
        
        if (data.count === 0) {
            questionsList.innerHTML = `
                <div style="text-align: center; padding: 60px;">
                    <h3>No pending questions for review</h3>
                    <p style="color: #666; margin: 20px 0;">Generate new questions to start reviewing</p>
                    <button class="btn btn-primary" onclick="showGenerateModal()">
                        ✨ Generate Questions
                    </button>
                </div>
            `;
            return;
        }
        
        questionsList.innerHTML = data.pending_questions.map(q => `
            <div class="question-card" id="question-${q.id}">
                <div class="question-header">
                    <input type="checkbox" class="question-checkbox" 
                           value="${q.id}" 
                           onchange="toggleQuestionSelection(${q.id})"
                           style="margin-right: 15px;">
                    <div style="flex: 1;">
                        <div class="question-meta">
                            <span class="badge badge-subject">${q.subject}</span>
                            <span class="badge badge-type">${q.question_type}</span>
                            <span class="badge" style="background: #667eea; color: white;">
                                📖 ${q.chapter_name || 'General'}
                            </span>
                            <span class="badge badge-pending">Pending Review</span>
                        </div>
                        <div class="question-text">${q.question}</div>
                        <div class="question-options">
                            <div class="option-item ${q.correct_option === 'A' ? 'correct' : ''}">
                                A. ${q.option_a}
                            </div>
                            <div class="option-item ${q.correct_option === 'B' ? 'correct' : ''}">
                                B. ${q.option_b}
                            </div>
                            <div class="option-item ${q.correct_option === 'C' ? 'correct' : ''}">
                                C. ${q.option_c}
                            </div>
                            <div class="option-item ${q.correct_option === 'D' ? 'correct' : ''}">
                                D. ${q.option_d}
                            </div>
                        </div>

                        ${q.explanation ? `
                        <div class="explanation-box" style="margin-top: 15px; padding: 12px; background: #f0f2ff; border-radius: 8px; font-size: 0.9em; border-left: 4px solid #667eea;">
                            <strong>💡 AI Explanation:</strong> ${q.explanation}
                        </div>
                        ` : ''}

                        <div id="ai-feedback-${q.id}" class="ai-feedback" style="display: none; margin-top: 15px; padding: 12px; border-radius: 8px; border-left: 4px solid #6c5ce7; background: #fff;">
                            <!-- AI feedback will be injected here -->
                        </div>

                        <div class="question-actions">
                            <button class="btn btn-ai btn-small" onclick="verifyWithAI(${q.id})" style="background: #6c5ce7; color: white;">
                                ✨ Verify with AI
                            </button>
                            <button class="btn btn-success btn-small" onclick="approveQuestion(${q.id})">
                                ✓ Approve & Add to CSV
                            </button>
                            <button class="btn btn-edit btn-small" onclick="editQuestion(${q.id})">
                                ✎ Edit
                            </button>
                            <button class="btn btn-danger btn-small" onclick="rejectQuestion(${q.id})">
                                ✗ Reject
                            </button>
                        </div>
                    </div>
                </div>
            </div>
        `).join('');
        
        renderMath();
    } catch (error) {
        console.error('Error loading pending questions:', error);
    }
}

async function loadApprovedQuestions() {
    const subject = document.getElementById('subject-select').value;
    const url = subject ?
        `${API_URL}/admin/approved-questions?subject=${subject}` :
        `${API_URL}/admin/approved-questions`;
    
    try {
        const response = await fetch(url);
        const data = await response.json();
        
        document.getElementById('approved-count').textContent = data.count;
        
        const questionsList = document.getElementById('approved-questions-list');
        
        if (data.count === 0) {
            questionsList.innerHTML = `
                <div style="text-align: center; padding: 60px; color: #666;">
                    <h3>No approved questions yet</h3>
                    <p>Approve pending questions to see them here</p>
                </div>
            `;
            return;
        }
        
        questionsList.innerHTML = data.approved_questions.map(q => `
            <div class="question-card">
                <div class="question-meta">
                    <span class="badge badge-subject">${q.subject}</span>
                    <span class="badge badge-type">${q.question_type}</span>
                    <span class="badge" style="background: #27ae60; color: white;">Approved & Added to CSV</span>
                </div>
                <div class="question-text">${q.question}</div>
                <div class="question-options">
                    <div class="option-item ${q.correct_option === 'A' ? 'correct' : ''}">
                        A. ${q.option_a}
                    </div>
                    <div class="option-item ${q.correct_option === 'B' ? 'correct' : ''}">
                        B. ${q.option_b}
                    </div>
                    <div class="option-item ${q.correct_option === 'C' ? 'correct' : ''}">
                        C. ${q.option_c}
                    </div>
                    <div class="option-item ${q.correct_option === 'D' ? 'correct' : ''}">
                        D. ${q.option_d}
                    </div>
                </div>
                <p style="margin-top: 10px; color: #666; font-size: 0.9em;">
                    ✓ Reviewed by: ${q.reviewed_by || 'Admin'} on ${new Date(q.reviewed_at).toLocaleString()}
                </p>
            </div>
        `).join('');
        
        renderMath();
    } catch (error) {
        console.error('Error loading approved questions:', error);
    }
}

async function verifyBulkAI() {
    if (pendingQuestions.length === 0) {
        alert('No pending questions to verify.');
        return;
    }
    
    if (!confirm(`This will verify all ${pendingQuestions.length} pending questions with AI. Continue?`)) return;
    
    // Trigger verification for each question
    for (const q of pendingQuestions) {
        verifyWithAI(q.id);
        // Small delay to prevent overwhelming the browser/API
        await new Promise(r => setTimeout(r, 1000));
    }
}

async function verifyWithAI(id) {
    const feedbackDiv = document.getElementById(`ai-feedback-${id}`);
    const question = pendingQuestions.find(q => q.id === id);
    
    if (!question) return;

    // Show loading state
    feedbackDiv.style.display = 'block';
    feedbackDiv.innerHTML = `
        <div style="display: flex; align-items: center; gap: 10px; color: #666;">
            <div class="spinner-small"></div>
            <span>AI is analyzing the question...</span>
        </div>
    `;

    try {
        const response = await fetch(`${API_URL}/admin/verify-with-ai`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                question: question.question,
                options: {
                    A: question.option_a,
                    B: question.option_b,
                    C: question.option_c,
                    D: question.option_d
                },
                suggested_answer: question.correct_option
            })
        });

        const result = await response.json();
        
        if (result.success) {
            const data = result.analysis;
            const isMatch = data.is_correct;
            
            let html = `
                <div style="margin-bottom: 10px;">
                    <strong style="color: ${isMatch ? '#2e7d32' : '#c62828'};">
                        ${isMatch ? '⭐ AI confirms this answer is correct!' : '⚠️ AI suggests a different answer!'}
                    </strong>
                </div>
                <div style="font-size: 0.95em; color: #444; margin-bottom: 12px; line-height: 1.5;">
                    ${data.explanation}
                </div>
            `;

            if (!isMatch) {
                html += `
                    <div style="background: #fff3e0; padding: 10px; border-radius: 6px; border: 1px solid #ffe0b2;">
                        <p style="margin: 0 0 8px 0; font-weight: bold; color: #e65100;">AI Suggestion: Option ${data.correct_option}</p>
                        <button class="btn btn-small" onclick="applyAISuggestion(${id}, '${data.correct_option}')" style="background: #ff9800; color: white;">
                            Update answer to ${data.correct_option}
                        </button>
                    </div>
                `;
            }

            feedbackDiv.innerHTML = html;
            renderMath(); // Render LaTeX in explanation
        } else {
            feedbackDiv.innerHTML = `<p style="color: red;">Error: ${result.error}</p>`;
        }
    } catch (error) {
        console.error('AI Verification failed:', error);
        feedbackDiv.innerHTML = `<p style="color: red;">Failed to connect to AI service.</p>`;
    }
}

async function applyAISuggestion(id, correctOption) {
    const question = pendingQuestions.find(q => q.id === id);
    if (!question) return;

    try {
        const response = await fetch(`${API_URL}/admin/edit-question/${id}`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                ...question,
                correct_option: correctOption,
                admin_user: 'admin'
            })
        });

        if (response.ok) {
            loadPendingQuestions(); // Refresh list to show updated correct option
        } else {
            alert('Failed to update question');
        }
    } catch (error) {
        console.error('Update failed:', error);
    }
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

function toggleQuestionSelection(questionId) {
    if (selectedQuestions.has(questionId)) {
        selectedQuestions.delete(questionId);
        document.getElementById(`question-${questionId}`).classList.remove('selected');
    } else {
        selectedQuestions.add(questionId);
        document.getElementById(`question-${questionId}`).classList.add('selected');
    }
}

function selectAll() {
    const checkboxes = document.querySelectorAll('.question-checkbox');
    checkboxes.forEach(cb => {
        cb.checked = true;
        const qId = parseInt(cb.value);
        selectedQuestions.add(qId);
        document.getElementById(`question-${qId}`).classList.add('selected');
    });
}

async function approveQuestion(questionId) {
    if (!confirm('Approve this question and add to main CSV question bank?')) return;
    
    try {
        const response = await fetch(`${API_URL}/admin/approve-question/${questionId}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ admin_user: 'admin' })
        });
        
        const data = await response.json();
        alert('✅ ' + data.message);
        
        loadStats();
        loadPendingQuestions();
    } catch (error) {
        console.error('Error approving question:', error);
        alert('❌ Failed to approve question');
    }
}

async function approveSelected() {
    if (selectedQuestions.size === 0) {
        alert('Please select at least one question');
        return;
    }
    
    if (!confirm(`Approve ${selectedQuestions.size} questions and add to CSV?`)) return;
    
    try {
        const response = await fetch(`${API_URL}/admin/approve-bulk`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                question_ids: Array.from(selectedQuestions),
                admin_user: 'admin'
            })
        });
        
        const data = await response.json();
        alert('✅ ' + data.message);
        
        selectedQuestions.clear();
        loadStats();
        loadPendingQuestions();
    } catch (error) {
        console.error('Error approving questions:', error);
        alert('❌ Failed to approve questions');
    }
}

async function rejectQuestion(questionId) {
    const reason = prompt('Enter reason for rejection:');
    if (!reason) return;
    
    try {
        const response = await fetch(`${API_URL}/admin/reject-question/${questionId}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                admin_user: 'admin',
                reason: reason
            })
        });
        
        const data = await response.json();
        alert('✅ ' + data.message);
        
        loadStats();
        loadPendingQuestions();
    } catch (error) {
        console.error('Error rejecting question:', error);
        alert('❌ Failed to reject question');
    }
}

async function rejectSelected() {
    if (selectedQuestions.size === 0) {
        alert('Please select at least one question');
        return;
    }
    
    const reason = prompt('Enter reason for rejection:');
    if (!reason) return;
    
    for (const qId of selectedQuestions) {
        await rejectQuestion(qId);
    }
    
    selectedQuestions.clear();
}

function editQuestion(questionId) {
    fetch(`${API_URL}/admin/pending-questions`)
        .then(res => res.json())
        .then(data => {
            const question = data.pending_questions.find(q => q.id === questionId);
            if (!question) return;
            
            currentEditQuestionId = questionId;
            
            document.getElementById('edit-type').value = question.question_type;
            document.getElementById('edit-question').value = question.question;
            document.getElementById('edit-option-a').value = question.option_a;
            document.getElementById('edit-option-b').value = question.option_b;
            document.getElementById('edit-option-c').value = question.option_c;
            document.getElementById('edit-option-d').value = question.option_d;
            document.getElementById('edit-correct').value = question.correct_option;
            
            document.getElementById('edit-modal').style.display = 'block';
        });
}

async function saveEdit() {
    if (!currentEditQuestionId) return;
    
    const data = {
        question: document.getElementById('edit-question').value,
        option_a: document.getElementById('edit-option-a').value,
        option_b: document.getElementById('edit-option-b').value,
        option_c: document.getElementById('edit-option-c').value,
        option_d: document.getElementById('edit-option-d').value,
        correct_option: document.getElementById('edit-correct').value,
        question_type: document.getElementById('edit-type').value,
        admin_user: 'admin'
    };
    
    try {
        const response = await fetch(`${API_URL}/admin/edit-question/${currentEditQuestionId}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        });
        
        const result = await response.json();
        alert('✅ ' + result.message);
        
        closeEditModal();
        loadPendingQuestions();
    } catch (error) {
        console.error('Error saving edit:', error);
        alert('❌ Failed to save changes');
    }
}

function showGenerateModal() {
    document.getElementById('generate-modal').style.display = 'block';
}

function closeGenerateModal() {
    document.getElementById('generate-modal').style.display = 'none';
    document.getElementById('generate-status').innerHTML = '';
}

function closeEditModal() {
    document.getElementById('edit-modal').style.display = 'none';
    currentEditQuestionId = null;
}

async function generateQuestions() {
    const subject = document.getElementById('generate-subject').value;
    const statusDiv = document.getElementById('generate-status');
    
    statusDiv.innerHTML = '<p style="color: #667eea;">⏳ Generating questions... This may take up to 60 seconds.</p>';
    
    try {
        const response = await fetch(`${API_URL}/admin/generate/${subject}`, {
            method: 'POST'
        });
        
        const data = await response.json();
        
        if (response.ok) {
            statusDiv.innerHTML = `
                <p style="color: #27ae60;">✅ ${data.message}</p>
                <p>Generated ${data.question_count} questions for review.</p>
            `;
            
            setTimeout(() => {
                closeGenerateModal();
                loadStats();
                loadPendingQuestions();
                // Switch to pending tab automatically
                document.querySelector('.tab-btn[onclick*="pending"]').click();
            }, 2000);
        } else {
            statusDiv.innerHTML = `<p style="color: #ff6b6b;">❌ ${data.error}</p>`;
        }
    } catch (error) {
        console.error('Error generating questions:', error);
        statusDiv.innerHTML = '<p style="color: #ff6b6b;">❌ Failed to generate questions. Please try again.</p>';
    }
}

function switchTab(tab) {
    document.querySelectorAll('.tab-btn').forEach(btn => btn.classList.remove('active'));
    event.target.classList.add('active');
    
    document.querySelectorAll('.tab-content').forEach(content => content.classList.remove('active'));
    
    if (tab === 'pending') {
        document.getElementById('pending-tab').classList.add('active');
        loadPendingQuestions();
    } else {
        document.getElementById('approved-tab').classList.add('active');
        loadApprovedQuestions();
    }
}