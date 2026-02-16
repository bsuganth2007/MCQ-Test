// Simple but robust API URL determination
let API_URL = '/api';

// If we're on a different port (like VS Code Live Server 5500), we must point to the backend
if (window.location.port !== '5002' && (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1')) {
    API_URL = `${window.location.protocol}//${window.location.hostname}:5002/api`;
}

let allHistory = [];
const ADMIN_EMAIL = 'bsuganth@gmail.com';
let isAdminUser = false;

window.onload = function() {
    loadHistory();
};

async function loadHistory() {
    try {
        const userId = localStorage.getItem('userId');
        const userEmail = localStorage.getItem('userEmail');
        isAdminUser = userEmail === ADMIN_EMAIL;

        if (!userId) {
            const historyTableBody = document.getElementById('history-table-body');
            historyTableBody.innerHTML = `
                <tr>
                    <td colspan="7" style="text-align: center; padding: 40px; color: #666;">
                        <h3>User not identified</h3>
                        <p>Please go back and enter your email before viewing history.</p>
                        <button class="btn btn-primary" onclick="goHome()">Back to Home</button>
                    </td>
                </tr>
            `;
            const loadingElement = document.getElementById('loading');
            if (loadingElement) loadingElement.style.display = 'none';
            return;
        }

        const userHeader = document.getElementById('user-header');
        if (userHeader) {
            userHeader.style.display = isAdminUser ? '' : 'none';
        }

        const historyUrl = isAdminUser
            ? `${API_URL}/admin/history`
            : `${API_URL}/history?user_id=${encodeURIComponent(userId)}`;

        const response = await fetch(historyUrl);
        const data = await response.json();
        
        allHistory = data.history || [];
        
        if (allHistory.length === 0) {
            const historyTableBody = document.getElementById('history-table-body');
            historyTableBody.innerHTML = `
                <tr>
                    <td colspan="7" style="text-align: center; padding: 40px; color: #666;">
                        <h3>No test history yet</h3>
                        <p>Take your first test to see results here!</p>
                        <button class="btn btn-primary" onclick="goHome()">Start Test</button>
                    </td>
                </tr>
            `;
            const loadingElement = document.getElementById('loading');
            if (loadingElement) loadingElement.style.display = 'none';
            return;
        }

        // Initialize features
        populateSubjectFilter();
        calculateAndDisplayStats();
        renderHistoryTable(allHistory);
        
        // Hide loading and show container
        const loadingElement = document.getElementById('loading');
        if (loadingElement) loadingElement.style.display = 'none';
        
        const containerElement = document.getElementById('history-container');
        if (containerElement) containerElement.style.display = 'block';
        
    } catch (error) {
        console.error('Error loading history:', error);
        document.getElementById('history-table-body').innerHTML = `
            <tr>
                <td colspan="7" style="text-align: center; padding: 40px; color: #ff6b6b;">
                    Error loading history. Please try again.
                </td>
            </tr>
        `;
    }
}

function populateSubjectFilter() {
    const filter = document.getElementById('subject-filter');
    const subjects = [...new Set(allHistory.map(h => h.subject))];
    
    // Clear existing options except 'All'
    while (filter.options.length > 1) {
        filter.remove(1);
    }
    
    subjects.forEach(subj => {
        const option = document.createElement('option');
        option.value = subj;
        option.textContent = subj;
        filter.appendChild(option);
    });
}

function calculateAndDisplayStats() {
    const statsTableBody = document.getElementById('stats-table-body');
    const subjects = [...new Set(allHistory.map(h => h.subject))];
    
    const stats = subjects.map(subj => {
        const items = allHistory.filter(h => h.subject === subj);
        const scores = items.map(h => parseFloat(h.score));
        const total = items.length;
        const avg = scores.reduce((a, b) => a + b, 0) / total;
        const min = Math.min(...scores);
        const max = Math.max(...scores);
        
        return {
            subject: subj,
            total,
            avg: avg.toFixed(1) + '%',
            min: min.toFixed(1) + '%',
            max: max.toFixed(1) + '%'
        };
    });

    statsTableBody.innerHTML = stats.map(s => `
        <tr>
            <td><strong>${s.subject}</strong></td>
            <td>${s.total}</td>
            <td>${s.avg}</td>
            <td style="color: #ff6b6b; font-weight: bold;">${s.min}</td>
            <td style="color: #27ae60;">${s.max}</td>
        </tr>
    `).join('');
}

function renderHistoryTable(data) {
    const historyTableBody = document.getElementById('history-table-body');
    
    historyTableBody.innerHTML = data.map((test) => {
        // Calculate Trend: Compare with the PREVIOUS test (in chronological order)
        // Since allHistory is sorted DESC (newest first), if there's a test after this one for the same subject, it's the previous one.
        let trendHtml = '<span style="color: #999;">-</span>';
        
        // Find next occurrence (previous in time) of the same subject in the ORIGINAL allHistory list
        const currentIndexInAll = allHistory.findIndex(t => t.id === test.id);
        const previousTest = allHistory.slice(currentIndexInAll + 1).find(t => t.subject === test.subject);
        
        if (previousTest) {
            const currentScore = parseFloat(test.score);
            const prevScore = parseFloat(previousTest.score);
            if (currentScore > prevScore) {
                trendHtml = `<span style="color: #27ae60; font-weight: bold;">▲ +${(currentScore - prevScore).toFixed(1)}%</span>`;
            } else if (currentScore < prevScore) {
                trendHtml = `<span style="color: #ff6b6b; font-weight: bold;">▼ ${(currentScore - prevScore).toFixed(1)}%</span>`;
            } else {
                trendHtml = `<span style="color: #ffb142; font-weight: bold;">● 0%</span>`;
            }
        }

        const userCell = isAdminUser
            ? `<td>${test.user_name || test.user_id || 'Unknown'}</td>`
            : '';

        return `
            <tr>
                <td>${test.test_no}</td>
                <td>${test.date}</td>
                <td>${test.time}</td>
                ${userCell}
                <td>${test.subject}</td>
                <td style="color: ${parseFloat(test.score) >= 60 ? '#27ae60' : '#ff6b6b'}; font-weight: bold;">
                    ${test.score}
                </td>
                <td>${trendHtml}</td>
                <td>
                    <button class="btn btn-small btn-primary" onclick="viewDetails(${test.id})">
                        View Details
                    </button>
                </td>
            </tr>
        `;
    }).join('');
}

function applyFilter() {
    const subject = document.getElementById('subject-filter').value;
    if (subject === 'all') {
        renderHistoryTable(allHistory);
    } else {
        const filtered = allHistory.filter(h => h.subject === subject);
        renderHistoryTable(filtered);
    }
}

function viewDetails(testId) {
    window.location.href = `results.html?id=${testId}`;
}

function goHome() {
    window.location.href = 'index.html';
}

function viewDetails(testId) {
    window.location.href = `results.html?id=${testId}`;
}

function goHome() {
    window.location.href = 'index.html';
}