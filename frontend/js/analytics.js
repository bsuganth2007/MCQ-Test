// Simple but robust API URL determination
let API_URL = '/api';

// If we're on a different port (like VS Code Live Server 5500), we must point to the backend
if (window.location.port !== '5002' && (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1')) {
    API_URL = `${window.location.protocol}//${window.location.hostname}:5002/api`;
}

window.onload = function() {
    loadAnalytics();
    loadUsers();
};

async function loadAnalytics() {
    try {
        const response = await fetch(`${API_URL}/admin/analytics`);
        const data = await response.json();
        
        const statsGrid = document.getElementById('overview-stats');
        statsGrid.innerHTML = `
            <tr>
                <td style="font-weight: 800; color: #2d3436; font-size: 1.25em;">${data.overview.total_users}</td>
                <td style="font-weight: 800; color: #2d3436; font-size: 1.25em;">${data.overview.total_visits}</td>
                <td style="font-weight: 800; color: #2d3436; font-size: 1.25em;">${data.overview.total_tests}</td>
                <td style="font-weight: 800; color: #00b894; font-size: 1.25em;">${data.overview.avg_score.toFixed(1)}%</td>
                <td style="font-weight: 800; color: #0984e3; font-size: 1.25em;">${data.overview.active_users_24h}</td>
            </tr>
        `;
    } catch (error) {
        console.error('Error loading analytics:', error);
    }
}

async function loadUsers() {
    try {
        const response = await fetch(`${API_URL}/admin/users`);
        const data = await response.json();
        
        const usersList = document.getElementById('users-list');
        
        if (data.count === 0) {
            usersList.innerHTML = '<tr><td colspan="7" style="text-align: center;">No users tracked yet</td></tr>';
            return;
        }
        
        usersList.innerHTML = data.users.map(user => `
            <tr>
                <td>${user.user_id}</td>
                <td>${user.user_name}</td>
                <td>${new Date(user.first_visit).toLocaleString()}</td>
                <td>${new Date(user.last_visit).toLocaleString()}</td>
                <td>${user.total_visits}</td>
                <td>${user.total_tests}</td>
                <td>
                    <button class="btn btn-small" onclick="viewUserDetails('${user.user_id}')">
                        View Details
                    </button>
                </td>
            </tr>
        `).join('');
    } catch (error) {
        console.error('Error loading users:', error);
    }
}

async function viewUserDetails(userId) {
    try {
        const response = await fetch(`${API_URL}/admin/user-stats/${userId}`);
        const data = await response.json();
        
        let details = `
User: ${data.user_info.user_name}
ID: ${data.user_info.user_id}
First Visit: ${new Date(data.user_info.first_visit).toLocaleString()}
Last Visit: ${new Date(data.user_info.last_visit).toLocaleString()}
Total Visits: ${data.user_info.total_visits}
Total Tests: ${data.user_info.total_tests}

Subject Performance:
${data.subject_stats.map(s => `- ${s.subject}: ${s.attempts} tests, Avg: ${s.avg_score}%, Best: ${s.best_score}%`).join('\n')}
        `;
        
        alert(details);
    } catch (error) {
        console.error('Error loading user details:', error);
    }
}

async function exportUsers() {
    try {
        const response = await fetch(`${API_URL}/admin/users`);
        const data = await response.json();
        
        let csv = 'User ID,Name,First Visit,Last Visit,Total Visits,Total Tests\n';
        data.users.forEach(user => {
            csv += `"${user.user_id}","${user.user_name}","${user.first_visit}","${user.last_visit}",${user.total_visits},${user.total_tests}\n`;
        });
        
        const blob = new Blob([csv], { type: 'text/csv' });
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `user-analytics-${new Date().toISOString().split('T')[0]}.csv`;
        a.click();
    } catch (error) {
        console.error('Error exporting users:', error);
    }
}