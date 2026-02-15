const API_URL = window.location.origin + '/api';

window.onload = function() {
    loadHistory();
};

async function loadHistory() {
    try {
        const response = await fetch(`${API_URL}/history`);
        const data = await response.json();
        
        const historyTableBody = document.getElementById('history-table-body');
        
        if (!data.history || data.history.length === 0) {
            historyTableBody.innerHTML = `
                <tr>
                    <td colspan="6" style="text-align: center; padding: 40px; color: #666;">
                        <h3>No test history yet</h3>
                        <p>Take your first test to see results here!</p>
                        <button class="btn btn-primary" onclick="goHome()">Start Test</button>
                    </td>
                </tr>
            `;
            return;
        }
        
        historyTableBody.innerHTML = data.history.map(test => `
            <tr>
                <td>${test.test_no}</td>
                <td>${test.date}</td>
                <td>${test.time}</td>
                <td>${test.subject}</td>
                <td style="color: ${parseFloat(test.score) >= 60 ? '#38ef7d' : '#ff6b6b'}; font-weight: bold;">
                    ${test.score}
                </td>
                <td>
                    <button class="btn btn-small btn-primary" onclick="viewDetails(${test.id})">
                        View Details
                    </button>
                </td>
            </tr>
        `).join('');
        
    } catch (error) {
        console.error('Error loading history:', error);
        document.getElementById('history-table-body').innerHTML = `
            <tr>
                <td colspan="6" style="text-align: center; padding: 40px; color: #ff6b6b;">
                    Error loading history. Please try again.
                </td>
            </tr>
        `;
    }
}

function viewDetails(testId) {
    window.location.href = `results.html?testId=${testId}`;
}

function goHome() {
    window.location.href = 'index.html';
}