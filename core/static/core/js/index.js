// Index Page Logic
document.addEventListener('DOMContentLoaded', () => {
    const loginModal = document.getElementById('loginModal');
    const closeModalBtn = document.getElementById('closeModal');

    document.querySelectorAll('.btn-login').forEach(btn => {
        btn.addEventListener('click', (e) => {
            if (btn.id === 'loginHeader' || btn.classList.contains('reveal')) {
                e.preventDefault();
                if (loginModal) {
                    loginModal.classList.add('active');
                    document.body.style.overflow = 'hidden';
                }
            }
        });
    });

    if (closeModalBtn) {
        closeModalBtn.addEventListener('click', () => {
            loginModal.classList.remove('active');
            document.body.style.overflow = 'auto';
        });
    }

    window.addEventListener('click', (e) => {
        if (e.target === loginModal) {
            loginModal.classList.remove('active');
            document.body.style.overflow = 'auto';
        }
    });

    // Intersection Observer for scroll animations
    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.classList.add('reveal');
            }
        });
    }, { threshold: 0.1 });

    document.querySelectorAll('.gig-full-card, .gig-card, .feature-item').forEach(el => {
        el.style.opacity = '0';
        observer.observe(el);
    });

    // Browse gigs filter toggle (UI-only)
    document.querySelectorAll('.filter-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
        });
    });
});

// Authentication Modal Functions
async function modalSendOTP() {
    const emailInput = document.getElementById('modalEmailInput');
    const email = emailInput.value.trim();
    const btn = document.getElementById('modalSendOtpBtn');

    if (!email || !email.includes('@')) {
        showToast('Please enter a valid email address.', 'error');
        return;
    }

    btn.disabled = true;
    btn.innerHTML = '<span class="spinner"></span>Sending...';

    try {
        const res = await apiCall('/api/send-otp/', {
            method: 'POST',
            body: JSON.stringify({ email })
        });
        const data = await res.json();

        if (data.success) {
            showToast(data.message, 'success');
            document.getElementById('modalOtpSection').classList.add('active');
            document.getElementById('modalSentEmailDisplay').textContent = email;
            emailInput.disabled = true;
            btn.textContent = 'OTP Sent ✓';
            const firstInput = document.querySelectorAll('#modalOtpInputs .otp-input')[0];
            if (firstInput) firstInput.focus();
            startModalResendCooldown();
        } else {
            showToast(data.message, 'error');
            btn.disabled = false;
            btn.textContent = 'Send OTP';
        }
    } catch (err) {
        showToast('Network error. Please try again.', 'error');
        btn.disabled = false;
        btn.textContent = 'Send OTP';
    }
}

async function modalVerifyOTP() {
    const inputs = document.querySelectorAll('#modalOtpInputs .otp-input');
    let otp = '';
    inputs.forEach(inp => otp += inp.value);

    if (otp.length !== 6) {
        showToast('Please enter the complete 6-digit OTP.', 'error');
        return;
    }

    const btn = document.getElementById('modalLoginBtn');
    btn.disabled = true;
    btn.innerHTML = '<span class="spinner"></span>Verifying...';

    try {
        const res = await apiCall('/api/verify-otp/', {
            method: 'POST',
            body: JSON.stringify({ otp })
        });
        const data = await res.json();

        if (data.success) {
            showToast(data.message, 'success');
            btn.textContent = 'Success ✓';
            setTimeout(() => {
                window.location.href = data.redirect || '/home/';
            }, 1000);
        } else {
            showToast(data.message, 'error');
            btn.disabled = false;
            btn.textContent = 'Login';
            inputs.forEach(inp => inp.value = '');
            if (inputs[0]) inputs[0].focus();
        }
    } catch (err) {
        showToast('Network error. Please try again.', 'error');
        btn.disabled = false;
        btn.textContent = 'Login';
    }
}

async function modalResendOTP() {
    const btn = document.getElementById('modalResendBtn');
    if (!btn || btn.classList.contains('disabled')) return;

    btn.classList.add('disabled');
    btn.textContent = 'Sending...';

    try {
        const res = await apiCall('/api/resend-otp/', {
            method: 'POST'
        });
        const data = await res.json();
        showToast(data.message, data.success ? 'success' : 'error');

        if (data.success) {
            document.querySelectorAll('#modalOtpInputs .otp-input').forEach(inp => inp.value = '');
            const firstInput = document.querySelectorAll('#modalOtpInputs .otp-input')[0];
            if (firstInput) firstInput.focus();
        }
    } catch (err) {
        showToast('Network error. Please try again.', 'error');
    }
    startModalResendCooldown();
}

function startModalResendCooldown() {
    const btn = document.getElementById('modalResendBtn');
    if (!btn) return;
    let seconds = 30;
    btn.classList.add('disabled');
    btn.textContent = `Resend OTP (${seconds}s)`;

    const interval = setInterval(() => {
        seconds--;
        btn.textContent = `Resend OTP (${seconds}s)`;
        if (seconds <= 0) {
            clearInterval(interval);
            btn.classList.remove('disabled');
            btn.textContent = 'Resend OTP';
        }
    }, 1000);
}

// OTP Input Handling
document.addEventListener('DOMContentLoaded', () => {
    const modalOtpInputsList = document.querySelectorAll('#modalOtpInputs .otp-input');
    modalOtpInputsList.forEach((input, index) => {
        input.addEventListener('input', (e) => {
            e.target.value = e.target.value.replace(/[^0-9]/g, '');
            if (e.target.value.length === 1 && index < modalOtpInputsList.length - 1) {
                modalOtpInputsList[index + 1].focus();
            }
        });

        input.addEventListener('keydown', (e) => {
            if (e.key === 'Backspace' && e.target.value.length === 0 && index > 0) {
                modalOtpInputsList[index - 1].focus();
            }
            if (e.key === 'Enter') modalVerifyOTP();
        });

        input.addEventListener('paste', (e) => {
            e.preventDefault();
            const pasteData = (e.clipboardData || window.clipboardData).getData('text').replace(/[^0-9]/g, '');
            if (pasteData.length >= 6) {
                for (let i = 0; i < 6; i++) {
                    if (modalOtpInputsList[i]) modalOtpInputsList[i].value = pasteData[i] || '';
                }
                if (modalOtpInputsList[5]) modalOtpInputsList[5].focus();
            }
        });
    });

    const emailInput = document.getElementById('modalEmailInput');
    if (emailInput) {
        emailInput.addEventListener('keydown', (e) => {
            if (e.key === 'Enter') modalSendOTP();
        });
    }
});
