// Home Page Logic
document.addEventListener('DOMContentLoaded', () => {
    const profileBtn = document.getElementById('profileBtn');
    const dropdown = document.getElementById('profileDropdown');

    if (profileBtn && dropdown) {
        profileBtn.addEventListener('click', (e) => {
            e.stopPropagation();
            dropdown.classList.toggle('open');
        });

        document.addEventListener('click', (e) => {
            if (!dropdown.contains(e.target)) {
                dropdown.classList.remove('open');
            }
        });
    }

    const aboutField = document.getElementById('regAbout');
    const aboutCount = document.getElementById('aboutCount');
    if (aboutField && aboutCount) {
        aboutField.addEventListener('input', () => {
            aboutCount.textContent = `${aboutField.value.length} / 500`;
        });
    }

});

// Tab switching logic for Student Dashboard (Global for reliability)
function switchStudentTab(tabId, btn) {
    const targetPanel = document.getElementById(`tab-${tabId}`);
    if (!targetPanel) return;

    // Deactivate all links in the container
    const container = btn.closest('.student-dashboard-tabs');
    if (container) {
        container.querySelectorAll('.tab-link').forEach(l => l.classList.remove('active'));
    }

    // Deactivate all panels
    document.querySelectorAll('.tab-panel').forEach(p => p.classList.remove('active'));

    // Activate current
    btn.classList.add('active');
    targetPanel.classList.add('active');
}

async function submitRegistration() {
    const btn = document.getElementById('registerBtn');
    const data = {
        full_name: document.getElementById('regName').value.trim(),
        mobile: document.getElementById('regMobile').value.trim(),
        gender: document.getElementById('regGender').value,
        dob: document.getElementById('regDob').value,
        college: document.getElementById('regCollege').value.trim(),
        about: document.getElementById('regAbout').value.trim(),
        skills: document.getElementById('regSkills').value.trim(),
        intro_video_url: document.getElementById('regVideo').value.trim(),
    };

    if (!data.full_name || !data.mobile || !data.gender || !data.dob || !data.college) {
        showToast('Please fill all required fields.', 'error');
        return;
    }

    btn.disabled = true;
    btn.innerHTML = '<span class="spinner"></span>Registering...';

    try {
        const res = await apiCall('/api/register/', {
            method: 'POST',
            body: JSON.stringify(data)
        });
        const result = await res.json();
        if (result.success) {
            showToast(result.message, 'success');
            setTimeout(() => window.location.reload(), 1500);
        } else {
            showToast(result.message, 'error');
            btn.disabled = false;
            btn.textContent = 'Register';
        }
    } catch (err) {
        showToast('Network error.', 'error');
        btn.disabled = false;
        btn.textContent = 'Register';
    }
}

async function applyToGig(gigId, btn) {
    const suitabilityNote = prompt('Write a brief on why you are suitable for this gig (minimum 10 characters):');
    if (suitabilityNote === null) return;
    if (!suitabilityNote.trim() || suitabilityNote.trim().length < 10) {
        showToast('Please write at least 10 characters.', 'error');
        return;
    }

    const originalText = btn.textContent;
    btn.disabled = true;
    btn.innerHTML = '<span class="spinner" style="margin-right:0;"></span>';
    try {
        const res = await apiCall('/api/student/apply/', {
            method: 'POST',
            body: JSON.stringify({ gig_id: gigId, suitability_note: suitabilityNote.trim() })
        });
        const result = await res.json();
        if (result.success) {
            showToast(result.message, 'success');
            btn.textContent = 'Applied';
            btn.style.background = 'rgba(255,255,255,0.05)';
            btn.style.color = 'var(--text-muted)';
            btn.style.cursor = 'default';
            setTimeout(() => window.location.reload(), 800);
        } else {
            showToast(result.message, 'error');
            btn.disabled = false;
            btn.textContent = originalText;
        }
    } catch (err) {
        showToast('Network error.', 'error');
        btn.disabled = false;
        btn.textContent = originalText;
    }
}

async function viewEmployerDetails(id) {
    const modal = document.getElementById('employerModal');
    const content = document.getElementById('empModalContent');
    if (!modal || !content) return;
    
    modal.style.display = 'flex';
    content.innerHTML = '<div style="text-align:center; padding:2rem;"><span class="spinner"></span></div>';
    try {
        const res = await apiCall(`/api/employer/details/?id=${id}`);
        const result = await res.json();
        if(result.success) {
            const e = result.data;
            content.innerHTML = `
                <div style="text-align:center; margin-bottom: 2rem;">
                    <div style="width:80px; height:80px; border-radius:50%; margin: 0 auto 1rem; border:2px solid var(--primary); display:flex; align-items:center; justify-content:center; background:rgba(255,255,255,0.03); overflow:hidden;">
                        <span style="font-size:2rem; font-weight:800; color:var(--primary); font-family:'Syne';">${e.company_name.charAt(0)}</span>
                    </div>
                    <h2 style="font-family:'Syne'; color:var(--primary); font-size:1.5rem; margin-bottom:0.3rem;">${e.company_name}</h2>
                    <p style="color:var(--text-muted); font-size: 0.9rem;">${e.location}</p>
                </div>
                <div style="display:grid; gap:0.8rem; background:rgba(255,255,255,0.05); padding:1.2rem; border-radius:16px;">
                    <div style="display:flex; justify-content:space-between; font-size: 0.9rem;"><span style="color:var(--text-muted);">Contact</span><span style="font-weight:600;">${e.full_name}</span></div>
                    <div style="display:flex; justify-content:space-between; font-size: 0.9rem;"><span style="color:var(--text-muted);">Email</span><span style="font-weight:600;">${e.email}</span></div>
                    <div style="display:flex; justify-content:space-between; font-size: 0.9rem;"><span style="color:var(--text-muted);">Phone</span><span style="font-weight:600;">${e.phone}</span></div>
                </div>
            `;
        }
    } catch(err) {
        content.innerHTML = '<p>Error loading employer details.</p>';
    }
}

function openProfileModal() {
    const modal = document.getElementById('profileModal');
    if (modal) modal.style.display = 'flex';
}

function closeProfileModal() {
    const modal = document.getElementById('profileModal');
    if (modal) modal.style.display = 'none';
}

async function updateStudentProfile() {
    const btn = document.getElementById('updateProfileBtn');
    const data = {
        full_name: document.getElementById('editName').value.trim(),
        mobile: document.getElementById('editMobile').value.trim(),
        gender: document.getElementById('editGender').value,
        dob: document.getElementById('editDob').value,
        college: document.getElementById('editCollege').value.trim(),
        about: document.getElementById('editAbout').value.trim(),
        skills: document.getElementById('editSkills').value.trim(),
        intro_video_url: document.getElementById('editVideo').value.trim(),
    };
    
    if (!data.full_name || !data.mobile || !data.gender || !data.dob || !data.college) {
        showToast('Required fields missing.', 'error');
        return;
    }

    btn.disabled = true;
    btn.innerHTML = '<span class="spinner"></span>Saving...';
    try {
        const res = await apiCall('/api/register/', {
            method: 'POST',
            body: JSON.stringify(data)
        });
        const result = await res.json();
        if (result.success) {
            showToast('Updated!', 'success');
            setTimeout(() => window.location.reload(), 1000);
        } else {
            showToast(result.message, 'error');
            btn.disabled = false;
            btn.textContent = 'Save Profile';
        }
    } catch (err) {
        showToast('Error.', 'error');
        btn.disabled = false;
        btn.textContent = 'Save Profile';
    }
}

// Review logic
function openReviewModal(appId, targetEmail, targetName) {
    document.getElementById('reviewAppId').value = appId;
    document.getElementById('reviewTargetName').textContent = targetName;
    document.getElementById('reviewRating').value = 0;
    document.getElementById('reviewComment').value = '';
    
    // Reset stars
    const stars = document.querySelectorAll('.rating-stars span');
    stars.forEach(s => {
        s.style.color = '#6b6b7a'; // var(--muted)
    });
    
    const modal = document.getElementById('reviewModal');
    if (modal) modal.style.display = 'flex';
}

function closeReviewModal() {
    const modal = document.getElementById('reviewModal');
    if (modal) modal.style.display = 'none';
}

function setRating(rating) {
    document.getElementById('reviewRating').value = rating;
    const stars = document.querySelectorAll('.rating-stars span');
    stars.forEach((s, idx) => {
        if (idx < rating) {
            s.style.color = '#c8f73b'; // var(--lime)
        } else {
            s.style.color = '#6b6b7a'; // var(--muted)
        }
    });
}

async function submitReview() {
    const appId = document.getElementById('reviewAppId').value;
    const rating = document.getElementById('reviewRating').value;
    const comment = document.getElementById('reviewComment').value.trim();
    
    if (rating == 0) {
        showToast('Please select a rating.', 'error');
        return;
    }
    
    const btn = document.querySelector('#reviewModal .btn-register');
    if (btn) {
        btn.disabled = true;
        btn.innerHTML = '<span class="spinner"></span>Submitting...';
    }
    
    try {
        const res = await apiCall('/api/reviews/submit/', {
            method: 'POST',
            body: JSON.stringify({
                application_id: appId,
                rating: parseInt(rating),
                comment: comment
            })
        });
        const result = await res.json();
        if (result.success) {
            showToast('Review submitted!', 'success');
            setTimeout(() => window.location.reload(), 1000);
        } else {
            showToast(result.message, 'error');
            if (btn) {
                btn.disabled = false;
                btn.textContent = 'Submit Review';
            }
        }
    } catch (e) {
        showToast('Error submitting review.', 'error');
        if (btn) {
            btn.disabled = false;
            btn.textContent = 'Submit Review';
        }
    }
}
