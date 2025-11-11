// Admin Panel JavaScript

// Confirm delete actions
document.addEventListener('DOMContentLoaded', function() {
    // Add any initialization code here
    console.log('Admin panel loaded');
});

// Auto-submit status changes
document.addEventListener('change', function(e) {
    if (e.target.classList.contains('status-select')) {
        // Status select already has onchange handler in HTML
        // This is just for any additional logic
    }
});

// Search form enhancements
const searchForms = document.querySelectorAll('.search-form');
searchForms.forEach(form => {
    form.addEventListener('submit', function(e) {
        // Form will submit normally
    });
});

