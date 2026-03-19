// Admin Dashboard Logic
function switchTab(tabId, el) {
    document.querySelectorAll('.tab-content').forEach(el => el.classList.remove('active'));
    document.querySelectorAll('.stat-item').forEach(el => el.classList.remove('selected'));
    const target = document.getElementById('tab-' + tabId);
    if (target) target.classList.add('active');
    if (el) el.classList.add('selected');
}

function openStaffModal() {
    const modal = document.getElementById('staffModal');
    if (modal) modal.classList.add('active');
}

function closeStaffModal() {
    const modal = document.getElementById('staffModal');
    if (modal) modal.classList.remove('active');
}

async function addStaff() {
    const email = document.getElementById('staffEmail').value.trim();
    const role = document.getElementById('staffRole').value;
    if(!email) {
        showToast('Email required', 'error');
        return;
    }
    try {
        const res = await apiCall('/api/admin/add-staff/', {
            method: 'POST',
            body: JSON.stringify({email, role})
        });
        const data = await res.json();
        if(data.success) {
            showToast(data.message);
            setTimeout(() => window.location.reload(), 1000);
        } else {
            showToast(data.message, 'error');
        }
    } catch(e) {
        showToast('Error adding staff member.', 'error');
    }
}

async function deleteStaff(email) {
    if(!confirm('Delete all details for ' + email + '? This cannot be undone.')) return;
    try {
        const res = await apiCall('/api/admin/delete-staff/', {
            method: 'POST',
            body: JSON.stringify({email})
        });
        const data = await res.json();
        if(data.success) {
            showToast(data.message);
            setTimeout(() => window.location.reload(), 1000);
        } else {
            showToast(data.message, 'error');
        }
    } catch(e) {
        showToast('Error deleting staff details.', 'error');
    }
}

async function toggleFreeze(email, btnId) {
    if(!confirm('Freeze/unfreeze account for ' + email + '?')) return;
    try {
        const res = await apiCall('/api/admin/toggle-freeze/', {
            method: 'POST',
            body: JSON.stringify({email})
        });
        const data = await res.json();
        if(data.success) {
            showToast(data.message);
            const btn = document.getElementById(btnId);
            if (btn) {
                if (data.is_frozen) {
                    btn.textContent = 'Unfreeze';
                    btn.classList.add('frozen');
                } else {
                    btn.textContent = 'Freeze';
                    btn.classList.remove('frozen');
                }
            }
            setTimeout(() => window.location.reload(), 800);
        } else {
            showToast(data.message, 'error');
        }
    } catch(e) {
        showToast('Error toggling freeze status.', 'error');
    }
}

async function toggleBan(id) {
    try {
        const res = await apiCall('/api/admin/toggle-ban/', {
            method: 'POST',
            body: JSON.stringify({student_id: id})
        });
        const data = await res.json();
        if(data.success) {
            showToast(data.message);
            const btn = document.getElementById(`banBtn-${id}`);
            if (btn) {
                if(data.is_banned) {
                    btn.textContent = 'Unban';
                    btn.classList.add('banned');
                } else {
                    btn.textContent = 'Ban';
                    btn.classList.remove('banned');
                }
            }
            setTimeout(() => window.location.reload(), 800);
        } else {
            showToast(data.message, 'error');
        }
    } catch(e) {
        showToast('Error toggling ban.', 'error');
    }
}

async function deleteStudent(id, name) {
    if(!confirm(`Are you sure you want to delete student: ${name}?`)) return;
    try {
        const res = await apiCall('/api/admin/delete-student/', {
            method: 'POST',
            body: JSON.stringify({student_id: id})
        });
        const data = await res.json();
        if(data.success) {
            showToast(data.message);
            const row = document.getElementById(`row-${id}`);
            if (row) row.remove();
            setTimeout(() => window.location.reload(), 800);
        } else {
            showToast(data.message, 'error');
        }
    } catch(e) {
        showToast('Error deleting student.', 'error');
    }
}

async function deleteGig(id, title) {
    if(!confirm(`Delete gig: ${title}?`)) return;
    try {
        const res = await apiCall('/api/admin/delete-gig/', {
            method: 'POST',
            body: JSON.stringify({gig_id: id})
        });
        const data = await res.json();
        if(data.success) {
            showToast(data.message);
            const row = document.getElementById(`gig-row-${id}`);
            if (row) row.remove();
            setTimeout(() => window.location.reload(), 800);
        } else {
            showToast(data.message, 'error');
        }
    } catch(e) {
        showToast('Error deleting gig.', 'error');
    }
}

async function viewDetails(id) {
    const modal = document.getElementById('detailsModal');
    const body = document.getElementById('modalBody');
    const nameEl = document.getElementById('modalName');
    
    if (!modal || !body) return;
    
    modal.classList.add('active');
    body.innerHTML = '<div style="text-align:center; padding:2rem;"><span class="spinner"></span></div>';
    
    try {
        const res = await apiCall(`/api/admin/student/?id=${id}`);
        const data = await res.json();
        if(data.success) {
            const p = data.data;
            if (nameEl) nameEl.textContent = p.full_name;
            body.innerHTML = `
                <div class="detail-row"><div class="detail-label">Email</div><div>${p.email}</div></div>
                <div class="detail-row"><div class="detail-label">Mobile</div><div>${p.mobile}</div></div>
                <div class="detail-row"><div class="detail-label">Platform</div><div>${p.registration_platform || '--'}</div></div>
                <div class="detail-row"><div class="detail-label">College</div><div>${p.college || '--'}</div></div>
                <div class="detail-row"><div class="detail-label">Skills</div><div>${p.skills || '--'}</div></div>
                <div class="detail-row"><div class="detail-label">About</div><div>${p.about || '--'}</div></div>
            `;
        } else {
            body.innerHTML = `<p>${data.message}</p>`;
        }
    } catch(e) {
        showToast('Error loading student details.', 'error');
        body.innerHTML = '<p>Error.</p>';
    }
}

async function viewGig(id) {
    const modal = document.getElementById('detailsModal');
    const body = document.getElementById('modalBody');
    const nameEl = document.getElementById('modalName');
    
    if (!modal || !body) return;
    
    modal.classList.add('active');
    body.innerHTML = '<div style="text-align:center; padding:2rem;"><span class="spinner"></span></div>';
    
    try {
        const res = await apiCall(`/api/employer/get-gig/?id=${id}`);
        const result = await res.json();
        if(result.success) {
            const g = result.data;
            if (nameEl) nameEl.textContent = g.title;
            body.innerHTML = `
                <div class="detail-row"><div class="detail-label">Status</div><div>${g.status}</div></div>
                <div class="detail-row"><div class="detail-label">Earnings</div><div>${g.earnings}</div></div>
                <div class="detail-row"><div class="detail-label">Date/Time</div><div>${g.date} ${g.time}</div></div>
                <div class="detail-row"><div class="detail-label">Description</div><div>${g.description}</div></div>
                ${g.image_url ? `<div class="detail-row"><div class="detail-label">Image</div><div><img src="${g.image_url}" style="max-width:100%; border-radius:8px; margin-top:0.5rem;"></div></div>` : ''}
            `;
        } else {
            body.innerHTML = `<p>${result.message}</p>`;
        }
    } catch(e) {
        showToast('Error loading gig details.', 'error');
        body.innerHTML = '<p>Error.</p>';
    }
}

function closeModal() {
    const modal = document.getElementById('detailsModal');
    if (modal) modal.classList.remove('active');
}
