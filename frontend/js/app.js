// Simple but robust API URL determination
let API_URL = '/api';

// If we're on a different port (like VS Code Live Server 5500), we must point to the backend
if (window.location.port !== '5002' && (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1')) {
    API_URL = `${window.location.protocol}//${window.location.hostname}:5002/api`;
}

// Check user identification on load
window.onload = function() {
    console.log('✅ Page loaded, initializing...');
    
    const userId = localStorage.getItem('userId');
    console.log('User ID check:', userId);
    
    if (!userId) {
        console.log('No user ID, showing modal...');
        showUserModal();
    } else {
        console.log('User found:', localStorage.getItem('userName'));
        trackPageVisit('home');
    }
    
    // Check for admin access and show button if allowed
    checkAdminAccess();
    
    // Initialize subject card click handlers
    initializeSubjectCards();
};

function checkAdminAccess() {
    const userEmail = localStorage.getItem('userEmail');
    const adminBtn = document.getElementById('admin-btn');
    const ADMIN_EMAIL = 'bsuganth@gmail.com';
    
    if (adminBtn) {
        if (userEmail === ADMIN_EMAIL) {
            adminBtn.style.display = 'inline-block';
        } else {
            adminBtn.style.display = 'none';
        }
    }

    // Default to database mode if not set
    if (!sessionStorage.getItem('questionSource')) {
        sessionStorage.setItem('questionSource', 'database');
    }
}

function selectMode(mode) {
    console.log('Mode selected:', mode);
    sessionStorage.setItem('questionSource', mode);
    
    // Update UI
    const dbBtn = document.getElementById('db-mode-btn');
    const genaiBtn = document.getElementById('genai-mode-btn');
    
    if (dbBtn && genaiBtn) {
        if (mode === 'database') {
            dbBtn.classList.add('active');
            genaiBtn.classList.remove('active');
        } else {
            genaiBtn.classList.add('active');
            dbBtn.classList.remove('active');
        }
    }
}

function initializeSubjectCards() {
    console.log('Initializing subject card handlers...');
    
    const cards = document.querySelectorAll('.subject-card');
    console.log(`Found ${cards.length} subject cards`);
    
    cards.forEach(card => {
        // Remove any existing click handlers
        card.onclick = null;
        
        // Get subject from onclick attribute or h3 text
        const onclickAttr = card.getAttribute('onclick');
        let subject = '';
        
        if (onclickAttr) {
            // Extract subject from onclick="startTest('Physics')"
            const match = onclickAttr.match(/startTest\(['"](.+?)['"]\)/);
            if (match) {
                subject = match[1];
            }
        }
        
        if (!subject) {
            // Fallback: get from h3 text
            const h3 = card.querySelector('h3');
            if (h3) {
                subject = h3.textContent.replace(/[^\w\s]/g, '').trim();
            }
        }
        
        console.log('Card subject:', subject);
        
        // Add click handler
        card.addEventListener('click', function(e) {
            e.preventDefault();
            console.log('Card clicked:', subject);
            startTest(subject);
        });
        
        // Also keep onclick for direct calls
        card.onclick = function() {
            startTest(subject);
        };
    });
    
    console.log('✅ Subject cards initialized');
}

function checkUserIdentification() {
    const userId = localStorage.getItem('userId');
    if (!userId) {
        showUserModal();
        return false;
    }
    return true;
}

function showUserModal() {
    // Remove any existing modal
    const existingModal = document.getElementById('userModal');
    if (existingModal) {
        existingModal.remove();
    }
    
    const modal = document.createElement('div');
    modal.id = 'userModal';
    modal.style.cssText = `
        display: block;
        position: fixed;
        z-index: 9999;
        left: 0;
        top: 0;
        width: 100%;
        height: 100%;
        background-color: rgba(0, 0, 0, 0.7);
    `;
    
    modal.innerHTML = `
        <div style="background: white; margin: 10% auto; padding: 40px; border-radius: 15px; max-width: 500px; box-shadow: 0 5px 30px rgba(0,0,0,0.3);">
            <h2 style="color: #667eea; margin-bottom: 15px;">👋 Welcome to ICSE MCQ Test!</h2>
            <p style="margin-bottom: 20px;">Please enter your details to continue:</p>
            
            <form id="userForm">
                <div style="margin-bottom: 20px;">
                    <label style="display: block; margin-bottom: 5px; font-weight: 600;">Your Name *</label>
                    <input type="text" 
                           id="userName" 
                           name="userName"
                           required 
                           autocomplete="name"
                           style="width: 100%; padding: 12px; border: 2px solid #ddd; border-radius: 8px; box-sizing: border-box;"
                           placeholder="Enter your full name">
                </div>
                
                <div style="margin-bottom: 20px;">
                    <label style="display: block; margin-bottom: 5px; font-weight: 600;">Email / Roll Number *</label>
                    <input type="text" 
                           id="userEmail" 
                           name="userEmail"
                           required 
                           autocomplete="email"
                           style="width: 100%; padding: 12px; border: 2px solid #ddd; border-radius: 8px; box-sizing: border-box;"
                           placeholder="Enter email or roll number">
                </div>
                
                <button type="submit" style="width: 100%; padding: 15px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; border: none; border-radius: 8px; font-size: 1.1em; font-weight: 600; cursor: pointer;">
                    Continue to Tests
                </button>
            </form>
            
            <div style="margin-top: 15px; padding: 10px; background: #f0f2ff; border-left: 4px solid #667eea; color: #666; font-size: 0.9em;">
                ℹ️ Your information helps us track your progress.
            </div>
        </div>
    `;
    
    document.body.appendChild(modal);
    
    // Add form submit handler
    document.getElementById('userForm').addEventListener('submit', submitUserInfo);
    
    console.log('✅ User modal displayed');
}

function submitUserInfo(event) {
    event.preventDefault();
    
    const userName = document.getElementById('userName').value.trim();
    const userEmail = document.getElementById('userEmail').value.trim();
    
    console.log('Form submitted:', userName, userEmail);
    
    if (!userName || !userEmail) {
        alert('Please fill in all fields');
        return;
    }
    
    const userId = userEmail.toLowerCase().replace(/\s+/g, '_');
    
    localStorage.setItem('userId', userId);
    localStorage.setItem('userName', userName);
    localStorage.setItem('userEmail', userEmail);
    
    console.log('✅ User info saved:', userId, userName);
    
    // Check for admin status immediately after login
    checkAdminAccess();
    
    // Track visit
    trackPageVisit('home');
    
    // Remove modal
    const modal = document.getElementById('userModal');
    if (modal) {
        modal.remove();
    }
    
    // Re-initialize subject cards after modal closes
    console.log('Re-initializing subject cards...');
    setTimeout(() => {
        initializeSubjectCards();
        alert(`Welcome, ${userName}! Click on any subject to start your test.`);
    }, 100);
}

function trackPageVisit(page) {
    const userId = localStorage.getItem('userId');
    const userName = localStorage.getItem('userName');
    
    if (userId) {
        console.log('Tracking page visit:', page);
        fetch(`${API_URL}/track/visit`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                user_id: userId,
                user_name: userName,
                page: page
            })
        })
        .then(response => console.log('Track response:', response.status))
        .catch(err => console.error('Tracking error:', err));
    }
}

function startTest(subject) {
    console.log('🎯 startTest called with:', subject);
    
    const userId = localStorage.getItem('userId');
    const userName = localStorage.getItem('userName');
    
    console.log('User check:', userId ? 'Found' : 'Not found');
    
    if (!userId) {
        console.log('No user ID, showing modal');
        showUserModal();
        return;
    }
    
    // Set session storage
    console.log('Setting sessionStorage...');
    sessionStorage.setItem('currentSubject', subject);
    sessionStorage.setItem('testStartTime', Date.now().toString());
    
    // Verify
    const saved = sessionStorage.getItem('currentSubject');
    console.log('Verification - saved subject:', saved);
    
    if (!saved) {
        alert('Error: Could not save test data. Please try again or refresh the page.');
        return;
    }
    
    // Track test start
    console.log('Tracking test start...');
    fetch(`${API_URL}/track/test-start`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            user_id: userId,
            user_name: userName,
            subject: subject
        })
    })
    .then(response => console.log('Track test start:', response.status))
    .catch(err => console.error('Tracking error:', err));
    
    // Navigate with small delay
    console.log('Navigating to test.html in 200ms...');
    setTimeout(() => {
        console.log('NOW navigating...');
        window.location.href = 'test.html';
    }, 200);
}

function viewHistory() {
    window.location.href = 'history.html';
}

// Make functions globally accessible
window.startTest = startTest;
window.viewHistory = viewHistory;
window.selectMode = selectMode;