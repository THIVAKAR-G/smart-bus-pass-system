// Dashboard JavaScript

// Language Switcher
document.getElementById('languageSelect').addEventListener('change', function(e) {
    const lang = e.target.value;
    loadTranslations(lang);
});

function loadTranslations(lang) {
    fetch(`/api/translations/${lang}`)
        .then(response => response.json())
        .then(translations => {
            // Update UI with translations
            document.querySelectorAll('[data-translate]').forEach(element => {
                const key = element.getAttribute('data-translate');
                if (translations[key]) {
                    element.textContent = translations[key];
                }
            });
        })
        .catch(error => console.error('Error loading translations:', error));
}

// Refresh Dashboard Data
document.getElementById('refreshBtn').addEventListener('click', function() {
    showLoading();
    location.reload();
});

function showLoading() {
    const btn = document.getElementById('refreshBtn');
    btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i>';
    btn.disabled = true;
    
    setTimeout(() => {
        btn.innerHTML = '<i class="fas fa-sync-alt"></i>';
        btn.disabled = false;
    }, 1000);
}

// Real-time Notifications
function checkNotifications() {
    // Simulate checking for new notifications
    const hasNewNotifications = Math.random() > 0.7;
    
    if (hasNewNotifications) {
        const badge = document.querySelector('.notification-bell .badge');
        const currentCount = parseInt(badge.textContent);
        badge.textContent = currentCount + 1;
        badge.style.display = 'block';
        
        // Show notification toast
        showNotification('New notification', 'You have a new update');
    }
}

// Check for notifications every 30 seconds
setInterval(checkNotifications, 30000);

// Show notification toast
function showNotification(title, message) {
    // Create toast container if it doesn't exist
    if (!document.getElementById('toastContainer')) {
        const container = document.createElement('div');
        container.id = 'toastContainer';
        container.style.position = 'fixed';
        container.style.top = '20px';
        container.style.right = '20px';
        container.style.zIndex = '9999';
        document.body.appendChild(container);
    }
    
    const toast = document.createElement('div');
    toast.className = 'toast show';
    toast.setAttribute('role', 'alert');
    toast.innerHTML = `
        <div class="toast-header">
            <strong class="me-auto">${title}</strong>
            <small>just now</small>
            <button type="button" class="btn-close" onclick="this.parentElement.parentElement.remove()"></button>
        </div>
        <div class="toast-body">${message}</div>
    `;
    
    document.getElementById('toastContainer').appendChild(toast);
    
    // Auto remove after 5 seconds
    setTimeout(() => {
        toast.remove();
    }, 5000);
}

// Chart Initialization (if you want to add charts)
function initializeCharts() {
    // This would require Chart.js library
    // Example chart for trip statistics
    const ctx = document.getElementById('tripChart');
    if (ctx) {
        new Chart(ctx, {
            type: 'line',
            data: {
                labels: ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'],
                datasets: [{
                    label: 'Trips',
                    data: [12, 19, 3, 5, 2, 3, 9],
                    borderColor: 'rgb(67, 97, 238)',
                    tension: 0.1
                }]
            }
        });
    }
}

// Pass Renewal Countdown
function updateRenewalCountdown() {
    const daysElement = document.querySelector('.stats-details h3');
    if (daysElement && daysElement.textContent !== '0' && daysElement.textContent !== 'No Pass') {
        const days = parseInt(daysElement.textContent);
        
        if (days <= 7) {
            // Show renewal warning
            const warningDiv = document.createElement('div');
            warningDiv.className = 'alert alert-warning alert-dismissible fade show mt-3';
            warningDiv.setAttribute('role', 'alert');
            warningDiv.innerHTML = `
                <i class="fas fa-exclamation-triangle me-2"></i>
                Your pass expires in ${days} days. <a href="/renew-pass" class="alert-link">Renew now</a> to avoid interruption.
                <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
            `;
            
            document.querySelector('.main-content').insertBefore(warningDiv, document.querySelector('.main-content').firstChild);
        }
    }
}

// Initialize on page load
document.addEventListener('DOMContentLoaded', function() {
    updateRenewalCountdown();
    
    // Add smooth scrolling
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function (e) {
            e.preventDefault();
            const target = document.querySelector(this.getAttribute('href'));
            if (target) {
                target.scrollIntoView({ behavior: 'smooth' });
            }
        });
    });
    
    // Initialize tooltips
    const tooltips = document.querySelectorAll('[data-bs-toggle="tooltip"]');
    tooltips.forEach(tooltip => {
        new bootstrap.Tooltip(tooltip);
    });
});

// Export functionality
function exportData(format) {
    const data = {
        trips: [],
        payments: []
    };
    
    // Collect data from tables
    const tripRows = document.querySelectorAll('.table tbody tr');
    tripRows.forEach(row => {
        const cells = row.querySelectorAll('td');
        if (cells.length) {
            data.trips.push({
                date: cells[0].textContent,
                route: cells[1].textContent,
                from: cells[2].textContent,
                to: cells[3].textContent,
                fare: cells[4].textContent,
                status: cells[5].textContent
            });
        }
    });
    
    if (format === 'csv') {
        exportToCSV(data);
    } else if (format === 'pdf') {
        exportToPDF(data);
    }
}

function exportToCSV(data) {
    let csv = 'Date,Route,From,To,Fare,Status\n';
    
    data.trips.forEach(trip => {
        csv += `${trip.date},${trip.route},${trip.from},${trip.to},${trip.fare},${trip.status}\n`;
    });
    
    const blob = new Blob([csv], { type: 'text/csv' });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'trip_history.csv';
    a.click();
}

function exportToPDF(data) {
    // This would require a PDF library
    alert('PDF export feature coming soon!');
}

// Keyboard shortcuts
document.addEventListener('keydown', function(e) {
    // Ctrl + D for dashboard
    if (e.ctrlKey && e.key === 'd') {
        e.preventDefault();
        window.location.href = '/dashboard';
    }
    
    // Ctrl + P for profile
    if (e.ctrlKey && e.key === 'p') {
        e.preventDefault();
        window.location.href = '/profile';
    }
    
    // Ctrl + L for logout
    if (e.ctrlKey && e.key === 'l') {
        e.preventDefault();
        window.location.href = '/logout';
    }
});