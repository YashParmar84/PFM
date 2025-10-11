// Personal Finance Management - Main JavaScript

document.addEventListener('DOMContentLoaded', function() {
    // Initialize tooltips
    var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    var tooltipList = tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });

    // Initialize popovers
    var popoverTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="popover"]'));
    var popoverList = popoverTriggerList.map(function (popoverTriggerEl) {
        return new bootstrap.Popover(popoverTriggerEl);
    });

    // Auto-hide alerts after 5 seconds
    setTimeout(function() {
        var alerts = document.querySelectorAll('.alert');
        alerts.forEach(function(alert) {
            var bsAlert = new bootstrap.Alert(alert);
            bsAlert.close();
        });
    }, 5000);

    // Form validation
    var forms = document.querySelectorAll('.needs-validation');
    Array.prototype.slice.call(forms).forEach(function(form) {
        form.addEventListener('submit', function(event) {
            if (!form.checkValidity()) {
                event.preventDefault();
                event.stopPropagation();
            }
            form.classList.add('was-validated');
        }, false);
    });

    // Transaction type change handler
    var transactionTypeSelect = document.getElementById('transaction_type');
    var categorySelect = document.getElementById('category');
    
    if (transactionTypeSelect && categorySelect) {
        transactionTypeSelect.addEventListener('change', function() {
            var selectedType = this.value;
            var options = categorySelect.options;
            
            // Clear current options
            categorySelect.innerHTML = '<option value="">Select Category</option>';
            
            if (selectedType === 'income') {
                // Income categories
                var incomeCategories = [
                    {value: 'salary', text: 'Salary'},
                    {value: 'freelance', text: 'Freelance'},
                    {value: 'investment', text: 'Investment'},
                    {value: 'other', text: 'Other'}
                ];
                
                incomeCategories.forEach(function(category) {
                    var option = document.createElement('option');
                    option.value = category.value;
                    option.textContent = category.text;
                    categorySelect.appendChild(option);
                });
            } else if (selectedType === 'expense') {
                // Expense categories
                var expenseCategories = [
                    {value: 'food', text: 'Food & Dining'},
                    {value: 'transportation', text: 'Transportation'},
                    {value: 'entertainment', text: 'Entertainment'},
                    {value: 'shopping', text: 'Shopping'},
                    {value: 'bills', text: 'Bills & Utilities'},
                    {value: 'healthcare', text: 'Healthcare'},
                    {value: 'education', text: 'Education'},
                    {value: 'other', text: 'Other'}
                ];
                
                expenseCategories.forEach(function(category) {
                    var option = document.createElement('option');
                    option.value = category.value;
                    option.textContent = category.text;
                    categorySelect.appendChild(option);
                });
            }
        });
    }

    // Number formatting for amount inputs
    var amountInputs = document.querySelectorAll('input[type="number"][step="0.01"]');
    amountInputs.forEach(function(input) {
        input.addEventListener('blur', function() {
            var value = parseFloat(this.value);
            if (!isNaN(value)) {
                this.value = value.toFixed(2);
            }
        });
    });

    // Confirm delete actions
    var deleteButtons = document.querySelectorAll('[data-confirm]');
    deleteButtons.forEach(function(button) {
        button.addEventListener('click', function(e) {
            var message = this.getAttribute('data-confirm');
            if (!confirm(message)) {
                e.preventDefault();
            }
        });
    });

    // Smooth scrolling for anchor links
    var anchorLinks = document.querySelectorAll('a[href^="#"]');
    anchorLinks.forEach(function(link) {
        link.addEventListener('click', function(e) {
            e.preventDefault();
            var target = document.querySelector(this.getAttribute('href'));
            if (target) {
                target.scrollIntoView({
                    behavior: 'smooth',
                    block: 'start'
                });
            }
        });
    });

    // Loading states for forms
    var forms = document.querySelectorAll('form');
    forms.forEach(function(form) {
        form.addEventListener('submit', function() {
            var submitButton = form.querySelector('button[type="submit"]');
            if (submitButton) {
                submitButton.classList.add('loading');
                submitButton.disabled = true;
                submitButton.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Processing...';
            }
        });
    });
});

// Utility functions
function formatCurrency(amount) {
    return new Intl.NumberFormat('en-US', {
        style: 'currency',
        currency: 'USD'
    }).format(amount);
}

function formatDate(date) {
    return new Intl.DateTimeFormat('en-US', {
        year: 'numeric',
        month: 'short',
        day: 'numeric'
    }).format(new Date(date));
}

// Chart.js integration (if needed)
function createChart(canvasId, data, type = 'doughnut') {
    var ctx = document.getElementById(canvasId);
    if (ctx) {
        new Chart(ctx, {
            type: type,
            data: data,
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'bottom'
                    }
                }
            }
        });
    }
}
