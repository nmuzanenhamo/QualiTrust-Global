/* ═══════════════════════════════════════════════════════
   QualiTrust Global — App Logic
   ═══════════════════════════════════════════════════════ */

/* ─────────── STATE ─────────── */
const API = '/api/v1';
let token = localStorage.getItem('qvs_token');
let refreshToken = localStorage.getItem('qvs_refresh');
let currentUser = null;
let qualPage = 1;
let auditPage = 1;
let editingQualId = null;
const PAGE_SIZE = 10;

/* ─────────── API HELPER ─────────── */
async function api(path, options = {}) {
  const headers = options.headers || {};
  if (token) headers['Authorization'] = `Bearer ${token}`;
  // Stringify body without mutating options.body, so 401 retries don't double-encode
  let body = options.body;
  if (body && !(body instanceof FormData) && typeof body !== 'string') {
    headers['Content-Type'] = 'application/json';
    body = JSON.stringify(body);
  }
  const res = await fetch(`${API}${path}`, { ...options, body, headers });

  if (res.status === 401 && refreshToken && !path.startsWith('/auth/')) {
    const refreshed = await tryRefresh();
    if (refreshed) return api(path, options);
  }

  if (!res.ok) {
    let detail = `Request failed (${res.status})`;
    try {
      const err = await res.json();
      if (typeof err.detail === 'string') detail = err.detail;
      else if (Array.isArray(err.detail)) {
        detail = err.detail.map(d => `${(d.loc || []).slice(-1)[0] || 'field'}: ${d.msg}`).join('; ');
      } else detail = JSON.stringify(err.detail || err);
    } catch { /* ignore */ }
    throw new Error(detail);
  }

  if (res.status === 204) return null;
  return res.json();
}

async function tryRefresh() {
  try {
    const res = await fetch(`${API}/auth/refresh?refresh_token=${encodeURIComponent(refreshToken)}`, { method: 'POST' });
    if (!res.ok) { logout(); return false; }
    const data = await res.json();
    token = data.access_token;
    refreshToken = data.refresh_token;
    localStorage.setItem('qvs_token', token);
    localStorage.setItem('qvs_refresh', refreshToken);
    return true;
  } catch {
    logout();
    return false;
  }
}

/* ─────────── TOAST ─────────── */
function toast(message, type = 'info') {
  const container = document.getElementById('toast-container');
  const el = document.createElement('div');
  el.className = `toast ${type}`;
  const icons = {
    success: '<svg width="19" height="19" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><path d="m9 11 3 3L22 4"/></svg>',
    error: '<svg width="19" height="19" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><path d="m15 9-6 6"/><path d="m9 9 6 6"/></svg>',
    info: '<svg width="19" height="19" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><path d="M12 16v-4"/><path d="M12 8h.01"/></svg>',
  };
  el.innerHTML = `${icons[type] || icons.info}<span>${escapeHtml(message)}</span>`;
  container.appendChild(el);
  setTimeout(() => {
    el.style.opacity = '0';
    el.style.transform = 'translateX(120%)';
    setTimeout(() => el.remove(), 350);
  }, 4200);
}

/* ─────────── LOADING ─────────── */
function showLoading() { document.getElementById('loading-overlay').classList.remove('hidden'); }
function hideLoading() { document.getElementById('loading-overlay').classList.add('hidden'); }

/* ─────────── AUTH ─────────── */
function logout() {
  token = null;
  refreshToken = null;
  currentUser = null;
  localStorage.removeItem('qvs_token');
  localStorage.removeItem('qvs_refresh');
  document.getElementById('app').classList.add('hidden');
  document.getElementById('auth-page').classList.remove('hidden');
}

async function loadCurrentUser() {
  try {
    currentUser = await api('/auth/me');
    updateUserUI();
  } catch {
    logout();
    throw new Error('Session expired');
  }
}

function updateUserUI() {
  if (!currentUser) return;
  document.getElementById('user-name').textContent = currentUser.full_name;
  document.getElementById('user-role').textContent = currentUser.role;
  document.getElementById('user-avatar').textContent = currentUser.full_name.charAt(0).toUpperCase();

  const isAdmin = currentUser.role === 'admin';
  document.querySelectorAll('.admin-only').forEach(el => {
    el.style.display = isAdmin ? 'flex' : 'none';
  });
}

/* ─────────── AUTH TABS & PASSWORD TOGGLE ─────────── */
document.querySelectorAll('.auth-tab').forEach(tab => {
  tab.addEventListener('click', () => {
    document.querySelectorAll('.auth-tab').forEach(t => t.classList.remove('active'));
    document.querySelectorAll('.auth-form').forEach(f => f.classList.remove('active'));
    tab.classList.add('active');
    document.getElementById(`${tab.dataset.tab}-form`).classList.add('active');
  });
});

document.querySelectorAll('.pw-toggle').forEach(btn => {
  btn.addEventListener('click', () => {
    const input = document.getElementById(btn.dataset.target);
    input.type = input.type === 'password' ? 'text' : 'password';
  });
});

/* ─────────── LOGIN ─────────── */
document.getElementById('login-form').addEventListener('submit', async (e) => {
  e.preventDefault();
  const email = document.getElementById('login-email').value.trim();
  const password = document.getElementById('login-password').value;
  const btn = e.target.querySelector('button[type=submit]');
  btn.disabled = true;
  showLoading();
  try {
    const formData = new FormData();
    formData.append('username', email);
    formData.append('password', password);
    const res = await fetch(`${API}/auth/login`, { method: 'POST', body: formData });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || 'Invalid email or password');
    }
    const data = await res.json();
    token = data.access_token;
    refreshToken = data.refresh_token;
    localStorage.setItem('qvs_token', token);
    localStorage.setItem('qvs_refresh', refreshToken);
    toast('Welcome back!', 'success');
    await initApp();
  } catch (err) {
    toast(err.message, 'error');
  } finally {
    btn.disabled = false;
    hideLoading();
  }
});

/* ─────────── REGISTER ─────────── */
document.getElementById('register-form').addEventListener('submit', async (e) => {
  e.preventDefault();
  const body = {
    email: document.getElementById('reg-email').value.trim(),
    full_name: document.getElementById('reg-name').value.trim(),
    password: document.getElementById('reg-password').value,
    role: document.getElementById('reg-role').value,
  };
  showLoading();
  try {
    await api('/auth/register', { method: 'POST', body });
    toast('Account created! Sign in to continue.', 'success');
    document.querySelector('[data-tab="login"]').click();
    document.getElementById('login-email').value = body.email;
    document.getElementById('login-password').focus();
  } catch (err) {
    toast(err.message, 'error');
  } finally {
    hideLoading();
  }
});

/* ─────────── NAVIGATION ─────────── */
const pageTitles = {
  dashboard: 'Dashboard',
  qualifications: 'Qualifications',
  verify: 'Verify Credential',
  ai: 'AI Fraud Analysis',
  audit: 'Audit Trail',
  users: 'User Management',
};

document.querySelectorAll('.nav-item').forEach(item => {
  item.addEventListener('click', (e) => {
    e.preventDefault();
    navigateTo(item.dataset.page);
  });
});

function navigateTo(page) {
  document.querySelectorAll('.nav-item').forEach(n => n.classList.remove('active'));
  const navItem = document.querySelector(`.nav-item[data-page="${page}"]`);
  if (navItem) navItem.classList.add('active');
  document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
  const pageEl = document.getElementById(`page-${page}`);
  if (pageEl) pageEl.classList.add('active');
  document.getElementById('page-title').textContent = pageTitles[page] || page;
  if (page === 'dashboard') loadDashboard();
  if (page === 'qualifications') loadQualifications();
  if (page === 'audit') loadAuditLogs();
  if (page === 'users') loadUsers();
  if (window.innerWidth <= 768) {
    document.getElementById('sidebar').classList.remove('open');
    document.getElementById('sidebar-backdrop').classList.remove('show');
  }
}

document.getElementById('go-to-quals').addEventListener('click', () => navigateTo('qualifications'));

/* ─────────── SIDEBAR (MOBILE) ─────────── */
document.getElementById('menu-toggle').addEventListener('click', () => {
  document.getElementById('sidebar').classList.toggle('open');
  document.getElementById('sidebar-backdrop').classList.toggle('show');
});

document.getElementById('sidebar-backdrop').addEventListener('click', () => {
  document.getElementById('sidebar').classList.remove('open');
  document.getElementById('sidebar-backdrop').classList.remove('show');
});

document.getElementById('logout-btn').addEventListener('click', () => {
  logout();
  toast('Signed out', 'info');
});

/* ─────────── DASHBOARD ─────────── */
async function loadDashboard() {
  try {
    const data = await api(`/qualifications/?page=1&page_size=100`);
    const quals = data.items || [];
    const total = data.total || 0;
    const verified = quals.filter(q => q.status === 'verified').length;
    const registered = quals.filter(q => q.status === 'registered').length;
    const rejected = quals.filter(q => q.status === 'rejected').length;

    document.getElementById('stat-total').textContent = total;
    document.getElementById('stat-verified').textContent = verified;
    document.getElementById('stat-pending').textContent = registered;
    document.getElementById('stat-rejected').textContent = rejected;
    document.getElementById('nav-qual-count').textContent = total;

    animateValue('donut-total', total);
    updateDonut(verified, registered, rejected, total);
    document.getElementById('legend-verified').textContent = verified;
    document.getElementById('legend-pending').textContent = registered;
    document.getElementById('legend-rejected').textContent = rejected;

    const recent = quals.slice(0, 5);
    const container = document.getElementById('recent-quals-table');
    if (recent.length === 0) {
      container.innerHTML = emptyState('/static/icons', 'No credentials yet', 'Register your first qualification to see it here.');
    } else {
      container.innerHTML = renderQualTable(recent, false);
    }
  } catch (err) {
    toast(err.message, 'error');
  }
}

function updateDonut(verified, pending, rejected, total) {
  if (total === 0) return;
  const pV = (verified / total) * 100;
  const pP = (pending / total) * 100;
  const pR = (rejected / total) * 100;

  document.querySelector('.seg-verified').style.strokeDasharray = `${pV} ${100 - pV}`;
  document.querySelector('.seg-pending').style.strokeDasharray = `${pP} ${100 - pP} `;
  document.querySelector('.seg-pending').style.strokeDashoffset = `${-pV}`;
  document.querySelector('.seg-rejected').style.strokeDasharray = `${pR} ${100 - pR}`;
  document.querySelector('.seg-rejected').style.strokeDashoffset = `${-(pV + pP)}`;
}

function animateValue(id, target) {
  const el = document.getElementById(id);
  const start = 0;
  const dur = 600;
  const t0 = performance.now();
  function tick(t) {
    const p = Math.min((t - t0) / dur, 1);
    el.textContent = Math.round(start + (target - start) * (1 - Math.pow(1 - p, 3)));
    if (p < 1) requestAnimationFrame(tick);
  }
  requestAnimationFrame(tick);
}

/* ─────────── QUALIFICATIONS ─────────── */
async function loadQualifications(page = 1) {
  qualPage = page;
  const search = document.getElementById('qual-search').value.trim();
  const statusFilter = document.getElementById('qual-status-filter').value;

  let params = `page=${page}&page_size=${PAGE_SIZE}`;
  if (search) params += `&query=${encodeURIComponent(search)}`;
  if (statusFilter) params += `&status=${encodeURIComponent(statusFilter)}`;

  const container = document.getElementById('quals-table');
  try {
    const data = await api(`/qualifications/?${params}`);
    document.getElementById('nav-qual-count').textContent = data.total;
    if (data.items.length === 0) {
      container.innerHTML = emptyState(null, 'No credentials found', 'Try adjusting your search or filters, or register a new credential.');
    } else {
      container.innerHTML = renderQualTable(data.items, true);
    }
    renderPagination('quals-pagination', data.page, data.total_pages, loadQualifications);
  } catch (err) {
    container.innerHTML = emptyState(null, 'Failed to load', err.message);
    toast(err.message, 'error');
  }
}

const typeLabels = {
  undergraduate_degree: 'Undergrad. Degree',
  masters_degree: "Master's Degree",
  postgraduate_diploma: 'Postgrad. Diploma',
  postgraduate_certificate: 'Postgrad. Certificate',
  doctorate: 'Doctorate (PhD)',
  diploma: 'Diploma',
  certificate: 'Certificate',
  professional_certification: 'Prof. Cert.',
  other: 'Other',
};

function statusBadge(status) {
  const cls = { registered: 'badge-registered', verified: 'badge-verified', rejected: 'badge-rejected', pending: 'badge-pending', revoked: 'badge-revoked' };
  const badgeClass = cls[status] || 'badge-registered';
  const label = status || 'registered';
  return '<span class="badge ' + badgeClass + '">' + escapeHtml(label) + '</span>';
}

function renderQualTable(quals, showActions) {
  let html = `<table><thead><tr>
    <th>ID</th><th>Title</th><th>Holder</th><th>Institution</th><th>Type</th><th>Grade</th><th>Status</th><th>Issued</th>
    ${showActions ? '<th style="text-align:right;">Actions</th>' : ''}
  </tr></thead><tbody>`;
  for (const q of quals) {
    const dateStr = q.date_issued ? new Date(q.date_issued).toLocaleDateString(undefined, { year: 'numeric', month: 'short', day: 'numeric' }) : '—';
    const gradeHtml = q.grade ? `<span style="color:var(--accent-2);font-weight:600;font-size:12px;">${escapeHtml(q.grade)}</span>` : '<span style="color:var(--text-3);">—</span>';
    let actions = '';
    if (showActions) {
      actions = `<td><div class="action-btns" style="justify-content:flex-end;">
        <button class="action-btn" onclick="viewQual(${q.id})">View</button>
        <button class="action-btn success" onclick="goVerify(${q.id})">Verify</button>
        <button class="action-btn" onclick="goAi(${q.id})">AI</button>
        <button class="action-btn" onclick="editQual(${q.id})">Edit</button>
        <button class="action-btn danger" onclick="deleteQual(${q.id})">Delete</button>
      </div></td>`;
    }
    html += `<tr>
      <td>#${q.id}</td>
      <td class="title-cell">${escapeHtml(q.title)}</td>
      <td>${escapeHtml(q.holder_name)}</td>
      <td>${escapeHtml(q.issuing_institution)}</td>
      <td><span class="badge badge-role">${escapeHtml(typeLabels[q.qualification_type] || q.qualification_type)}</span></td>
      <td>${gradeHtml}</td>
      <td>${statusBadge(q.status)}</td>
      <td>${dateStr}</td>
      ${actions}
    </tr>`;
  }
  html += '</tbody></table>';
  return html;
}

window.goVerify = function(id) {
  navigateTo('verify');
  document.querySelector('.verify-tab[data-lookup="id"]').click();
  document.getElementById('verify-id').value = id;
  document.getElementById('verify-serial').value = '';
  document.getElementById('verify-reg').value = '';
  clearVerifyFileDrop();
  document.getElementById('lookup-preview').classList.add('hidden');
  document.getElementById('verify-empty').classList.add('hidden');
  document.getElementById('verify-result').classList.add('hidden');
  document.getElementById('verify-history').classList.add('hidden');
};

window.goAi = function(id) {
  navigateTo('ai');
  document.getElementById('ai-qual-id').value = id;
};

/* ─────────── QUAL MODAL (VIEW / ADD / EDIT) ─────────── */
const modal = document.getElementById('modal-overlay');
let selectedFile = null;

const fileDrop = document.getElementById('file-drop');
const fileInput = document.getElementById('f-document');
const fileDropText = document.getElementById('file-drop-text');
const extractBtn = document.getElementById('extract-btn');
const extractStatus = document.getElementById('extract-status');

fileDrop.addEventListener('click', () => fileInput.click());
fileInput.addEventListener('change', () => {
  if (fileInput.files.length > 0) {
    selectedFile = fileInput.files[0];
    fileDropText.textContent = selectedFile.name;
    fileDrop.classList.add('has-file');
    extractBtn.style.display = 'flex';
    extractStatus.classList.add('hidden');
  }
});
fileDrop.addEventListener('dragover', (e) => { e.preventDefault(); fileDrop.classList.add('dragover'); });
fileDrop.addEventListener('dragleave', () => fileDrop.classList.remove('dragover'));
fileDrop.addEventListener('drop', (e) => {
  e.preventDefault();
  fileDrop.classList.remove('dragover');
  if (e.dataTransfer.files.length > 0) {
    selectedFile = e.dataTransfer.files[0];
    fileInput.files = e.dataTransfer.files;
    fileDropText.textContent = selectedFile.name;
    fileDrop.classList.add('has-file');
    extractBtn.style.display = 'flex';
    extractStatus.classList.add('hidden');
  }
});

function clearFileDrop() {
  selectedFile = null;
  fileInput.value = '';
  fileDropText.textContent = 'Click to upload or drag a PDF / image';
  fileDrop.classList.remove('has-file');
  extractBtn.style.display = 'none';
  extractStatus.classList.add('hidden');
}

/* Auto-extract: reads the uploaded document via OCR and fills form fields */
extractBtn.addEventListener('click', async () => {
  if (!selectedFile) { toast('Upload a document first', 'error'); return; }

  extractBtn.disabled = true;
  extractBtn.innerHTML = '<div class="spinner" style="width:16px;height:16px;border-width:2px;"></div> Reading document...';
  extractStatus.classList.remove('hidden', 'success', 'error');
  extractStatus.classList.add('info');
  extractStatus.innerHTML = '<div class="extract-summary"><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><path d="M12 6v6l4 2"/></svg> Extracting text from document...</div>';

  try {
    const formData = new FormData();
    formData.append('file', selectedFile);
    const resp = await fetch(`${API}/qualifications/extract`, {
      method: 'POST',
      headers: { Authorization: `Bearer ${token}` },
      body: formData,
    });
    if (!resp.ok) {
      const err = await resp.json().catch(() => ({}));
      throw new Error(err.detail || resp.statusText);
    }
    const data = await resp.json();

    // Auto-fill form fields from extracted data
    if (data.holder_name) document.getElementById('f-holder').value = data.holder_name;
    if (data.issuing_institution) setInstitutionValue(data.issuing_institution);
    if (data.title) setTitleValue(data.title);
    if (data.qualification_type) document.getElementById('f-type').value = data.qualification_type;
    if (data.grade) {
      const gradeSelect = document.getElementById('f-grade');
      const gradeOption = Array.from(gradeSelect.options).find(o => o.value === data.grade);
      if (gradeOption) {
        gradeSelect.value = data.grade;
      } else {
        // If the grade doesn't match a predefined option, add it
        const newOption = new Option(data.grade, data.grade, true, true);
        gradeSelect.add(newOption);
      }
    }
    if (data.serial_number) document.getElementById('f-serial').value = data.serial_number;
    if (data.registration_number) document.getElementById('f-regnum').value = data.registration_number;
    if (data.holder_id_number) document.getElementById('f-idnum').value = data.holder_id_number;
    if (data.date_issued) {
      // Try to parse the date and set it
      const parsed = new Date(data.date_issued);
      if (!isNaN(parsed)) {
        document.getElementById('f-date').value = parsed.toISOString().split('T')[0];
      }
    }

    // Show extraction summary
    const conf = data.confidence || {};
    const foundFields = conf.extracted || [];
    const missingFields = conf.missing || [];
    const pct = conf.percentage || 0;

    let fieldsHtml = '';
    if (foundFields.length > 0) {
      fieldsHtml += '<div class="extract-fields">';
      for (const f of foundFields) {
        fieldsHtml += `<span class="extract-tag found">✓ ${escapeHtml(f.replace(/_/g, ' '))}</span>`;
      }
      if (missingFields.length > 0) {
        for (const f of missingFields) {
          fieldsHtml += `<span class="extract-tag missing">✕ ${escapeHtml(f.replace(/_/g, ' '))}</span>`;
        }
      }
      fieldsHtml += '</div>';
    }

    extractStatus.classList.remove('info', 'error');
    extractStatus.classList.add('success');
    extractStatus.innerHTML = `
      <div class="extract-summary">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><path d="m9 11 3 3L22 4"/></svg>
        ${pct}% of fields extracted — review and complete the form below.
      </div>
      ${fieldsHtml}
    `;

    toast(`${pct}% of fields auto-filled from document`, 'success');
  } catch (err) {
    extractStatus.classList.remove('info', 'success');
    extractStatus.classList.add('error');
    extractStatus.innerHTML = `<div class="extract-summary"><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><path d="m15 9-6 6"/><path d="m9 9 6 6"/></svg> ${escapeHtml(err.message)}</div>`;
    toast(err.message, 'error');
  } finally {
    extractBtn.disabled = false;
    extractBtn.innerHTML = '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 12a9 9 0 1 1-9-9"/><path d="M21 3v6h-6"/></svg> Read Document & Auto-Fill';
  }
});

function openModal(mode, id = null) {
  editingQualId = id;
  const titleEl = document.getElementById('modal-title');
  const formEl = document.getElementById('qual-form');
  const viewEl = document.getElementById('view-qual-body');
  const submitBtn = document.getElementById('qual-submit-btn');

  viewEl.classList.add('hidden');
  formEl.classList.add('hidden');

  if (mode === 'add') {
    titleEl.textContent = 'Register New Credential';
    formEl.classList.remove('hidden');
    formEl.reset();
    setInstitutionValue('');
    clearFileDrop();
    submitBtn.textContent = 'Register Credential';
  } else if (mode === 'edit') {
    titleEl.textContent = `Edit Credential #${id}`;
    formEl.classList.remove('hidden');
    clearFileDrop();
    submitBtn.textContent = 'Save Changes';
  } else if (mode === 'view') {
    titleEl.textContent = `Credential #${id} Details`;
    viewEl.classList.remove('hidden');
  }

  modal.classList.remove('hidden');
}

function closeModal() {
  modal.classList.add('hidden');
  editingQualId = null;
}

document.getElementById('add-qual-btn').addEventListener('click', () => openModal('add'));
document.getElementById('modal-close').addEventListener('click', closeModal);
document.getElementById('modal-cancel').addEventListener('click', closeModal);
// Don't close on overlay click — user might accidentally click outside while filling the form
// Only close on explicit close/cancel button or Escape (when not typing)
document.addEventListener('keydown', (e) => {
  if (e.key === 'Escape') {
    const active = document.activeElement;
    const isTyping = active && (active.tagName === 'INPUT' || active.tagName === 'TEXTAREA' || active.tagName === 'SELECT');
    if (!isTyping) { closeModal(); closeUserModal(); }
  }
});

/* ─────────── INSTITUTION / PROGRAMME CASCADE ─────────── */
const OTHER_VALUE = '__other__';
const instSelect = document.getElementById('f-institution');
const instOther = document.getElementById('f-institution-other');
const titleSelect = document.getElementById('f-title');
const titleOther = document.getElementById('f-title-other');

/* Populate the institution dropdown once on load. */
(function populateInstitutions() {
  const opts = ['<option value="">Select an institution…</option>'];
  for (const inst of (window.INSTITUTIONS || [])) {
    opts.push(`<option value="${escapeHtml(inst.name)}">${escapeHtml(inst.name)}</option>`);
  }
  opts.push('<option value="__other__">Other (specify manually)…</option>');
  instSelect.innerHTML = opts.join('');
})();

/* Reveal/hide the manual institution input. */
instSelect.addEventListener('change', () => {
  if (instSelect.value === OTHER_VALUE) {
    instOther.classList.remove('hidden');
    instOther.required = true;
    instOther.focus();
  } else {
    instOther.classList.add('hidden');
    instOther.required = false;
    instOther.value = '';
  }
  populateTitles(instSelect.value);
});

/* Populate the qualification-title dropdown based on the chosen institution. */
function populateTitles(institutionName) {
  const opts = [];
  if (!institutionName || institutionName === OTHER_VALUE) {
    opts.push('<option value="">Select an institution first…</option>');
  } else {
    opts.push('<option value="">Select a programme…</option>');
    const inst = (window.INSTITUTIONS || []).find(i => i.name === institutionName);
    if (inst && inst.programmes) {
      for (const p of inst.programmes) {
        opts.push(`<option value="${escapeHtml(p)}">${escapeHtml(p)}</option>`);
      }
    }
    opts.push('<option value="__other__">Other (specify manually)…</option>');
  }
  titleSelect.innerHTML = opts.join('');
  titleSelect.value = '';
  titleOther.classList.add('hidden');
  titleOther.required = false;
  titleOther.value = '';
}

/* Reveal/hide the manual title input. */
titleSelect.addEventListener('change', () => {
  if (titleSelect.value === OTHER_VALUE) {
    titleOther.classList.remove('hidden');
    titleOther.required = true;
    titleOther.focus();
  } else {
    titleOther.classList.add('hidden');
    titleOther.required = false;
    titleOther.value = '';
  }
});

/* Resolve the final institution value from select or manual input. */
function resolveInstitution() {
  if (instSelect.value === OTHER_VALUE) return instOther.value.trim();
  return instSelect.value.trim();
}

/* Resolve the final qualification title value from select or manual input. */
function resolveTitle() {
  if (titleSelect.value === OTHER_VALUE) return titleOther.value.trim();
  return titleSelect.value.trim();
}

/* Set the institution field to an existing value (used when editing). */
function setInstitutionValue(value) {
  const exists = Array.from(instSelect.options).some(o => o.value === value);
  if (exists) {
    instSelect.value = value;
    instOther.classList.add('hidden');
    instOther.required = false;
    instOther.value = '';
  } else if (value) {
    instSelect.value = OTHER_VALUE;
    instOther.classList.remove('hidden');
    instOther.required = true;
    instOther.value = value;
  } else {
    instSelect.value = '';
    instOther.classList.add('hidden');
    instOther.required = false;
    instOther.value = '';
  }
  populateTitles(instSelect.value);
}

/* Set the qualification title field to an existing value (used when editing). */
function setTitleValue(value) {
  const exists = Array.from(titleSelect.options).some(o => o.value === value);
  if (exists) {
    titleSelect.value = value;
    titleOther.classList.add('hidden');
    titleOther.required = false;
    titleOther.value = '';
  } else if (value) {
    titleSelect.value = OTHER_VALUE;
    titleOther.classList.remove('hidden');
    titleOther.required = true;
    titleOther.value = value;
  } else {
    titleSelect.value = '';
    titleOther.classList.add('hidden');
    titleOther.required = false;
    titleOther.value = '';
  }
}

window.viewQual = async function(id) {
  showLoading();
  try {
    const q = await api(`/qualifications/${id}`);
    openModal('view', id);
    const rows = [
      ['Title', escapeHtml(q.title)],
      ['Type', escapeHtml(typeLabels[q.qualification_type] || q.qualification_type)],
      ['Status', statusBadge(q.status)],
      ['Institution', escapeHtml(q.issuing_institution)],
      ['Holder', escapeHtml(q.holder_name)],
      ['Holder Email', q.holder_email ? escapeHtml(q.holder_email) : '—'],
      ['Holder ID No.', q.holder_id_number ? escapeHtml(q.holder_id_number) : '—'],
      ['Date Issued', q.date_issued ? new Date(q.date_issued).toLocaleDateString() : '—'],
      ['Registration No.', q.registration_number ? escapeHtml(q.registration_number) : '—'],
      ['Serial No.', q.serial_number ? escapeHtml(q.serial_number) : '—'],
      ['Grade / Class', q.grade ? `<span style="color:var(--accent-2);font-weight:600;">${escapeHtml(q.grade)}</span>` : '—'],
      ['Credential Hash', q.credential_hash ? `<span class="hash-value">${escapeHtml(q.credential_hash)}</span>` : '<span style="color:var(--red);">Not assigned</span>'],
      ['Previous Hash', q.previous_hash ? `<span class="hash-value">${escapeHtml(q.previous_hash)}</span>` : '— (genesis)'],
      ['Description', q.description ? escapeHtml(q.description) : '—'],
      ['Document', q.document_path
        ? `<a href="${escapeHtml(q.document_path)}" target="_blank" rel="noopener" style="color:var(--accent-2);font-weight:600;text-decoration:none;display:inline-flex;align-items:center;gap:6px;"><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><path d="M14 2v6h6"/></svg>View Document</a>`
        : '<span style="color:var(--text-3);">No document uploaded</span>'],
      ['Registered', new Date(q.created_at).toLocaleString()],
    ];
    document.getElementById('view-qual-body').innerHTML = `
      <div class="view-rows">
        ${rows.map(([l, v]) => `<div class="view-row"><span class="view-label">${l}</span><span class="view-value">${v}</span></div>`).join('')}
      </div>
      <div class="modal-foot">
        <button class="btn btn-ghost" onclick="closeModal()">Close</button>
        <button class="btn btn-primary" onclick="goVerify(${id}); closeModal();">Verify This Credential</button>
      </div>
    `;
  } catch (err) {
    toast(err.message, 'error');
  } finally {
    hideLoading();
  }
};
window.closeModal = closeModal;

window.editQual = async function(id) {
  showLoading();
  try {
    const q = await api(`/qualifications/${id}`);
    openModal('edit', id);
    document.getElementById('f-type').value = q.qualification_type || 'undergraduate_degree';
    setInstitutionValue(q.issuing_institution || '');
    setTitleValue(q.title || '');
    document.getElementById('f-holder').value = q.holder_name || '';
    if (q.date_issued) {
      const d = new Date(q.date_issued);
      document.getElementById('f-date').value = d.toISOString().split('T')[0];
    }
    document.getElementById('f-email').value = q.holder_email || '';
    document.getElementById('f-idnum').value = q.holder_id_number || '';
    document.getElementById('f-regnum').value = q.registration_number || '';
    document.getElementById('f-serial').value = q.serial_number || '';
    document.getElementById('f-grade').value = q.grade || '';
    document.getElementById('f-desc').value = q.description || '';
  } catch (err) {
    toast(err.message, 'error');
    closeModal();
  } finally {
    hideLoading();
  }
};

document.getElementById('qual-form').addEventListener('submit', async (e) => {
  e.preventDefault();
  const body = {
    title: resolveTitle(),
    qualification_type: document.getElementById('f-type').value,
    issuing_institution: resolveInstitution(),
    holder_name: document.getElementById('f-holder').value.trim(),
    holder_email: document.getElementById('f-email').value.trim() || null,
    holder_id_number: document.getElementById('f-idnum').value.trim() || null,
    date_issued: new Date(document.getElementById('f-date').value).toISOString(),
    registration_number: document.getElementById('f-regnum').value.trim() || null,
    serial_number: document.getElementById('f-serial').value.trim() || null,
    grade: document.getElementById('f-grade').value || null,
    description: document.getElementById('f-desc').value.trim() || null,
  };
  showLoading();
  try {
    let createdId;
    if (editingQualId) {
      await api(`/qualifications/${editingQualId}`, { method: 'PUT', body });
      createdId = editingQualId;
      toast('Credential updated successfully!', 'success');
    } else {
      const result = await api('/qualifications/', { method: 'POST', body });
      createdId = result.id;
      toast('Credential registered with blockchain hash!', 'success');
    }

    if (selectedFile && createdId) {
      const formData = new FormData();
      formData.append('file', selectedFile);
      const resp = await fetch(`${API}/qualifications/${createdId}/document`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}` },
        body: formData,
      });
      if (!resp.ok) {
        const err = await resp.json().catch(() => ({}));
        toast(`Document upload failed: ${err.detail || resp.statusText}`, 'error');
      } else {
        toast('Document uploaded successfully!', 'success');
      }
    }

    closeModal();
    loadQualifications(editingQualId ? qualPage : 1);
  } catch (err) {
    toast(err.message, 'error');
  } finally {
    hideLoading();
  }
});

window.deleteQual = async function(id) {
  if (!confirm(`Delete credential #${id}? This can be reverted by an admin.`)) return;
  showLoading();
  try {
    await api(`/qualifications/${id}`, { method: 'DELETE' });
    toast('Credential deleted', 'success');
    loadQualifications(qualPage);
  } catch (err) {
    toast(err.message, 'error');
  } finally {
    hideLoading();
  }
};

/* Search & filter */
let searchTimeout;
document.getElementById('qual-search').addEventListener('input', () => {
  clearTimeout(searchTimeout);
  searchTimeout = setTimeout(() => loadQualifications(1), 400);
});
document.getElementById('qual-status-filter').addEventListener('change', () => loadQualifications(1));

/* ─────────── VERIFICATION ─────────── */
let verifyLookupMode = 'id';
let verifySelectedFile = null;

const verifyFileDrop = document.getElementById('verify-file-drop');
const verifyFileInput = document.getElementById('verify-document');
const verifyFileDropText = document.getElementById('verify-file-drop-text');

verifyFileDrop.addEventListener('click', () => verifyFileInput.click());
verifyFileInput.addEventListener('change', () => {
  if (verifyFileInput.files.length > 0) {
    verifySelectedFile = verifyFileInput.files[0];
    verifyFileDropText.textContent = verifySelectedFile.name;
    verifyFileDrop.classList.add('has-file');
  }
});
verifyFileDrop.addEventListener('dragover', (e) => { e.preventDefault(); verifyFileDrop.classList.add('dragover'); });
verifyFileDrop.addEventListener('dragleave', () => verifyFileDrop.classList.remove('dragover'));
verifyFileDrop.addEventListener('drop', (e) => {
  e.preventDefault();
  verifyFileDrop.classList.remove('dragover');
  if (e.dataTransfer.files.length > 0) {
    verifySelectedFile = e.dataTransfer.files[0];
    verifyFileInput.files = e.dataTransfer.files;
    verifyFileDropText.textContent = verifySelectedFile.name;
    verifyFileDrop.classList.add('has-file');
  }
});

function clearVerifyFileDrop() {
  verifySelectedFile = null;
  verifyFileInput.value = '';
  verifyFileDropText.textContent = 'Upload certificate/transcript to compare';
  verifyFileDrop.classList.remove('has-file');
}

document.querySelectorAll('.verify-tab').forEach(tab => {
  tab.addEventListener('click', () => {
    document.querySelectorAll('.verify-tab').forEach(t => t.classList.remove('active'));
    document.querySelectorAll('.lookup-mode').forEach(m => m.classList.remove('active'));
    tab.classList.add('active');
    verifyLookupMode = tab.dataset.lookup;
    document.getElementById(`lookup-${verifyLookupMode}`).classList.add('active');
    document.getElementById('lookup-preview').classList.add('hidden');

    // In By Document mode the file upload is the lookup mechanism — make it required
    const fileLabel = document.getElementById('verify-file-label');
    if (verifyLookupMode === 'document') {
      fileLabel.innerHTML = 'Upload Certificate / Transcript <span style="color:var(--red);font-weight:600;">required</span>';
    } else {
      fileLabel.innerHTML = 'Upload Document for AI Comparison <span class="optional">optional</span>';
    }
  });
});

document.getElementById('verify-btn').addEventListener('click', async () => {
  const method = document.getElementById('verify-method').value;
  const notes = document.getElementById('verify-notes').value.trim();
  let qualId = document.getElementById('verify-id').value;

  // ── By Document mode: upload-only verification (employer flow) ──
  if (verifyLookupMode === 'document') {
    if (!verifySelectedFile) { toast('Upload a certificate document first', 'error'); return; }

    showLoading();
    try {
      const formData = new FormData();
      formData.append('method', method);
      if (notes) formData.append('notes', notes);
      formData.append('file', verifySelectedFile);
      const token = localStorage.getItem('token');
      const resp = await fetch(`/api/v1/qualifications/verify-document`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}` },
        body: formData,
      });
      if (!resp.ok) {
        const err = await resp.json().catch(() => ({}));
        throw new Error(err.detail || resp.statusText);
      }
      const result = await resp.json();
      hideLoading();
      renderDocumentVerificationResult(result);
    } catch (err) {
      hideLoading();
      toast(err.message, 'error');
    }
    return;
  }

  if (verifyLookupMode === 'serial') {
    const serial = document.getElementById('verify-serial').value.trim();
    const reg = document.getElementById('verify-reg').value.trim();
    if (!serial) { toast('Enter a serial number', 'error'); return; }

    showLoading();
    try {
      let lookupUrl = `/qualifications/lookup?serial_number=${encodeURIComponent(serial)}`;
      if (reg) lookupUrl += `&registration_number=${encodeURIComponent(reg)}`;
      const found = await api(lookupUrl);
      qualId = found.id;
      document.getElementById('lookup-preview').classList.remove('hidden');
      document.getElementById('lookup-preview-body').innerHTML = `
        <div class="result-detail-row"><span class="result-detail-label">ID</span><span class="result-detail-value">#${found.id}</span></div>
        <div class="result-detail-row"><span class="result-detail-label">Title</span><span class="result-detail-value">${escapeHtml(found.title)}</span></div>
        <div class="result-detail-row"><span class="result-detail-label">Holder</span><span class="result-detail-value">${escapeHtml(found.holder_name)}</span></div>
        <div class="result-detail-row"><span class="result-detail-label">Institution</span><span class="result-detail-value">${escapeHtml(found.issuing_institution)}</span></div>
        <div class="result-detail-row"><span class="result-detail-label">Type</span><span class="result-detail-value">${escapeHtml(typeLabels[found.qualification_type] || found.qualification_type)}</span></div>
        ${found.grade ? `<div class="result-detail-row"><span class="result-detail-label">Grade / Class</span><span class="result-detail-value" style="color:var(--accent-2);font-weight:600;">${escapeHtml(found.grade)}</span></div>` : ''}
        <div class="result-detail-row"><span class="result-detail-label">Date Issued</span><span class="result-detail-value">${found.date_issued ? new Date(found.date_issued).toLocaleDateString() : '—'}</span></div>
        <div class="result-detail-row"><span class="result-detail-label">Status</span><span class="result-detail-value">${statusBadge(found.status)}</span></div>
      `;
    } catch (err) {
      hideLoading();
      toast(err.message, 'error');
      return;
    }
    hideLoading();
  }

  if (!qualId) { toast('Enter a qualification ID or serial/registration numbers', 'error'); return; }

  showLoading();
  try {
    let result;
    if (verifySelectedFile) {
      const formData = new FormData();
      formData.append('method', method);
      if (notes) formData.append('notes', notes);
      formData.append('file', verifySelectedFile);
      const token = localStorage.getItem('token');
      const resp = await fetch(`/api/v1/qualifications/${qualId}/verify-with-document`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}` },
        body: formData,
      });
      if (!resp.ok) {
        const err = await resp.json().catch(() => ({}));
        throw new Error(err.detail || resp.statusText);
      }
      result = await resp.json();
    } else {
      let url = `/qualifications/${qualId}/verify?method=${encodeURIComponent(method)}`;
      if (notes) url += `&notes=${encodeURIComponent(notes)}`;
      result = await api(url, { method: 'POST' });
    }

    document.getElementById('verify-empty').classList.add('hidden');
    const resultEl = document.getElementById('verify-result');
    resultEl.classList.remove('hidden');

    const badge = document.getElementById('result-badge');
    const isPass = result.is_authentic && result.result !== 'rejected';
    badge.className = `result-badge ${isPass ? 'success' : 'fail'}`;
    badge.textContent = isPass
      ? `✓ Authentic — ${escapeHtml(result.result)}`
      : `✕ Not Authentic — ${escapeHtml(result.result)}`;

    document.getElementById('result-details').innerHTML = `
      <div class="result-detail-row"><span class="result-detail-label">Qualification ID</span><span class="result-detail-value">#${result.qualification_id}</span></div>
      <div class="result-detail-row"><span class="result-detail-label">Method</span><span class="result-detail-value">${escapeHtml(result.method)}</span></div>
      <div class="result-detail-row"><span class="result-detail-label">Verification Hash</span><span class="result-detail-value hash-value">${result.verification_hash ? escapeHtml(result.verification_hash) : 'Not assigned'}</span></div>
      <div class="result-detail-row"><span class="result-detail-label">AI Confidence</span><span class="result-detail-value">${result.ai_confidence_score != null ? result.ai_confidence_score + '%' : '—'}</span></div>
      <div class="result-detail-row"><span class="result-detail-label">Message</span><span class="result-detail-value">${escapeHtml(result.message)}</span></div>
      <div class="result-detail-row"><span class="result-detail-label">Verified At</span><span class="result-detail-value">${new Date(result.verified_at).toLocaleString()}</span></div>
      ${result.checks ? renderChecks(result.checks) : ''}
      ${result.qualification ? renderQualificationDetails(result.qualification) : ''}
    `;

    const aiEl = document.getElementById('result-ai');
    if (result.ai_analysis) {
      const ai = result.ai_analysis;
      let aiHtml = '<div style="margin-top:16px;padding-top:14px;border-top:1px solid var(--border);"><h4 style="font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:1px;color:var(--text-3);margin-bottom:10px;">AI Fraud Analysis</h4>';
      if (ai.recommendation) {
        const rec = ai.recommendation.toUpperCase();
        const cls = rec.includes('APPROVE') ? 'approve' : rec.includes('REJECT') ? 'reject' : 'review';
        const recColor = cls === 'approve' ? 'var(--green)' : cls === 'reject' ? 'var(--red)' : 'var(--amber)';
        aiHtml += `<div class="result-detail-row"><span class="result-detail-label">Recommendation</span><span class="result-detail-value" style="color:${recColor};font-weight:600;">${escapeHtml(ai.recommendation)}</span></div>`;
      }
      if (ai.risk_score != null) {
        aiHtml += `<div class="result-detail-row"><span class="result-detail-label">Risk Score</span><span class="result-detail-value">${ai.risk_score}/100</span></div>`;
      }
      if (ai.confidence_score != null) {
        aiHtml += `<div class="result-detail-row"><span class="result-detail-label">Confidence</span><span class="result-detail-value">${ai.confidence_score}%</span></div>`;
      }
      if (ai.anomalies && ai.anomalies.length > 0) {
        aiHtml += `<div class="result-detail-row"><span class="result-detail-label">Anomalies</span><span class="result-detail-value">${ai.anomalies.map(a => escapeHtml(a)).join('<br>')}</span></div>`;
      } else {
        aiHtml += `<div class="result-detail-row"><span class="result-detail-label">Anomalies</span><span class="result-detail-value" style="color:var(--green);">None detected</span></div>`;
      }
      aiHtml += '</div>';
      aiEl.innerHTML = aiHtml;
    } else {
      aiEl.innerHTML = '';
    }

    // Document analysis results
    const docEl = document.getElementById('result-document');
    if (result.document_analysis) {
      const da = result.document_analysis;
      let docHtml = '<div style="margin-top:16px;padding-top:14px;border-top:1px solid var(--border);"><h4 style="font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:1px;color:var(--text-3);margin-bottom:10px;">Document Match Analysis</h4>';

      // Data match section
      if (da.data_match) {
        const dm = da.data_match;
        const recColor = dm.recommendation === 'APPROVE' ? 'var(--green)' : dm.recommendation === 'REJECT' ? 'var(--red)' : 'var(--amber)';
        docHtml += `<div class="result-detail-row"><span class="result-detail-label">Data Match Score</span><span class="result-detail-value" style="color:${recColor};font-weight:600;">${dm.match_score}% — ${escapeHtml(dm.recommendation)}</span></div>`;
        docHtml += `<div class="result-detail-row"><span class="result-detail-label">Summary</span><span class="result-detail-value">${escapeHtml(dm.summary)}</span></div>`;
        if (dm.checks && dm.checks.length > 0) {
          docHtml += '<div style="margin-top:8px;">';
          for (const c of dm.checks) {
            const icon = c.found_in_document ? '<span class="check-pass">✓</span>' : '<span class="check-fail">✕</span>';
            docHtml += `<div class="result-detail-row"><span class="result-detail-label">${escapeHtml(c.field)}</span><span class="result-detail-value">${icon} ${c.found_in_document ? 'Match' : 'Mismatch'} (registered: ${escapeHtml(c.registered)})</span></div>`;
          }
          docHtml += '</div>';
        }
      }

      // Document vs document section
      if (da.document_vs_document) {
        const dvd = da.document_vs_document;
        const recColor2 = dvd.recommendation === 'APPROVE' ? 'var(--green)' : dvd.recommendation === 'REJECT' ? 'var(--red)' : 'var(--amber)';
        docHtml += `<div class="result-detail-row" style="margin-top:8px;"><span class="result-detail-label">Document vs Stored Doc</span><span class="result-detail-value" style="color:${recColor2};font-weight:600;">${dvd.match_score}% — ${escapeHtml(dvd.recommendation)}</span></div>`;
        docHtml += `<div class="result-detail-row"><span class="result-detail-label">Summary</span><span class="result-detail-value">${escapeHtml(dvd.summary)}</span></div>`;
      }

      // Extracted text preview
      if (da.extracted_text_preview) {
        docHtml += `<details style="margin-top:8px;"><summary style="cursor:pointer;font-size:12px;color:var(--text-3);font-weight:600;">Extracted Text Preview</summary><div style="margin-top:6px;padding:8px;background:var(--bg-2);border-radius:6px;font-size:11px;color:var(--text-3);white-space:pre-wrap;max-height:200px;overflow-y:auto;">${escapeHtml(da.extracted_text_preview)}</div></details>`;
      }

      docHtml += '</div>';
      docEl.innerHTML = docHtml;
    } else {
      docEl.innerHTML = '';
    }

    toast(isPass ? 'Verification passed!' : 'Verification failed', isPass ? 'success' : 'error');

    loadVerifyHistory(qualId);
  } catch (err) {
    toast(err.message, 'error');
  } finally {
    hideLoading();
  }
});

async function loadVerifyHistory(id) {
  try {
    const history = await api(`/qualifications/${id}/verifications`);
    const histEl = document.getElementById('verify-history');
    if (history.length > 0) {
      histEl.classList.remove('hidden');
      document.getElementById('history-list').innerHTML = history.map(h => `
        <div class="history-item">
          <div class="history-item-row">
            <span>Result</span>
            <span class="badge ${h.result === 'verified' ? 'badge-verified' : h.result === 'rejected' ? 'badge-rejected' : 'badge-pending'}">${escapeHtml(h.result)}</span>
          </div>
          <div class="history-item-row"><span>Method</span><span>${escapeHtml(h.method)}</span></div>
          <div class="history-item-row"><span>Date</span><span>${new Date(h.created_at).toLocaleString()}</span></div>
          ${h.notes ? `<div class="history-notes">${escapeHtml(h.notes)}</div>` : ''}
        </div>
      `).join('');
    } else {
      histEl.classList.add('hidden');
    }
  } catch { /* ignore */ }
}

function renderChecks(checks) {
  const labels = {
    has_hash: 'Credential Hash Assigned',
    hash_valid: 'Hash Chain Integrity',
    has_serial: 'Serial Number Present',
    has_registration: 'Registration Number Present',
    not_expired: 'Not Expired',
    not_revoked: 'Not Revoked',
  };
  const icons = {
    pass: '<svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><path d="m9 11 3 3L22 4"/></svg>',
    fail: '<svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round"><circle cx="12" cy="12" r="10"/><path d="m15 9-6 6"/><path d="m9 9 6 6"/></svg>',
  };
  let html = '<div style="margin-top:16px;padding-top:14px;border-top:1px solid var(--border);"><h4 style="font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:1px;color:var(--text-3);margin-bottom:10px;">Blockchain Integrity Checks</h4>';
  for (const [key, passed] of Object.entries(checks)) {
    const label = labels[key] || key;
    html += `<div class="result-detail-row">
      <span class="result-detail-label">${label}</span>
      <span class="${passed ? 'check-pass' : 'check-fail'}">${icons[passed ? 'pass' : 'fail']} ${passed ? 'Pass' : 'Fail'}</span>
    </div>`;
  }
  html += '</div>';
  return html;
}

/* Render full qualification details in verification results */
function renderQualificationDetails(q) {
  const typeLabel = typeLabels[q.qualification_type] || q.qualification_type || '—';
  const dateStr = q.date_issued ? new Date(q.date_issued).toLocaleDateString(undefined, { year: 'numeric', month: 'long', day: 'numeric' }) : '—';
  const gradeHtml = q.grade
    ? `<span class="value grade-badge">${escapeHtml(q.grade)}</span>`
    : '<span class="value" style="color:var(--text-3);">Not specified</span>';

  return `
    <div class="qual-detail-panel">
      <h4>Confirmed Qualification Details</h4>
      <div class="qual-detail-grid">
        <div class="qual-detail-item">
          <span class="label">Qualification Title</span>
          <span class="value">${escapeHtml(q.title || '—')}</span>
        </div>
        <div class="qual-detail-item">
          <span class="label">Type</span>
          <span class="value">${escapeHtml(typeLabel)}</span>
        </div>
        <div class="qual-detail-item">
          <span class="label">Issuing Institution</span>
          <span class="value">${escapeHtml(q.issuing_institution || '—')}</span>
        </div>
        <div class="qual-detail-item">
          <span class="label">Holder Name</span>
          <span class="value">${escapeHtml(q.holder_name || '—')}</span>
        </div>
        <div class="qual-detail-item">
          <span class="label">Grade / Class</span>
          ${gradeHtml}
        </div>
        <div class="qual-detail-item">
          <span class="label">Date Issued</span>
          <span class="value">${dateStr}</span>
        </div>
        <div class="qual-detail-item">
          <span class="label">Registration No.</span>
          <span class="value">${q.registration_number ? escapeHtml(q.registration_number) : '—'}</span>
        </div>
        <div class="qual-detail-item">
          <span class="label">Serial No.</span>
          <span class="value">${q.serial_number ? escapeHtml(q.serial_number) : '—'}</span>
        </div>
        <div class="qual-detail-item">
          <span class="label">Holder ID No.</span>
          <span class="value">${q.holder_id_number ? escapeHtml(q.holder_id_number) : '—'}</span>
        </div>
        <div class="qual-detail-item">
          <span class="label">Status</span>
          <span class="value">${statusBadge(q.status || 'pending')}</span>
        </div>
      </div>
    </div>
  `;
}

/* Render results for the By Document verification mode (employer flow) */
function renderDocumentVerificationResult(result) {
  document.getElementById('verify-empty').classList.add('hidden');
  const resultEl = document.getElementById('verify-result');
  resultEl.classList.remove('hidden');

  const badge = document.getElementById('result-badge');
  const detailsEl = document.getElementById('result-details');
  const aiEl = document.getElementById('result-ai');
  const docEl = document.getElementById('result-document');

  // ── Badge ──
  let badgeText, badgeClass, toastMsg, toastType;
  if (result.status === 'found') {
    const isPass = result.is_authentic && result.result !== 'rejected';
    badgeClass = `result-badge ${isPass ? 'success' : 'fail'}`;
    badgeText = isPass ? `✓ Authentic — ${escapeHtml(result.result)}` : `✕ Not Authentic — ${escapeHtml(result.result)}`;
    toastMsg = isPass ? 'Verification passed!' : 'Verification failed';
    toastType = isPass ? 'success' : 'error';
  } else if (result.status === 'not_found') {
    badgeClass = 'result-badge fail';
    badgeText = '✕ No Matching Record Found';
    toastMsg = 'No matching credential found in the system';
    toastType = 'error';
  } else {
    badgeClass = 'result-badge';
    badgeText = '⚠ Unable to Verify';
    toastMsg = 'Could not extract a serial number from the document';
    toastType = 'error';
  }
  badge.className = badgeClass;
  badge.textContent = badgeText;

  // ── Extracted fields section ──
  const ef = result.extracted_fields || {};
  const methodLabel = result.extraction_method === 'openai_vision' ? 'AI Vision (GPT-4o)' : 'OCR + Pattern Matching';
  let html = `
    <div style="margin-top:4px;">
      <h4 style="font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:1px;color:var(--text-3);margin-bottom:10px;">
        Fields Read From Document <span style="text-transform:none;letter-spacing:0;font-weight:500;">(${escapeHtml(methodLabel)})</span>
      </h4>
      <div class="result-detail-row"><span class="result-detail-label">Candidate Name</span><span class="result-detail-value">${ef.holder_name ? escapeHtml(ef.holder_name) : '<span style="color:var(--text-3);">Not detected</span>'}</span></div>
      <div class="result-detail-row"><span class="result-detail-label">Institution</span><span class="result-detail-value">${ef.issuing_institution ? escapeHtml(ef.issuing_institution) : '<span style="color:var(--text-3);">Not detected</span>'}</span></div>
      <div class="result-detail-row"><span class="result-detail-label">Qualification / Programme</span><span class="result-detail-value">${ef.title ? escapeHtml(ef.title) : '<span style="color:var(--text-3);">Not detected</span>'}</span></div>
      ${ef.grade ? `<div class="result-detail-row"><span class="result-detail-label">Grade / Class</span><span class="result-detail-value">${escapeHtml(ef.grade)}</span></div>` : ''}
      <div class="result-detail-row"><span class="result-detail-label">Serial Number</span><span class="result-detail-value">${ef.serial_number ? escapeHtml(ef.serial_number) : '<span style="color:var(--red);">Not detected</span>'}</span></div>
      ${ef.registration_number ? `<div class="result-detail-row"><span class="result-detail-label">Registration Number</span><span class="result-detail-value">${escapeHtml(ef.registration_number)}</span></div>` : ''}
      ${ef.date_issued ? `<div class="result-detail-row"><span class="result-detail-label">Date Issued</span><span class="result-detail-value">${escapeHtml(ef.date_issued)}</span></div>` : ''}
      ${ef.holder_id_number ? `<div class="result-detail-row"><span class="result-detail-label">Holder ID Number</span><span class="result-detail-value">${escapeHtml(ef.holder_id_number)}</span></div>` : ''}
    </div>
  `;

  // ── Outcome message ──
  html += `<div class="result-detail-row" style="margin-top:12px;"><span class="result-detail-label">Outcome</span><span class="result-detail-value">${escapeHtml(result.message)}</span></div>`;

  // ── Full verification details (when found) ──
  if (result.status === 'found') {
    html += `
      <div class="result-detail-row"><span class="result-detail-label">Qualification ID</span><span class="result-detail-value">#${result.qualification_id}</span></div>
      <div class="result-detail-row"><span class="result-detail-label">Method</span><span class="result-detail-value">${escapeHtml(result.method)}</span></div>
      <div class="result-detail-row"><span class="result-detail-label">Verification Hash</span><span class="result-detail-value hash-value">${result.verification_hash ? escapeHtml(result.verification_hash) : 'Not assigned'}</span></div>
      <div class="result-detail-row"><span class="result-detail-label">AI Confidence</span><span class="result-detail-value">${result.ai_confidence_score != null ? result.ai_confidence_score + '%' : '—'}</span></div>
      ${result.verified_at ? `<div class="result-detail-row"><span class="result-detail-label">Verified At</span><span class="result-detail-value">${new Date(result.verified_at).toLocaleString()}</span></div>` : ''}
      ${result.checks ? renderChecks(result.checks) : ''}
      ${result.qualification ? renderQualificationDetails(result.qualification) : ''}
    `;
  }

  detailsEl.innerHTML = html;

  // ── AI analysis (when found) ──
  if (result.ai_analysis) {
    const ai = result.ai_analysis;
    let aiHtml = '<div style="margin-top:16px;padding-top:14px;border-top:1px solid var(--border);"><h4 style="font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:1px;color:var(--text-3);margin-bottom:10px;">AI Fraud Analysis</h4>';
    if (ai.recommendation) {
      const rec = ai.recommendation.toUpperCase();
      const cls = rec.includes('APPROVE') ? 'approve' : rec.includes('REJECT') ? 'reject' : 'review';
      const recColor = cls === 'approve' ? 'var(--green)' : cls === 'reject' ? 'var(--red)' : 'var(--amber)';
      aiHtml += `<div class="result-detail-row"><span class="result-detail-label">Recommendation</span><span class="result-detail-value" style="color:${recColor};font-weight:600;">${escapeHtml(ai.recommendation)}</span></div>`;
    }
    if (ai.risk_score != null) aiHtml += `<div class="result-detail-row"><span class="result-detail-label">Risk Score</span><span class="result-detail-value">${ai.risk_score}/100</span></div>`;
    if (ai.confidence_score != null) aiHtml += `<div class="result-detail-row"><span class="result-detail-label">Confidence</span><span class="result-detail-value">${ai.confidence_score}%</span></div>`;
    if (ai.anomalies && ai.anomalies.length > 0) {
      aiHtml += `<div class="result-detail-row"><span class="result-detail-label">Anomalies</span><span class="result-detail-value">${ai.anomalies.map(a => escapeHtml(a)).join('<br>')}</span></div>`;
    } else {
      aiHtml += `<div class="result-detail-row"><span class="result-detail-label">Anomalies</span><span class="result-detail-value" style="color:var(--green);">None detected</span></div>`;
    }
    aiHtml += '</div>';
    aiEl.innerHTML = aiHtml;
  } else {
    aiEl.innerHTML = '';
  }

  // ── Document match analysis (when found) ──
  if (result.document_analysis) {
    const da = result.document_analysis;
    let docHtml = '<div style="margin-top:16px;padding-top:14px;border-top:1px solid var(--border);"><h4 style="font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:1px;color:var(--text-3);margin-bottom:10px;">Document Match Analysis</h4>';
    if (da.data_match) {
      const dm = da.data_match;
      const recColor = dm.recommendation === 'APPROVE' ? 'var(--green)' : dm.recommendation === 'REJECT' ? 'var(--red)' : 'var(--amber)';
      docHtml += `<div class="result-detail-row"><span class="result-detail-label">Data Match Score</span><span class="result-detail-value" style="color:${recColor};font-weight:600;">${dm.match_score}% — ${escapeHtml(dm.recommendation)}</span></div>`;
      docHtml += `<div class="result-detail-row"><span class="result-detail-label">Summary</span><span class="result-detail-value">${escapeHtml(dm.summary)}</span></div>`;
      if (dm.checks && dm.checks.length > 0) {
        docHtml += '<div style="margin-top:8px;">';
        for (const c of dm.checks) {
          const icon = c.found_in_document ? '<span class="check-pass">✓</span>' : '<span class="check-fail">✕</span>';
          docHtml += `<div class="result-detail-row"><span class="result-detail-label">${escapeHtml(c.field)}</span><span class="result-detail-value">${icon} ${c.found_in_document ? 'Match' : 'Mismatch'} (registered: ${escapeHtml(c.registered)})</span></div>`;
        }
        docHtml += '</div>';
      }
    }
    if (da.extracted_text_preview) {
      docHtml += `<details style="margin-top:8px;"><summary style="cursor:pointer;font-size:12px;color:var(--text-3);font-weight:600;">Extracted Text Preview</summary><div style="margin-top:6px;padding:8px;background:var(--bg-2);border-radius:6px;font-size:11px;color:var(--text-3);white-space:pre-wrap;max-height:200px;overflow-y:auto;">${escapeHtml(da.extracted_text_preview)}</div></details>`;
    }
    docHtml += '</div>';
    docEl.innerHTML = docHtml;
  } else {
    docEl.innerHTML = '';
  }

  toast(toastMsg, toastType);

  if (result.status === 'found' && result.qualification_id) {
    loadVerifyHistory(result.qualification_id);
  } else {
    document.getElementById('verify-history').classList.add('hidden');
  }
}

/* ─────────── AI ANALYSIS ─────────── */
document.getElementById('ai-analyze-btn').addEventListener('click', async () => {
  const id = document.getElementById('ai-qual-id').value;
  if (!id) { toast('Enter a qualification ID', 'error'); return; }
  showLoading();
  try {
    const result = await api(`/ai/analyze/${id}`, { method: 'POST' });
    document.getElementById('ai-empty').classList.add('hidden');
    const el = document.getElementById('ai-result');
    el.classList.remove('hidden');

    let html = '';

    // Recommendation banner
    if (result.recommendation) {
      const rec = result.recommendation.toUpperCase();
      const cls = rec.includes('APPROVE') ? 'approve' : rec.includes('REJECT') ? 'reject' : 'review';
      html += `<div class="ai-card"><div class="rec-banner ${cls}">
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">${cls === 'approve' ? '<path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><path d="m9 11 3 3L22 4"/>' : cls === 'reject' ? '<circle cx="12" cy="12" r="10"/><path d="m15 9-6 6"/><path d="m9 9 6 6"/>' : '<path d="M12 8v4l3 3"/><circle cx="12" cy="12" r="10"/>'}</svg>
        ${escapeHtml(result.recommendation)}
      </div></div>`;
    }

    // Scores
    if (result.risk_score != null || result.confidence_score != null) {
      const risk = result.risk_score ?? 0;
      const conf = result.confidence_score ?? 0;
      const riskColor = risk >= 50 ? 'var(--red)' : risk >= 25 ? 'var(--amber)' : 'var(--green)';
      html += `<div class="ai-card"><h4>Risk Assessment</h4>
        <div class="risk-gauge-row">
          <span style="font-size:13px;color:var(--text-2);font-weight:600;">Risk Score</span>
          <div class="risk-bar"><div class="risk-fill" style="width:${Math.max(risk, 2)}%;background:${riskColor};"></div></div>
          <strong style="font-size:15px;color:${riskColor};">${risk}/100</strong>
        </div>
        <div class="conf-grid" style="margin-top:16px;">
          <div class="conf-item"><strong style="color:var(--green);">${conf}%</strong><span>Confidence</span></div>
          <div class="conf-item"><strong>${escapeHtml(result.method || 'heuristic')}</strong><span>Engine</span></div>
        </div>
      </div>`;
    }

    // Anomalies
    if (result.anomalies && result.anomalies.length > 0) {
      html += `<div class="ai-card"><h4>Anomalies Detected (${result.anomalies.length})</h4><ul class="anomaly-list">
        ${result.anomalies.map(a => `<li>
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="m21.73 18-8-14a2 2 0 0 0-3.48 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3z"/><path d="M12 9v4"/><path d="M12 17h.01"/></svg>
          ${escapeHtml(a)}
        </li>`).join('')}
      </ul></div>`;
    } else if (result.anomalies) {
      html += `<div class="ai-card"><h4>Anomalies Detected</h4><p style="font-size:13px;color:var(--green);font-weight:600;">✓ No anomalies found — credential appears clean.</p></div>`;
    }

    // Meta
    html += `<div class="ai-card"><h4>Analysis Meta</h4>
      <div class="result-detail-row"><span class="result-detail-label">Qualification ID</span><span class="result-detail-value">#${result.qualification_id}</span></div>
      <div class="result-detail-row"><span class="result-detail-label">Result</span><span class="result-detail-value">${escapeHtml(result.result || '—')}</span></div>
      <div class="result-detail-row"><span class="result-detail-label">Analyzed At</span><span class="result-detail-value">${new Date(result.verified_at).toLocaleString()}</span></div>
    </div>`;

    el.innerHTML = html;
    toast('AI analysis complete', 'success');
  } catch (err) {
    toast(err.message, 'error');
  } finally {
    hideLoading();
  }
});

/* ─────────── AUDIT LOGS ─────────── */
async function loadAuditLogs(page = 1) {
  auditPage = page;
  const actionFilter = document.getElementById('audit-action-filter').value;
  let params = `page=${page}&page_size=${PAGE_SIZE}`;
  if (actionFilter) params += `&action=${encodeURIComponent(actionFilter)}`;

  const container = document.getElementById('audit-table');
  try {
    const data = await api(`/audit-logs/?${params}`);
    if (data.items.length === 0) {
      container.innerHTML = emptyState(null, 'No audit entries', 'System actions will appear here as an immutable trail.');
    } else {
      const actionBadges = {
        create: 'badge-role',
        verify: 'badge-pending',
        update: 'badge-role',
        delete: 'badge-rejected',
        ai_analysis: 'badge-pending',
        login: 'badge-verified',
        logout: 'badge-role',
      };
      let html = `<table><thead><tr>
        <th>ID</th><th>Action</th><th>Entity</th><th>Description</th><th>User</th><th>Timestamp</th>
      </tr></thead><tbody>`;
      for (const log of data.items) {
        html += `<tr>
          <td>#${log.id}</td>
          <td><span class="badge ${actionBadges[log.action] || 'badge-role'}">${escapeHtml(log.action)}</span></td>
          <td>${escapeHtml(log.entity_type)}${log.entity_id ? ` #${log.entity_id}` : ''}</td>
          <td>${escapeHtml(log.description)}</td>
          <td>${log.user_id ? 'User #' + log.user_id : 'System'}</td>
          <td>${new Date(log.created_at).toLocaleString()}</td>
        </tr>`;
      }
      html += '</tbody></table>';
      container.innerHTML = html;
    }
    renderPagination('audit-pagination', data.page, data.total_pages, loadAuditLogs);
  } catch (err) {
    container.innerHTML = emptyState(null, 'Failed to load', err.message);
    toast(err.message, 'error');
  }
}

document.getElementById('audit-action-filter').addEventListener('change', () => loadAuditLogs(1));
document.getElementById('audit-refresh').addEventListener('click', () => {
  loadAuditLogs(auditPage);
  toast('Audit log refreshed', 'info');
});

/* ─────────── USER MANAGEMENT ─────────── */
async function loadUsers() {
  const container = document.getElementById('users-table');
  try {
    const users = await api('/auth/users');
    if (users.length === 0) {
      container.innerHTML = emptyState(null, 'No users', 'Create users to grant system access.');
      return;
    }
    let html = `<table><thead><tr>
      <th>ID</th><th>Name</th><th>Email</th><th>Role</th><th>Status</th><th>Joined</th><th style="text-align:right;">Actions</th>
    </tr></thead><tbody>`;
    for (const u of users) {
      const roleBadge = u.role === 'admin' ? 'badge-verified' : u.role === 'verifier' ? 'badge-pending' : 'badge-role';
      const statusBadge = u.is_active
        ? '<span class="badge badge-verified">Active</span>'
        : '<span class="badge badge-rejected">Inactive</span>';
      const isSelf = currentUser && u.id === currentUser.id;
      let actions = '<td><div class="action-btns" style="justify-content:flex-end;">';
      actions += `<select class="select-sm" onchange="changeRole(${u.id}, this.value)" ${isSelf ? 'disabled' : ''}>`;
      for (const r of ['viewer', 'verifier', 'admin']) {
        actions += `<option value="${r}" ${u.role === r ? 'selected' : ''}>${r}</option>`;
      }
      actions += '</select>';
      if (!isSelf) {
        if (u.is_active) {
          actions += `<button class="action-btn danger" onclick="deactivateUser(${u.id})">Deactivate</button>`;
        } else {
          actions += `<button class="action-btn success" onclick="activateUser(${u.id})">Activate</button>`;
        }
      }
      actions += '</div></td>';
      html += `<tr>
        <td>#${u.id}</td>
        <td class="title-cell">${escapeHtml(u.full_name)}${isSelf ? ' <span style="color:var(--text-3);font-size:11px;">(you)</span>' : ''}</td>
        <td>${escapeHtml(u.email)}</td>
        <td><span class="badge ${roleBadge}">${escapeHtml(u.role)}</span></td>
        <td>${statusBadge}</td>
        <td>${new Date(u.created_at).toLocaleDateString()}</td>
        ${actions}
      </tr>`;
    }
    html += '</tbody></table>';
    container.innerHTML = html;
  } catch (err) {
    container.innerHTML = emptyState(null, 'Failed to load', err.message);
    toast(err.message, 'error');
  }
}

window.changeRole = async function(userId, newRole) {
  showLoading();
  try {
    await api(`/auth/users/${userId}/role?role=${encodeURIComponent(newRole)}`, { method: 'PUT' });
    toast(`Role changed to ${newRole}`, 'success');
    loadUsers();
  } catch (err) {
    toast(err.message, 'error');
    loadUsers();
  } finally {
    hideLoading();
  }
};

window.deactivateUser = async function(userId) {
  if (!confirm('Deactivate this account? The user will be unable to sign in.')) return;
  showLoading();
  try {
    await api(`/auth/users/${userId}/deactivate`, { method: 'PUT' });
    toast('User deactivated', 'success');
    loadUsers();
  } catch (err) {
    toast(err.message, 'error');
  } finally {
    hideLoading();
  }
};

window.activateUser = async function(userId) {
  showLoading();
  try {
    await api(`/auth/users/${userId}/activate`, { method: 'PUT' });
    toast('User activated', 'success');
    loadUsers();
  } catch (err) {
    toast(err.message, 'error');
  } finally {
    hideLoading();
  }
};

/* User modal */
const userModal = document.getElementById('user-modal-overlay');
function closeUserModal() { userModal.classList.add('hidden'); }
document.getElementById('add-user-btn').addEventListener('click', () => userModal.classList.remove('hidden'));
document.getElementById('user-modal-close').addEventListener('click', closeUserModal);
document.getElementById('user-modal-cancel').addEventListener('click', closeUserModal);
userModal.addEventListener('click', (e) => { if (e.target === userModal) closeUserModal(); });
window.closeUserModal = closeUserModal;

document.getElementById('user-form').addEventListener('submit', async (e) => {
  e.preventDefault();
  const body = {
    email: document.getElementById('u-email').value.trim(),
    full_name: document.getElementById('u-name').value.trim(),
    password: document.getElementById('u-password').value,
    role: document.getElementById('u-role').value,
  };
  showLoading();
  try {
    await api('/auth/users', { method: 'POST', body });
    toast(`User created as ${body.role}`, 'success');
    closeUserModal();
    e.target.reset();
    loadUsers();
  } catch (err) {
    toast(err.message, 'error');
  } finally {
    hideLoading();
  }
});

/* ─────────── PAGINATION ─────────── */
function renderPagination(containerId, current, total, callback) {
  const el = document.getElementById(containerId);
  if (total <= 1) { el.innerHTML = ''; return; }
  let html = `<button class="page-btn" ${current <= 1 ? 'disabled' : ''} data-pg="${current - 1}">‹ Prev</button>`;
  for (let i = 1; i <= total; i++) {
    if (i === 1 || i === total || (i >= current - 1 && i <= current + 1)) {
      html += `<button class="page-btn ${i === current ? 'active' : ''}" data-pg="${i}">${i}</button>`;
    } else if (i === current - 2 || i === current + 2) {
      html += `<span class="page-btn" style="border:none;background:none;cursor:default;">…</span>`;
    }
  }
  html += `<button class="page-btn" ${current >= total ? 'disabled' : ''} data-pg="${current + 1}">Next ›</button>`;
  el.innerHTML = html;
  el.querySelectorAll('.page-btn[data-pg]').forEach(btn => {
    btn.addEventListener('click', () => {
      if (!btn.disabled) callback(parseInt(btn.dataset.pg));
    });
  });
}

/* ─────────── EMPTY STATE HELPER ─────────── */
function emptyState(_, title, desc) {
  return `<div class="empty-state">
    <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M22 10v6M2 10l10-5 10 5-10 5z"/><path d="M6 12v5c3 3 9 3 12 0v-5"/></svg>
    <strong>${escapeHtml(title)}</strong>
    <span>${escapeHtml(desc)}</span>
  </div>`;
}

/* ─────────── UTILS ─────────── */
function escapeHtml(str) {
  if (str == null) return '';
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}

/* ─────────── INIT ─────────── */
async function initApp() {
  document.getElementById('auth-page').classList.add('hidden');
  document.getElementById('app').classList.remove('hidden');
  document.getElementById('page-date').textContent = new Date().toLocaleDateString(undefined, {
    weekday: 'long', year: 'numeric', month: 'long', day: 'numeric',
  });
  await loadCurrentUser();
  navigateTo('dashboard');
}

if (token) {
  initApp().catch(() => {});
}
