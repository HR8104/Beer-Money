// Login Page Logic
async function sendOTP() {
    const emailInput = document.getElementById('emailInput');
    const email = emailInput.value.trim();
    const btn = document.getElementById('sendOtpBtn');

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
            document.getElementById('otpSection').classList.add('active');
            document.getElementById('sentEmailDisplay').textContent = email;
            emailInput.disabled = true;
            btn.textContent = 'OTP Sent ✓';
            const firstInput = document.querySelectorAll('.otp-input')[0];
            if (firstInput) firstInput.focus();
            startResendCooldown();
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

async function verifyOTP() {
    const inputs = document.querySelectorAll('.otp-input');
    let otp = '';
    inputs.forEach(inp => otp += inp.value);

    if (otp.length !== 6) {
        showToast('Please enter the complete 6-digit OTP.', 'error');
        return;
    }

    const btn = document.getElementById('loginBtn');
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

async function resendOTP() {
    const btn = document.getElementById('resendBtn');
    if (!btn || btn.classList.contains('disabled')) return;

    btn.classList.add('disabled');
    btn.textContent = 'Sending...';

    try {
        const res = await apiCall('/api/resend-otp/', {
            method: 'POST'
        });
        const data = await res.json();

        if (data.success) {
            showToast(data.message, 'success');
            document.querySelectorAll('.otp-input').forEach(inp => inp.value = '');
            const firstInput = document.querySelectorAll('.otp-input')[0];
            if (firstInput) firstInput.focus();
        } else {
            showToast(data.message, 'error');
        }
    } catch (err) {
        showToast('Network error. Please try again.', 'error');
    }

    startResendCooldown();
}

function startResendCooldown() {
    const btn = document.getElementById('resendBtn');
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

document.addEventListener('DOMContentLoaded', () => {
    const otpInputsList = document.querySelectorAll('.otp-input');

    otpInputsList.forEach((input, index) => {
        input.addEventListener('input', (e) => {
            e.target.value = e.target.value.replace(/[^0-9]/g, '');
            if (e.target.value.length === 1 && index < otpInputsList.length - 1) {
                otpInputsList[index + 1].focus();
            }
        });

        input.addEventListener('keydown', (e) => {
            if (e.key === 'Backspace' && e.target.value.length === 0 && index > 0) {
                otpInputsList[index - 1].focus();
            }
            if (e.key === 'Enter') verifyOTP();
        });

        input.addEventListener('paste', (e) => {
            e.preventDefault();
            const pasteData = (e.clipboardData || window.clipboardData).getData('text').replace(/[^0-9]/g, '');
            if (pasteData.length >= 6) {
                for (let i = 0; i < 6; i++) {
                    if (otpInputsList[i]) otpInputsList[i].value = pasteData[i] || '';
                }
                if (otpInputsList[5]) otpInputsList[5].focus();
            }
        });
    });

    const emailInput = document.getElementById('emailInput');
    if (emailInput) {
        emailInput.addEventListener('keydown', (e) => {
            if (e.key === 'Enter') sendOTP();
        });
    }
});
