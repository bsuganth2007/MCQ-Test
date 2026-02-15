window.onload = function() {
    // Simple password protection
    const savedPassword = localStorage.getItem('adminPassword');
    if (savedPassword !== 'admin123') {  // Change this password!
        const password = prompt('Enter admin password:');
        if (password !== 'admin123') {  // Change this password!
            alert('Access denied');
            window.location.href = '/';
            return;
        }
        localStorage.setItem('adminPassword', password);
    }
    
    // Continue with normal loading
    loadStats();
    loadPendingQuestions();
};
const API_URL = 'http://localhost:5001/api';
let currentEditQuestionId = null;
let selectedQuestions = new Set();

// Load stats on page load
window.onload = function() {
    loadStats();
    loadPendingQuestions();
};

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
                            <span class="badge badge-pending">Pending Review</span>
                        </div>
                        <div class="question-text">${q.question}</div>
                        <div class="question-options">
                            <div class="option-item ${q.correct_option === 'A' ? 'correct' : ''}">
                                <strong>A.</strong> ${q.option_a}
                            </div>
                            <div class="option-item ${q.correct_option === 'B' ? 'correct' : ''}">
                                <strong>B.</strong> ${q.option_b}
                            </div>
                            <div class="option-item ${q.correct_option === 'C' ? 'correct' : ''}">
                                <strong>C.</strong> ${q.option_c}
                            </div>
                            <div class="option-item ${q.correct_option === 'D' ? 'correct' : ''}">
                                <strong>D.</strong> ${q.option_d}
                            </div>
                        </div>
                        <div class="question-actions">
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
                    <span class="badge" style="background: #38ef7d; color: white;">Approved & Added to CSV</span>
                </div>
                <div class="question-text">${q.question}</div>
                <div class="question-options">
                    <div class="option-item ${q.correct_option === 'A' ? 'correct' : ''}">
                        <strong>A.</strong> ${q.option_a}
                    </div>
                    <div class="option-item ${q.correct_option === 'B' ? 'correct' : ''}">
                        <strong>B.</strong> ${q.option_b}
                    </div>
                    <div class="option-item ${q.correct_option === 'C' ? 'correct' : ''}">
                        <strong>C.</strong> ${q.option_c}
                    </div>
                    <div class="option-item ${q.correct_option === 'D' ? 'correct' : ''}">
                        <strong>D.</strong> ${q.option_d}
                    </div>
                </div>
                <p style="margin-top: 10px; color: #666; font-size: 0.9em;">
                    ✓ Reviewed by: ${q.reviewed_by || 'Admin'} on ${new Date(q.reviewed_at).toLocaleString()}
                </p>
            </div>
        `).join('');
        
    } catch (error) {
        console.error('Error loading approved questions:', error);
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
                <p style="color: #38ef7d;">✅ ${data.message}</p>
                <p>Generated ${data.question_count} questions for review.</p>
            `;
            
            setTimeout(() => {
                closeGenerateModal();
                loadStats();
                loadPendingQuestions();
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