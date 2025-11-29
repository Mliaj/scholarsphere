// Authentication JavaScript for Scholarsphere

document.addEventListener('DOMContentLoaded', function() {
    initializeAuthForms();
    initializePasswordValidation();
    initializeStudentIdValidation();
    initializePasswordToggle(); // Call the new password toggle function
});

// Initialize authentication forms
function initializeAuthForms() {
    const loginForm = document.getElementById('loginForm');
    const signupForm = document.getElementById('studentSignupForm');
    
    if (loginForm) {
        loginForm.addEventListener('submit', handleLoginSubmit);
    }
    
    if (signupForm) {
        signupForm.addEventListener('submit', handleSignupSubmit);
    }
}

// Handle login form submission
function handleLoginSubmit(event) {
    const form = event.target;
    const identifier = form.querySelector('input[name="identifier"]').value.trim();
    const password = form.querySelector('input[name="password"]').value;
    
    // Basic validation
    if (!identifier || !password) {
        event.preventDefault();
        showNotification('Please provide your ID/email and password.', 'error');
        return;
    }
    
    // Show loading state
    const submitBtn = form.querySelector('button[type="submit"]');
    if (submitBtn) {
        submitBtn.disabled = true;
        submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Signing in...';
    }
}

// Handle signup form submission
function handleSignupSubmit(event) {
    const form = event.target;
    
    // Validate form
    if (!validateSignupForm(form)) {
        event.preventDefault();
        return;
    }
    
    // Show loading state
    const submitBtn = form.querySelector('button[type="submit"]');
    if (submitBtn) {
        submitBtn.disabled = true;
        submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Creating account...';
    }
}

// Validate signup form
function validateSignupForm(form) {
    const firstName = form.querySelector('input[name="firstName"]').value.trim();
    const lastName = form.querySelector('input[name="lastName"]').value.trim();
    const email = form.querySelector('input[name="email"]').value.trim();
    const studentId = form.querySelector('input[name="studentId"]').value.trim();
    const birthday = form.querySelector('input[name="birthday"]').value;
    const password = form.querySelector('input[name="password"]').value;
    const repeatPassword = form.querySelector('input[name="repeatPassword"]').value;
    
    let isValid = true;
    
    // Check required fields
    if (!firstName) {
        showFieldError(form.querySelector('input[name="firstName"]'), 'First name is required');
        isValid = false;
    }
    
    if (!lastName) {
        showFieldError(form.querySelector('input[name="lastName"]'), 'Last name is required');
        isValid = false;
    }
    
    if (!email) {
        showFieldError(form.querySelector('input[name="email"]'), 'Email is required');
        isValid = false;
    } else if (!isValidEmail(email)) {
        showFieldError(form.querySelector('input[name="email"]'), 'Please enter a valid email address');
        isValid = false;
    }
    
    if (!studentId) {
        showFieldError(form.querySelector('input[name="studentId"]'), 'Student ID is required');
        isValid = false;
    } else if (!isValidStudentId(studentId)) {
        showFieldError(form.querySelector('input[name="studentId"]'), 'Student ID must be exactly 8 digits');
        isValid = false;
    }
    
    if (!birthday) {
        showFieldError(form.querySelector('input[name="birthday"]'), 'Birthday is required');
        isValid = false;
    }
    
    if (!password) {
        showFieldError(form.querySelector('input[name="password"]'), 'Password is required');
        isValid = false;
    } else if (password.length < 8) {
        showFieldError(form.querySelector('input[name="password"]'), 'Password must be at least 8 characters long');
        isValid = false;
    }
    
    if (!repeatPassword) {
        showFieldError(form.querySelector('input[name="repeatPassword"]'), 'Please confirm your password');
        isValid = false;
    } else if (password !== repeatPassword) {
        showFieldError(form.querySelector('input[name="repeatPassword"]'), 'Passwords do not match');
        isValid = false;
    }
    
    return isValid;
}

// Initialize password validation
function initializePasswordValidation() {
    const passwordInputs = document.querySelectorAll('input[type="password"]');
    
    passwordInputs.forEach(input => {
        input.addEventListener('input', function() {
            validatePasswordStrength(this);
        });
    });
}

// Validate password strength
function validatePasswordStrength(input) {
    const password = input.value;
    const strengthIndicator = getOrCreateStrengthIndicator(input);
    
    if (password.length === 0) {
        strengthIndicator.style.display = 'none';
        return;
    }
    
    let strength = 0;
    let feedback = [];
    
    // Length check
    if (password.length >= 8) {
        strength += 1;
    } else {
        feedback.push('At least 8 characters');
    }
    
    // Uppercase check
    if (/[A-Z]/.test(password)) {
        strength += 1;
    } else {
        feedback.push('One uppercase letter');
    }
    
    // Lowercase check
    if (/[a-z]/.test(password)) {
        strength += 1;
    } else {
        feedback.push('One lowercase letter');
    }
    
    // Number check
    if (/\d/.test(password)) {
        strength += 1;
    } else {
        feedback.push('One number');
    }
    
    // Special character check
    if (/[!@#$%^&*(),.?":{}|<>]/.test(password)) {
        strength += 1;
    } else {
        feedback.push('One special character');
    }
    
    // Update strength indicator
    updateStrengthIndicator(strengthIndicator, strength, feedback);
}

// Get or create password strength indicator
function getOrCreateStrengthIndicator(input) {
    // Determine the target parent: if input is in password-input-container, go up one level
    const targetParent = input.parentNode.classList.contains('password-input-container') 
        ? input.parentNode.parentNode 
        : input.parentNode;

    let indicator = targetParent.querySelector('.password-strength');
    
    if (!indicator) {
        indicator = document.createElement('div');
        indicator.className = 'password-strength';
        indicator.style.cssText = `
            margin-top: 0.5rem;
            font-size: 0.875rem;
        `;
        targetParent.appendChild(indicator);
    }
    
    return indicator;
}

// Update password strength indicator
function updateStrengthIndicator(indicator, strength, feedback) {
    const strengthLevels = ['Very Weak', 'Weak', 'Fair', 'Good', 'Strong'];
    const strengthColors = ['#dc3545', '#fd7e14', '#ffc107', '#20c997', '#28a745'];
    
    indicator.innerHTML = `
        <div style="display: flex; align-items: center; gap: 0.5rem;">
            <div style="flex: 1; height: 4px; background: #e9ecef; border-radius: 2px; overflow: hidden;">
                <div style="height: 100%; width: ${(strength / 5) * 100}%; background: ${strengthColors[strength - 1] || '#dc3545'}; transition: all 0.3s;"></div>
            </div>
            <span style="color: ${strengthColors[strength - 1] || '#dc3545'}; font-weight: 500;">
                ${strengthLevels[strength - 1] || 'Very Weak'}
            </span>
        </div>
        ${feedback.length > 0 ? `<div style="margin-top: 0.25rem; color: #6c757d; font-size: 0.8rem;">Missing: ${feedback.join(', ')}</div>` : ''}
    `;
}

// Initialize student ID validation
function initializeStudentIdValidation() {
    const studentIdInput = document.querySelector('input[name="studentId"]');
    
    if (studentIdInput) {
        studentIdInput.addEventListener('input', function() {
            // Only allow numbers
            this.value = this.value.replace(/[^0-9]/g, '');
            
            // Limit to 8 digits
            if (this.value.length > 8) {
                this.value = this.value.slice(0, 8);
            }
        });
        
        studentIdInput.addEventListener('blur', function() {
            if (this.value && !isValidStudentId(this.value)) {
                showFieldError(this, 'Student ID must be exactly 8 digits');
            } else {
                clearFieldError(this);
            }
        });
    }
}

// Validation helper functions
function isValidEmail(email) {
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return emailRegex.test(email);
}

function isValidStudentId(studentId) {
    const studentIdRegex = /^\d{8}$/;
    return studentIdRegex.test(studentId);
}

function showFieldError(input, message) {
    clearFieldError(input);
    
    input.classList.add('is-invalid');
    
    const errorDiv = document.createElement('div');
    errorDiv.className = 'form-error';
    errorDiv.textContent = message;
    
    // Determine insertion point: if wrapped, append to the wrapper's parent
    const targetParent = input.parentNode.classList.contains('password-input-container') 
        ? input.parentNode.parentNode 
        : input.parentNode;
        
    targetParent.appendChild(errorDiv);
}

function clearFieldError(input) {
    input.classList.remove('is-invalid');
    
    const targetParent = input.parentNode.classList.contains('password-input-container') 
        ? input.parentNode.parentNode 
        : input.parentNode;

    const existingError = targetParent.querySelector('.form-error');
    if (existingError) {
        existingError.remove();
    }
}

// Real-time validation
function initializeRealTimeValidation() {
    const inputs = document.querySelectorAll('input[required]');
    
    inputs.forEach(input => {
        input.addEventListener('blur', function() {
            validateField(this);
        });
        
        input.addEventListener('input', function() {
            // Clear error on input
            if (this.classList.contains('is-invalid')) {
                clearFieldError(this);
            }
        });
    });
}

function validateField(input) {
    const value = input.value.trim();
    
    if (!value) {
        showFieldError(input, 'This field is required');
        return false;
    }
    
    // Email validation
    if (input.type === 'email' && !isValidEmail(value)) {
        showFieldError(input, 'Please enter a valid email address');
        return false;
    }
    
    // Student ID validation
    if (input.name === 'studentId' && !isValidStudentId(value)) {
        showFieldError(input, 'Student ID must be exactly 8 digits');
        return false;
    }
    
    clearFieldError(input);
    return true;
}

// Initialize real-time validation when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    initializeRealTimeValidation();
});

// Form submission with AJAX (optional)
function submitFormAjax(form, successCallback, errorCallback) {
    const formData = new FormData(form);
    const url = form.action || window.location.href;
    
    fetch(url, {
        method: 'POST',
        body: formData,
        headers: {
            'X-Requested-With': 'XMLHttpRequest'
        }
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            if (successCallback) successCallback(data);
        } else {
            if (errorCallback) errorCallback(data);
        }
    })
    .catch(error => {
        console.error('Form submission error:', error);
        if (errorCallback) errorCallback({ error: 'Network error occurred' });
    });
}

// Function to toggle password visibility
function initializePasswordToggle() {
    const passwordField = document.getElementById('password');
    const toggleButton = document.getElementById('password-toggle');

    if (passwordField && toggleButton) {
        toggleButton.addEventListener('click', function() {
            // Toggle the type attribute
            const type = passwordField.getAttribute('type') === 'password' ? 'text' : 'password';
            passwordField.setAttribute('type', type);

            // Toggle the eye icon
            const icon = this.querySelector('i');
            if (icon) {
                icon.classList.toggle('fa-eye');
                icon.classList.toggle('fa-eye-slash');
            }
        });
    }
}

