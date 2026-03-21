// Employer Dashboard Logic
document.addEventListener('DOMContentLoaded', () => {
    // Attach "Post Gig" button listener if it exists
    const postGigBtn = document.querySelector('button[onclick="openGigModal()"]');
    if (postGigBtn) {
        postGigBtn.removeAttribute('onclick');
        postGigBtn.addEventListener('click', openGigModal);
    }
    setGigDateTimeConstraints('gigDate', ['gigStartTime', 'gigEndTime']);
    setGigDateTimeConstraints('editGigDate', ['editGigStartTime', 'editGigEndTime']);
});

function getNowLocalParts() {
    const now = new Date();
    const pad = (n) => String(n).padStart(2, '0');
    return {
        date: `${now.getFullYear()}-${pad(now.getMonth() + 1)}-${pad(now.getDate())}`,
        time: `${pad(now.getHours())}:${pad(now.getMinutes())}`
    };
}

function setGigDateTimeConstraints(dateInputId, timeInputIds) {
    const dateInput = document.getElementById(dateInputId);
    const timeInputs = (Array.isArray(timeInputIds) ? timeInputIds : [timeInputIds])
        .map(id => document.getElementById(id))
        .filter(el => !!el);
    
    if (!dateInput || timeInputs.length === 0) return;

    const nowParts = getNowLocalParts();
    dateInput.min = nowParts.date;

    const syncTimeMin = () => {
        const parts = getNowLocalParts();
        if (dateInput.value === parts.date) {
            timeInputs.forEach(ti => ti.min = parts.time);
        } else {
            timeInputs.forEach(ti => ti.removeAttribute('min'));
        }
    };

    dateInput.addEventListener('change', syncTimeMin);
    syncTimeMin();
}

function switchTab(tabId, btn) {
    document.querySelectorAll('.tab-content').forEach(el => el.classList.remove('active'));
    document.querySelectorAll('.tab-btn').forEach(el => el.classList.remove('active'));
    const targetContent = document.getElementById('tab-' + tabId);
    if (targetContent) targetContent.classList.add('active');
    if (btn) btn.classList.add('active');
}

async function saveEmpProfile() {
    const data = {
        full_name: document.getElementById('empName').value.trim(),
        phone: document.getElementById('empPhone').value.trim(),
        company_name: document.getElementById('empCompany').value.trim(),
        location: document.getElementById('empLocation').value.trim(),
    };

    if (!data.full_name || !data.phone || !data.company_name) {
        showToast('Required fields missing.', 'error');
        return;
    }

    try {
        const res = await apiCall('/api/register-employer/', {
            method:'POST',
            body: JSON.stringify(data)
        });
        const resData = await res.json();
        if(resData.success) {
            showToast('Profile saved!', 'success');
            setTimeout(() => window.location.reload(), 1000);
        } else {
            showToast(resData.message, 'error');
        }
    } catch(e) {
        showToast('Error saving profile.', 'error');
    }
}

async function updateEmpProfile() {
    const data = {
        full_name: document.getElementById('editName').value.trim(),
        phone: document.getElementById('editPhone').value.trim(),
        company_name: document.getElementById('editCompany').value.trim(),
        location: document.getElementById('editLocation').value.trim(),
    };
    try {
        const res = await apiCall('/api/register-employer/', {
            method:'POST',
            body: JSON.stringify(data)
        });
        const resData = await res.json();
        if(resData.success) {
            showToast('Profile updated!', 'success');
            setTimeout(() => window.location.reload(), 1000);
        } else {
            showToast(resData.message, 'error');
        }
    } catch(e) {
        showToast('Error updating profile.', 'error');
    }
}

function openGigModal() {
    const modal = document.getElementById('gigModal');
    if (modal) {
        const submitBtn = document.querySelector('#gigModal .btn-create');
        if (submitBtn) submitBtn.textContent = 'Post Gig';
        setGigDateTimeConstraints('gigDate', ['gigStartTime', 'gigEndTime']);
        modal.classList.add('active');
        modal.style.display = 'flex'; // Force display as fallback
    }
}

function closeGigModal() {
    const modal = document.getElementById('gigModal');
    if (modal) {
        modal.classList.remove('active');
        modal.style.display = 'none';
    }
}

async function submitGig() {
    const btn = document.querySelector('#gigModal .btn-create');
    const formData = new FormData();
    formData.append('title', document.getElementById('gigTitle').value.trim());
    formData.append('description', document.getElementById('gigDesc').value.trim());
    formData.append('date', document.getElementById('gigDate').value);
    formData.append('start_time', document.getElementById('gigStartTime').value);
    formData.append('end_time', document.getElementById('gigEndTime').value);
    formData.append('earnings', document.getElementById('gigEarnings').value.trim());
    formData.append('status', document.getElementById('gigStatus').value);
    
    const imageFile = document.getElementById('gigImage').files[0];
    if (imageFile) {
        formData.append('image', imageFile);
    }

    if (!formData.get('title') || !formData.get('description') || !formData.get('date') || !formData.get('start_time') || !formData.get('end_time') || !formData.get('earnings')) {
        showToast('Please fill all gig details.', 'error');
        return;
    }

    if (btn) {
        btn.disabled = true;
        btn.innerHTML = '<span class="spinner"></span>Posting...';
    }

    try {
        const res = await apiCall('/api/post-gig/', {
            method:'POST',
            body: formData // FormData automatically sets multipart/form-data
        });
        const resData = await res.json();
        if(resData.success) {
            showToast(resData.message || 'Gig posted successfully!', 'success');
            setTimeout(() => window.location.reload(), 1000);
        } else {
            showToast(resData.message, 'error');
            if (btn) {
                btn.disabled = false;
                btn.textContent = 'Post Gig';
            }
        }
    } catch(e) {
        showToast('Error posting gig.', 'error');
        if (btn) {
            btn.disabled = false;
            btn.textContent = 'Post Gig';
        }
    }
}

async function openEditModal(id) {
    try {
        const res = await apiCall(`/api/employer/get-gig/?id=${id}`);
        const result = await res.json();
        if(result.success) {
            const g = result.data;
            document.getElementById('editGigId').value = g.id;
            document.getElementById('editGigTitle').value = g.title;
            document.getElementById('editGigDesc').value = g.description;
            document.getElementById('editGigDate').value = g.date;
            document.getElementById('editGigStartTime').value = g.start_time;
            document.getElementById('editGigEndTime').value = g.end_time;
            document.getElementById('editGigEarnings').value = g.earnings;
            document.getElementById('editGigStatus').value = g.status;
            document.getElementById('editGigMode').value = 'edit';
            const editBtn = document.querySelector('#editGigModal .btn-create');
            if (editBtn) editBtn.textContent = 'Update';
            setGigDateTimeConstraints('editGigDate', ['editGigStartTime', 'editGigEndTime']);
            
            // Handle image preview
            const preview = document.getElementById('editGigPreview');
            const previewImg = preview ? preview.querySelector('img') : null;
            if (preview && previewImg) {
                if (g.image_url) {
                    previewImg.src = g.image_url;
                    preview.style.display = 'block';
                } else {
                    preview.style.display = 'none';
                }
            }

            const modal = document.getElementById('editGigModal');
            if (modal) {
                modal.classList.add('active');
                modal.style.display = 'flex';
            }
        } else {
            showToast(result.message, 'error');
        }
    } catch(e) {
        showToast('Error loading gig details.', 'error');
    }
}

async function openReuseModal(id) {
    await openEditModal(id);
    const statusField = document.getElementById('editGigStatus');
    const editBtn = document.querySelector('#editGigModal .btn-create');
    const modeField = document.getElementById('editGigMode');
    if (statusField) statusField.value = 'ACTIVE';
    if (modeField) modeField.value = 'reuse';
    if (editBtn) editBtn.textContent = 'Reuse Gig';
}

function closeEditModal() {
    const modal = document.getElementById('editGigModal');
    if (modal) {
        modal.classList.remove('active');
        modal.style.display = 'none';
    }
}

async function submitEditGig() {
    const btn = document.querySelector('#editGigModal .btn-create');
    const formData = new FormData();
    formData.append('gig_id', document.getElementById('editGigId').value);
    formData.append('mode', document.getElementById('editGigMode').value || 'edit');
    formData.append('title', document.getElementById('editGigTitle').value.trim());
    formData.append('description', document.getElementById('editGigDesc').value.trim());
    formData.append('date', document.getElementById('editGigDate').value);
    formData.append('start_time', document.getElementById('editGigStartTime').value);
    formData.append('end_time', document.getElementById('editGigEndTime').value);
    formData.append('earnings', document.getElementById('editGigEarnings').value.trim());
    formData.append('status', document.getElementById('editGigStatus').value);

    const imageFile = document.getElementById('editGigImage').files[0];
    if (imageFile) {
        formData.append('image', imageFile);
    }

    if (!formData.get('title') || !formData.get('description') || !formData.get('date') || !formData.get('start_time') || !formData.get('end_time') || !formData.get('earnings')) {
        showToast('Please fill all required fields.', 'error');
        return;
    }

    if (btn) {
        btn.disabled = true;
        btn.innerHTML = '<span class="spinner"></span>Updating...';
    }

    try {
        const res = await apiCall('/api/employer/update-gig/', {
            method:'POST',
            body: formData
        });
        const resData = await res.json();
        if(resData.success) {
            showToast(resData.message || 'Gig updated successfully!', 'success');
            setTimeout(() => window.location.reload(), 1000);
        } else {
            showToast(resData.message, 'error');
            if (btn) {
                btn.disabled = false;
                btn.textContent = 'Update';
            }
        }
    } catch(e) {
        showToast('Error updating gig.', 'error');
        if (btn) {
            btn.disabled = false;
            btn.textContent = 'Update';
        }
    }
}

async function manageGig(id, action) {
    if(!confirm('Are you sure you want to ' + action + ' this gig?')) return;
    try {
        const res = await apiCall('/api/employer/manage-gig/', {
            method:'POST',
            body: JSON.stringify({ gig_id: id, action: action })
        });
        const resData = await res.json();
        if(resData.success) {
            showToast(resData.message || 'Action completed!', 'success');
            setTimeout(() => window.location.reload(), 1000);
        } else {
            showToast(resData.message, 'error');
        }
    } catch(e) {
        showToast('Error performing action.', 'error');
    }
}

async function manageApp(id, status) {
    try {
        const res = await apiCall('/api/employer/manage-application/', {
            method:'POST',
            body: JSON.stringify({ application_id: id, action: status })
        });
        const resData = await res.json();
        if(resData.success) {
            showToast('Application updated!', 'success');
            setTimeout(() => window.location.reload(), 1000);
        } else {
            showToast(resData.message, 'error');
        }
    } catch(e) {
        showToast('Error updating application.', 'error');
    }
}

async function viewStudent(id) {
    const modal = document.getElementById('studentModal');
    const body = document.getElementById('sBody');
    if (!modal || !body) return;
    
    modal.classList.add('active');
    modal.style.display = 'flex';
    body.innerHTML = '<div style="text-align:center; padding:2rem;"><span class="spinner"></span></div>';
    try {
        const res = await apiCall(`/api/admin/student/?id=${id}`);
        const result = await res.json();
        if(result.success) {
            const s = result.data;
            const nameEl = document.getElementById('sName');
            if (nameEl) nameEl.textContent = s.full_name;
            body.innerHTML = `
                <div style="text-align:center; margin-bottom:1.5rem;">
                    <div style="width:100px; height:100px; border-radius:50%; border:2px solid var(--primary); background:var(--surface); display:flex; align-items:center; justify-content:center; font-weight:900; font-size:2.2rem; color:var(--primary); font-family:'Syne'; margin:0 auto;">
                        ${(s.full_name || 'S').charAt(0).toUpperCase()}
                    </div>
                </div>
                <div style="display:grid; gap:0.8rem;">
                    <p><strong>College:</strong> ${s.college || 'N/A'}</p>
                    <p><strong>Email:</strong> ${s.email}</p>
                    <p><strong>Phone:</strong> ${s.mobile}</p>
                    <p><strong>About:</strong> ${s.about || 'N/A'}</p>
                    <p><strong>Skills:</strong> ${s.skills || 'N/A'}</p>
                    ${s.intro_video_url ? `<p><strong>Intro Video:</strong> <a href="${s.intro_video_url}" target="_blank" style="color:var(--primary);">Watch Video -&gt;</a></p>` : ''}
                </div>
            `;
        } else {
            body.innerHTML = `<p>${result.message}</p>`;
        }
    } catch(e) {
        body.innerHTML = '<p>Error loading student details.</p>';
    }
}

function closeStudentModal() {
    const modal = document.getElementById('studentModal');
    if (modal) {
        modal.classList.remove('active');
        modal.style.display = 'none';
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
    stars.forEach(s => s.style.color = 'var(--text-muted)');
    
    const modal = document.getElementById('reviewModal');
    if (modal) {
        modal.classList.add('active');
        modal.style.display = 'flex';
    }
}

function closeReviewModal() {
    const modal = document.getElementById('reviewModal');
    if (modal) {
        modal.classList.remove('active');
        modal.style.display = 'none';
    }
}

function setRating(rating) {
    document.getElementById('reviewRating').value = rating;
    const stars = document.querySelectorAll('.rating-stars span');
    stars.forEach((s, idx) => {
        if (idx < rating) {
            s.style.color = 'var(--primary)';
        } else {
            s.style.color = 'var(--text-muted)';
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
    
    const btn = document.querySelector('#reviewModal .btn-create');
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
