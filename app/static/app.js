/* ═══════════════════════════════════════════════════════════
   LICENSE KEY MANAGER — Application Logic
   Pure Vanilla JavaScript • No Dependencies
   ═══════════════════════════════════════════════════════════ */

(() => {
    'use strict';

    // ══════════════════════════════════════════════════════
    // API CLIENT
    // ══════════════════════════════════════════════════════
    class ApiClient {
        constructor() {
            this.baseUrl = window.location.origin;
            this.token = localStorage.getItem('lkm_token') || null;
        }

        setToken(token) {
            this.token = token;
            if (token) {
                localStorage.setItem('lkm_token', token);
            } else {
                localStorage.removeItem('lkm_token');
            }
        }

        async request(method, path, body = null, options = {}) {
            const url = `${this.baseUrl}${path}`;
            const headers = {
                'Content-Type': 'application/json',
                ...options.headers,
            };

            if (this.token) {
                headers['Authorization'] = `Bearer ${this.token}`;
            }

            const config = { method, headers };
            if (body && method !== 'GET') {
                config.body = JSON.stringify(body);
            }

            try {
                const response = await fetch(url, config);
                const data = await response.json().catch(() => ({}));

                if (!response.ok) {
                    const errMsg = data.detail || data.message || `Request failed (${response.status})`;
                    throw new Error(errMsg);
                }

                return data;
            } catch (err) {
                if (err.message === 'Failed to fetch') {
                    throw new Error('Network error. Please check your connection.');
                }
                throw err;
            }
        }

        get(path) { return this.request('GET', path); }
        post(path, body) { return this.request('POST', path, body); }
        put(path, body) { return this.request('PUT', path, body); }
        delete(path) { return this.request('DELETE', path); }

        // Auth
        login(username, password) {
            return this.post('/api/auth/login', { username, password });
        }
        getMe() {
            return this.get('/api/auth/me');
        }
        changePassword(current_password, new_password) {
            return this.put('/api/auth/change-password', { current_password, new_password });
        }

        // Keys
        generateKeys(data) {
            return this.post('/api/keys/generate', data);
        }
        listKeys(page = 1, perPage = 20, status = 'all', search = '') {
            const params = new URLSearchParams({ page, per_page: perPage, status, search });
            return this.get(`/api/keys/list?${params}`);
        }
        revokeKey(key) {
            return this.put(`/api/keys/revoke/${encodeURIComponent(key)}`);
        }
        deleteKey(key) {
            return this.delete(`/api/keys/delete/${encodeURIComponent(key)}`);
        }
        updateKey(key, data) {
            return this.put(`/api/keys/update/${encodeURIComponent(key)}`, data);
        }

        // Users
        createUser(data) {
            return this.post('/api/users/create', data);
        }
        listUsers() {
            return this.get('/api/users/list');
        }
        deleteUser(userId) {
            return this.delete(`/api/users/delete/${userId}`);
        }
        updateUser(userId, data) {
            return this.put(`/api/users/update/${userId}`, data);
        }

        // Stats
        getStats() {
            return this.get('/api/stats');
        }
    }

    // ══════════════════════════════════════════════════════
    // TOAST NOTIFICATION SYSTEM
    // ══════════════════════════════════════════════════════
    const Toast = {
        container: null,

        init() {
            this.container = document.getElementById('toast-container');
        },

        show(message, type = 'info', duration = 3500) {
            const icons = {
                success: '✅',
                error: '❌',
                warning: '⚠️',
                info: 'ℹ️',
            };

            const toast = document.createElement('div');
            toast.className = `toast toast-${type}`;
            toast.style.setProperty('--toast-duration', `${duration}ms`);
            toast.innerHTML = `
                <span class="toast-icon">${icons[type] || icons.info}</span>
                <span class="toast-message">${this.escapeHtml(message)}</span>
            `;

            this.container.appendChild(toast);

            setTimeout(() => {
                if (toast.parentNode) toast.remove();
            }, duration + 400);
        },

        success(msg) { this.show(msg, 'success'); },
        error(msg) { this.show(msg, 'error', 5000); },
        warning(msg) { this.show(msg, 'warning'); },
        info(msg) { this.show(msg, 'info'); },

        escapeHtml(str) {
            const div = document.createElement('div');
            div.textContent = str;
            return div.innerHTML;
        }
    };

    // ══════════════════════════════════════════════════════
    // MODAL SYSTEM
    // ══════════════════════════════════════════════════════
    const Modal = {
        el: null,
        overlay: null,
        content: null,

        init() {
            this.el = document.getElementById('modal');
            this.overlay = document.getElementById('modal-overlay');
            this.content = document.getElementById('modal-content');
            this.overlay.addEventListener('click', () => this.hide());
        },

        show(html) {
            this.content.innerHTML = html;
            this.el.style.display = 'flex';
            document.body.style.overflow = 'hidden';

            // Attach close buttons
            this.content.querySelectorAll('[data-modal-close]').forEach(btn => {
                btn.addEventListener('click', () => this.hide());
            });
        },

        hide() {
            this.el.style.display = 'none';
            document.body.style.overflow = '';
        }
    };

    // ══════════════════════════════════════════════════════
    // CONFIRM DIALOG
    // ══════════════════════════════════════════════════════
    const Confirm = {
        el: null,
        overlay: null,
        content: null,

        init() {
            this.el = document.getElementById('confirm-dialog');
            this.overlay = document.getElementById('confirm-overlay');
            this.content = document.getElementById('confirm-content');
        },

        show({ icon = '⚠️', title, message, confirmText = 'Confirm', confirmClass = 'btn-danger', onConfirm }) {
            this.content.innerHTML = `
                <div class="confirm-icon">${icon}</div>
                <div class="confirm-title">${title}</div>
                <div class="confirm-message">${message}</div>
                <div class="confirm-actions">
                    <button class="btn btn-secondary" id="confirm-cancel">Cancel</button>
                    <button class="btn ${confirmClass}" id="confirm-ok">${confirmText}</button>
                </div>
            `;
            this.el.style.display = 'flex';
            document.body.style.overflow = 'hidden';

            document.getElementById('confirm-cancel').addEventListener('click', () => this.hide());
            this.overlay.addEventListener('click', () => this.hide(), { once: true });
            document.getElementById('confirm-ok').addEventListener('click', () => {
                this.hide();
                onConfirm();
            });
        },

        hide() {
            this.el.style.display = 'none';
            document.body.style.overflow = '';
        }
    };

    // ══════════════════════════════════════════════════════
    // HELPERS
    // ══════════════════════════════════════════════════════
    function formatDate(dateStr) {
        if (!dateStr) return '—';
        try {
            const d = new Date(dateStr);
            if (isNaN(d.getTime())) return dateStr;
            return d.toLocaleDateString('en-US', {
                year: 'numeric', month: 'short', day: 'numeric',
                hour: '2-digit', minute: '2-digit',
            });
        } catch {
            return dateStr;
        }
    }

    function timeAgo(dateStr) {
        if (!dateStr) return '—';
        try {
            const d = new Date(dateStr);
            if (isNaN(d.getTime())) return dateStr;
            const now = new Date();
            const seconds = Math.floor((now - d) / 1000);

            if (seconds < 60) return 'Just now';
            const minutes = Math.floor(seconds / 60);
            if (minutes < 60) return `${minutes}m ago`;
            const hours = Math.floor(minutes / 60);
            if (hours < 24) return `${hours}h ago`;
            const days = Math.floor(hours / 24);
            if (days < 30) return `${days}d ago`;
            const months = Math.floor(days / 30);
            if (months < 12) return `${months}mo ago`;
            return `${Math.floor(months / 12)}y ago`;
        } catch {
            return dateStr;
        }
    }

    function debounce(fn, delay) {
        let timer;
        return (...args) => {
            clearTimeout(timer);
            timer = setTimeout(() => fn(...args), delay);
        };
    }

    function animateCounter(element, target, duration = 1200) {
        const start = parseInt(element.textContent, 10) || 0;
        if (start === target) return;
        const startTime = performance.now();

        function update(currentTime) {
            const elapsed = currentTime - startTime;
            const progress = Math.min(elapsed / duration, 1);
            // ease-out cubic
            const eased = 1 - Math.pow(1 - progress, 3);
            element.textContent = Math.floor(start + (target - start) * eased).toLocaleString();
            if (progress < 1) {
                requestAnimationFrame(update);
            } else {
                element.textContent = target.toLocaleString();
            }
        }
        requestAnimationFrame(update);
    }

    async function copyToClipboard(text, btnEl) {
        try {
            await navigator.clipboard.writeText(text);
            if (btnEl) {
                const orig = btnEl.textContent;
                btnEl.textContent = '✓ Copied';
                btnEl.classList.add('copied');
                setTimeout(() => {
                    btnEl.textContent = orig;
                    btnEl.classList.remove('copied');
                }, 1500);
            }
            Toast.success('Copied to clipboard');
        } catch {
            Toast.error('Failed to copy');
        }
    }

    function escapeHtml(str) {
        if (!str) return '';
        const div = document.createElement('div');
        div.textContent = str;
        return div.innerHTML;
    }

    // ══════════════════════════════════════════════════════
    // APPLICATION STATE
    // ══════════════════════════════════════════════════════
    const State = {
        user: null,
        keys: [],
        keysTotal: 0,
        keysPage: 1,
        keysPerPage: 20,
        keysFilter: 'all',
        keysSearch: '',
        users: [],
        stats: {},
        currentView: 'dashboard',
    };

    const api = new ApiClient();

    // ══════════════════════════════════════════════════════
    // DOM REFERENCES
    // ══════════════════════════════════════════════════════
    const $ = (sel) => document.querySelector(sel);
    const $$ = (sel) => document.querySelectorAll(sel);

    const DOM = {
        loginPage: $('#login-page'),
        appLayout: $('#app-layout'),
        loginForm: $('#login-form'),
        loginUsername: $('#login-username'),
        loginPassword: $('#login-password'),
        loginError: $('#login-error'),
        loginBtn: $('#login-btn'),
        sidebar: $('#sidebar'),
        sidebarOverlay: $('#sidebar-overlay'),
        menuToggle: $('#menu-toggle'),
        topbarTitle: $('#topbar-title'),
        topbarUsername: $('#topbar-username'),
        topbarRole: $('#topbar-role'),
        logoutBtn: $('#logout-btn'),
        navUsers: $('#nav-users'),
        keysSearch: $('#keys-search'),
        filterTabs: $('#filter-tabs'),
        keysTbody: $('#keys-tbody'),
        keysEmpty: $('#keys-empty'),
        keysLoading: $('#keys-loading'),
        keysPagination: $('#keys-pagination'),
        generateForm: $('#generate-form'),
        genBtn: $('#gen-btn'),
        generatedPanel: $('#generated-keys-panel'),
        generatedList: $('#generated-keys-list'),
        copyAllBtn: $('#copy-all-btn'),
        addUserBtn: $('#add-user-btn'),
        usersTbody: $('#users-tbody'),
        usersLoading: $('#users-loading'),
        passwordForm: $('#password-form'),
        settingsUsername: $('#settings-username'),
        settingsRole: $('#settings-role'),
    };

    // ══════════════════════════════════════════════════════
    // ROUTER
    // ══════════════════════════════════════════════════════
    const Router = {
        views: ['dashboard', 'keys', 'generate', 'users', 'settings'],
        titles: {
            dashboard: 'Dashboard',
            keys: 'License Keys',
            generate: 'Generate Keys',
            users: 'User Management',
            settings: 'Settings',
        },

        init() {
            window.addEventListener('hashchange', () => this.navigate());
            this.navigate();
        },

        navigate() {
            const hash = (window.location.hash || '#dashboard').replace('#', '');
            const view = this.views.includes(hash) ? hash : 'dashboard';

            // Role check: only owners see users
            if (view === 'users' && State.user?.role !== 'owner') {
                window.location.hash = '#dashboard';
                return;
            }

            State.currentView = view;
            this.render(view);
        },

        render(view) {
            // Update sidebar active
            $$('.sidebar-item').forEach(item => {
                item.classList.toggle('active', item.dataset.view === view);
            });

            // Update views
            $$('.view').forEach(v => v.classList.remove('active'));
            const viewEl = $(`#view-${view}`);
            if (viewEl) viewEl.classList.add('active');

            // Update topbar title
            DOM.topbarTitle.textContent = this.titles[view] || 'Dashboard';

            // Close mobile sidebar
            DOM.sidebar.classList.remove('open');
            DOM.sidebarOverlay.classList.remove('visible');

            // Trigger data load
            switch (view) {
                case 'dashboard': loadStats(); break;
                case 'keys': loadKeys(); break;
                case 'users': loadUsers(); break;
                case 'settings': renderSettings(); break;
            }
        }
    };

    // ══════════════════════════════════════════════════════
    // AUTH
    // ══════════════════════════════════════════════════════
    async function checkAuth() {
        if (!api.token) {
            showLogin();
            return;
        }

        try {
            const user = await api.getMe();
            State.user = user;
            showApp();
        } catch {
            api.setToken(null);
            showLogin();
        }
    }

    function showLogin() {
        DOM.loginPage.style.display = 'flex';
        DOM.appLayout.style.display = 'none';
        DOM.loginUsername.focus();
    }

    function showApp() {
        DOM.loginPage.style.display = 'none';
        DOM.appLayout.style.display = 'flex';

        // Populate user info
        DOM.topbarUsername.textContent = State.user.username;
        DOM.topbarRole.textContent = State.user.role;
        DOM.topbarRole.className = `role-badge ${State.user.role}`;

        // Show/hide users nav based on role
        DOM.navUsers.classList.toggle('hidden', State.user.role !== 'owner');

        Router.init();
    }

    async function handleLogin(e) {
        e.preventDefault();
        const username = DOM.loginUsername.value.trim();
        const password = DOM.loginPassword.value;

        if (!username || !password) {
            showLoginError('Please enter username and password');
            return;
        }

        setLoginLoading(true);
        DOM.loginError.style.display = 'none';

        try {
            const data = await api.login(username, password);
            api.setToken(data.access_token);
            State.user = {
                username: data.username || username,
                role: data.role || 'admin',
            };
            DOM.loginForm.reset();
            showApp();
            Toast.success(`Welcome back, ${State.user.username}!`);
        } catch (err) {
            showLoginError(err.message || 'Login failed');
        } finally {
            setLoginLoading(false);
        }
    }

    function showLoginError(msg) {
        DOM.loginError.textContent = msg;
        DOM.loginError.style.display = 'block';
    }

    function setLoginLoading(loading) {
        const btn = DOM.loginBtn;
        btn.disabled = loading;
        btn.querySelector('.btn-text').style.display = loading ? 'none' : '';
        btn.querySelector('.btn-loader').style.display = loading ? 'inline-block' : 'none';
    }

    function handleLogout() {
        api.setToken(null);
        State.user = null;
        State.keys = [];
        State.users = [];
        State.stats = {};
        window.location.hash = '';
        showLogin();
        Toast.info('Logged out successfully');
    }

    // ══════════════════════════════════════════════════════
    // DASHBOARD / STATS
    // ══════════════════════════════════════════════════════
    async function loadStats() {
        try {
            const stats = await api.getStats();
            State.stats = stats;

            const fields = ['total_keys', 'active_keys', 'expired_keys', 'revoked_keys', 'total_users', 'total_validations'];
            fields.forEach(field => {
                const el = $(`[data-stat="${field}"]`);
                if (el) {
                    animateCounter(el, stats[field] || 0);
                }
            });
        } catch (err) {
            Toast.error('Failed to load stats: ' + err.message);
        }
    }

    // ══════════════════════════════════════════════════════
    // KEYS MANAGEMENT
    // ══════════════════════════════════════════════════════
    async function loadKeys() {
        DOM.keysLoading.style.display = 'flex';
        DOM.keysTbody.innerHTML = '';
        DOM.keysEmpty.style.display = 'none';

        try {
            const data = await api.listKeys(
                State.keysPage,
                State.keysPerPage,
                State.keysFilter,
                State.keysSearch
            );

            State.keys = data.keys || [];
            State.keysTotal = data.total || 0;

            DOM.keysLoading.style.display = 'none';

            if (State.keys.length === 0) {
                DOM.keysEmpty.style.display = 'block';
                DOM.keysPagination.innerHTML = '';
                return;
            }

            renderKeysTable();
            renderKeysPagination(data.total, data.page, data.per_page);
        } catch (err) {
            DOM.keysLoading.style.display = 'none';
            Toast.error('Failed to load keys: ' + err.message);
        }
    }

    function renderKeysTable() {
        const role = State.user?.role;
        const canRevoke = role === 'owner' || role === 'admin';
        const canDelete = role === 'owner';

        DOM.keysTbody.innerHTML = State.keys.map((k, i) => `
            <tr class="table-row" data-key="${escapeHtml(k.key)}" style="animation-delay: ${i * 30}ms">
                <td>
                    <span class="key-display" title="${escapeHtml(k.key)}">${escapeHtml(k.key)}</span>
                </td>
                <td><span class="status-badge ${k.status}">${k.status}</span></td>
                <td title="${formatDate(k.created_at)}">${timeAgo(k.created_at)}</td>
                <td>${formatDate(k.expires_at)}</td>
                <td><span class="td-hwid" title="${escapeHtml(k.hwid || '')}">${escapeHtml(k.hwid || '—')}</span></td>
                <td>${escapeHtml(k.created_by || '—')}</td>
                <td>${k.validation_count || 0}</td>
                <td>
                    <div class="actions-cell" onclick="event.stopPropagation()">
                        <button class="copy-btn" onclick="App.copyKey('${escapeHtml(k.key)}', this)" title="Copy key">📋</button>
                        ${canRevoke && k.status === 'active' ? `<button class="btn btn-warning btn-sm" onclick="App.revokeKey('${escapeHtml(k.key)}')" title="Revoke">⛔</button>` : ''}
                        ${canDelete ? `<button class="btn btn-danger btn-sm" onclick="App.deleteKey('${escapeHtml(k.key)}')" title="Delete">🗑️</button>` : ''}
                        <button class="btn btn-secondary btn-sm" onclick="App.editKey('${escapeHtml(k.key)}')" title="Edit">✏️</button>
                    </div>
                </td>
            </tr>
        `).join('');

        // Row click => detail modal
        DOM.keysTbody.querySelectorAll('.table-row').forEach(row => {
            row.addEventListener('click', () => {
                const key = row.dataset.key;
                const keyObj = State.keys.find(k => k.key === key);
                if (keyObj) showKeyDetail(keyObj);
            });
        });
    }

    function renderKeysPagination(total, currentPage, perPage) {
        const totalPages = Math.ceil(total / perPage);
        if (totalPages <= 1) {
            DOM.keysPagination.innerHTML = '';
            return;
        }

        let html = '';
        html += `<button ${currentPage <= 1 ? 'disabled' : ''} onclick="App.goToPage(${currentPage - 1})">‹ Prev</button>`;

        const maxVisible = 5;
        let startPage = Math.max(1, currentPage - Math.floor(maxVisible / 2));
        let endPage = Math.min(totalPages, startPage + maxVisible - 1);
        if (endPage - startPage + 1 < maxVisible) {
            startPage = Math.max(1, endPage - maxVisible + 1);
        }

        if (startPage > 1) {
            html += `<button onclick="App.goToPage(1)">1</button>`;
            if (startPage > 2) html += `<span class="pagination-info">…</span>`;
        }

        for (let i = startPage; i <= endPage; i++) {
            html += `<button class="${i === currentPage ? 'active' : ''}" onclick="App.goToPage(${i})">${i}</button>`;
        }

        if (endPage < totalPages) {
            if (endPage < totalPages - 1) html += `<span class="pagination-info">…</span>`;
            html += `<button onclick="App.goToPage(${totalPages})">${totalPages}</button>`;
        }

        html += `<button ${currentPage >= totalPages ? 'disabled' : ''} onclick="App.goToPage(${currentPage + 1})">Next ›</button>`;
        html += `<span class="pagination-info">${total} total</span>`;

        DOM.keysPagination.innerHTML = html;
    }

    function showKeyDetail(k) {
        Modal.show(`
            <div class="modal-header">
                <h2 class="modal-title">Key Details</h2>
                <button class="modal-close" data-modal-close>✕</button>
            </div>
            <div class="modal-body">
                <div class="detail-item full-width">
                    <span class="detail-label">License Key</span>
                    <span class="detail-value mono">${escapeHtml(k.key)}</span>
                </div>
                <div class="detail-grid">
                    <div class="detail-item">
                        <span class="detail-label">Status</span>
                        <span class="detail-value"><span class="status-badge ${k.status}">${k.status}</span></span>
                    </div>
                    <div class="detail-item">
                        <span class="detail-label">Validations</span>
                        <span class="detail-value">${k.validation_count || 0}</span>
                    </div>
                    <div class="detail-item">
                        <span class="detail-label">Created At</span>
                        <span class="detail-value">${formatDate(k.created_at)}</span>
                    </div>
                    <div class="detail-item">
                        <span class="detail-label">Expires At</span>
                        <span class="detail-value">${formatDate(k.expires_at)}</span>
                    </div>
                    <div class="detail-item">
                        <span class="detail-label">Created By</span>
                        <span class="detail-value">${escapeHtml(k.created_by || '—')}</span>
                    </div>
                    <div class="detail-item">
                        <span class="detail-label">Last Validated</span>
                        <span class="detail-value">${formatDate(k.last_validated)}</span>
                    </div>
                    <div class="detail-item full-width">
                        <span class="detail-label">HWID</span>
                        <span class="detail-value mono">${escapeHtml(k.hwid || 'Not bound')}</span>
                    </div>
                    <div class="detail-item full-width">
                        <span class="detail-label">Notes</span>
                        <span class="detail-value">${escapeHtml(k.notes || 'No notes')}</span>
                    </div>
                </div>
            </div>
            <div class="modal-footer">
                <button class="btn btn-secondary" data-modal-close>Close</button>
                <button class="btn btn-primary" onclick="App.copyKey('${escapeHtml(k.key)}', this)">📋 Copy Key</button>
            </div>
        `);
    }

    // ══════════════════════════════════════════════════════
    // KEY ACTIONS
    // ══════════════════════════════════════════════════════
    function revokeKey(key) {
        Confirm.show({
            icon: '⛔',
            title: 'Revoke Key',
            message: `Are you sure you want to revoke this key?<br><code style="font-family: 'JetBrains Mono', monospace; font-size: 0.8rem; color: var(--text-primary);">${escapeHtml(key)}</code>`,
            confirmText: 'Revoke',
            confirmClass: 'btn-warning',
            async onConfirm() {
                try {
                    await api.revokeKey(key);
                    Toast.success('Key revoked successfully');
                    loadKeys();
                } catch (err) {
                    Toast.error('Failed to revoke: ' + err.message);
                }
            }
        });
    }

    function deleteKey(key) {
        Confirm.show({
            icon: '🗑️',
            title: 'Delete Key',
            message: `This action is irreversible. Delete this key?<br><code style="font-family: 'JetBrains Mono', monospace; font-size: 0.8rem; color: var(--text-primary);">${escapeHtml(key)}</code>`,
            confirmText: 'Delete',
            confirmClass: 'btn-danger',
            async onConfirm() {
                try {
                    await api.deleteKey(key);
                    Toast.success('Key deleted successfully');
                    loadKeys();
                } catch (err) {
                    Toast.error('Failed to delete: ' + err.message);
                }
            }
        });
    }

    function editKey(key) {
        const keyObj = State.keys.find(k => k.key === key);
        if (!keyObj) return;

        const expVal = keyObj.expires_at ? new Date(keyObj.expires_at).toISOString().slice(0, 16) : '';

        Modal.show(`
            <div class="modal-header">
                <h2 class="modal-title">Edit Key</h2>
                <button class="modal-close" data-modal-close>✕</button>
            </div>
            <div class="modal-body">
                <div class="detail-item full-width">
                    <span class="detail-label">Key</span>
                    <span class="detail-value mono">${escapeHtml(key)}</span>
                </div>
                <div class="form-group">
                    <label class="form-label" for="edit-expiry">Expiry Date</label>
                    <input type="datetime-local" id="edit-expiry" class="form-input" value="${expVal}">
                </div>
                <div class="form-group">
                    <label class="form-label" for="edit-notes">Notes</label>
                    <textarea id="edit-notes" class="form-input form-textarea" rows="3">${escapeHtml(keyObj.notes || '')}</textarea>
                </div>
            </div>
            <div class="modal-footer">
                <button class="btn btn-secondary" data-modal-close>Cancel</button>
                <button class="btn btn-primary" id="save-edit-btn">💾 Save Changes</button>
            </div>
        `);

        document.getElementById('save-edit-btn').addEventListener('click', async () => {
            const expires_at = document.getElementById('edit-expiry').value || null;
            const notes = document.getElementById('edit-notes').value;

            try {
                await api.updateKey(key, { expires_at, notes });
                Toast.success('Key updated successfully');
                Modal.hide();
                loadKeys();
            } catch (err) {
                Toast.error('Failed to update: ' + err.message);
            }
        });
    }

    // ══════════════════════════════════════════════════════
    // KEY GENERATION
    // ══════════════════════════════════════════════════════
    async function handleGenerate(e) {
        e.preventDefault();

        const prefix = document.getElementById('gen-prefix').value.trim() || 'LIC';
        const quantity = parseInt(document.getElementById('gen-quantity').value, 10);
        const expires_at = document.getElementById('gen-expiry').value || null;
        const notes = document.getElementById('gen-notes').value.trim() || null;

        if (quantity < 1 || quantity > 100) {
            Toast.warning('Quantity must be between 1 and 100');
            return;
        }

        setGenerateLoading(true);

        try {
            const result = await api.generateKeys({ quantity, expires_at, notes, prefix });
            const keys = Array.isArray(result) ? result : (result.keys || [result]);

            renderGeneratedKeys(keys);
            Toast.success(`Generated ${keys.length} key(s) successfully!`);
        } catch (err) {
            Toast.error('Generation failed: ' + err.message);
        } finally {
            setGenerateLoading(false);
        }
    }

    function setGenerateLoading(loading) {
        const btn = DOM.genBtn;
        btn.disabled = loading;
        btn.querySelector('.btn-text').style.display = loading ? 'none' : '';
        btn.querySelector('.btn-loader').style.display = loading ? 'inline-block' : 'none';
    }

    function renderGeneratedKeys(keys) {
        DOM.generatedPanel.style.display = 'block';

        const keyStrings = keys.map(k => typeof k === 'string' ? k : k.key);
        DOM.generatedList.innerHTML = keyStrings.map((key, i) => `
            <div class="generated-key-item" style="--i: ${i}">
                <span class="generated-key-text">${escapeHtml(key)}</span>
                <button class="copy-btn" onclick="App.copyKey('${escapeHtml(key)}', this)">📋 Copy</button>
            </div>
        `).join('');

        // Store for copy all
        DOM.generatedPanel._keys = keyStrings;
    }

    function copyAllKeys() {
        const keys = DOM.generatedPanel._keys || [];
        if (keys.length === 0) return;
        copyToClipboard(keys.join('\n'), DOM.copyAllBtn);
    }

    // ══════════════════════════════════════════════════════
    // USER MANAGEMENT
    // ══════════════════════════════════════════════════════
    async function loadUsers() {
        if (State.user?.role !== 'owner') return;

        DOM.usersLoading.style.display = 'flex';
        DOM.usersTbody.innerHTML = '';

        try {
            const users = await api.listUsers();
            State.users = Array.isArray(users) ? users : (users.users || []);
            DOM.usersLoading.style.display = 'none';
            renderUsersTable();
        } catch (err) {
            DOM.usersLoading.style.display = 'none';
            Toast.error('Failed to load users: ' + err.message);
        }
    }

    function renderUsersTable() {
        DOM.usersTbody.innerHTML = State.users.map((u, i) => `
            <tr class="table-row" style="animation-delay: ${i * 30}ms">
                <td><strong>${escapeHtml(u.username)}</strong></td>
                <td><span class="role-badge ${u.role}">${u.role}</span></td>
                <td>${escapeHtml(u.created_by || '—')}</td>
                <td title="${formatDate(u.created_at)}">${timeAgo(u.created_at)}</td>
                <td>
                    <div class="user-actions" onclick="event.stopPropagation()">
                        <button class="btn btn-secondary btn-sm" onclick="App.editUser(${u.id})" title="Edit user">✏️</button>
                        <button class="btn btn-danger btn-sm" onclick="App.deleteUser(${u.id}, '${escapeHtml(u.username)}')" title="Delete user">🗑️</button>
                    </div>
                </td>
            </tr>
        `).join('');
    }

    function showAddUserModal() {
        Modal.show(`
            <div class="modal-header">
                <h2 class="modal-title">Add User</h2>
                <button class="modal-close" data-modal-close>✕</button>
            </div>
            <div class="modal-body">
                <div class="form-group">
                    <label class="form-label" for="new-username">Username</label>
                    <input type="text" id="new-username" class="form-input" placeholder="Enter username" required>
                </div>
                <div class="form-group">
                    <label class="form-label" for="new-user-password">Password</label>
                    <input type="password" id="new-user-password" class="form-input" placeholder="Enter password" required minlength="6">
                </div>
                <div class="form-group">
                    <label class="form-label" for="new-user-role">Role</label>
                    <select id="new-user-role" class="form-select">
                        <option value="moderator">Moderator</option>
                        <option value="admin">Admin</option>
                        <option value="owner">Owner</option>
                    </select>
                </div>
            </div>
            <div class="modal-footer">
                <button class="btn btn-secondary" data-modal-close>Cancel</button>
                <button class="btn btn-primary" id="create-user-btn">➕ Create User</button>
            </div>
        `);

        document.getElementById('create-user-btn').addEventListener('click', async () => {
            const username = document.getElementById('new-username').value.trim();
            const password = document.getElementById('new-user-password').value;
            const role = document.getElementById('new-user-role').value;

            if (!username || !password) {
                Toast.warning('Please fill in all fields');
                return;
            }

            try {
                await api.createUser({ username, password, role });
                Toast.success(`User "${username}" created successfully`);
                Modal.hide();
                loadUsers();
            } catch (err) {
                Toast.error('Failed to create user: ' + err.message);
            }
        });
    }

    function editUser(userId) {
        const user = State.users.find(u => u.id === userId);
        if (!user) return;

        Modal.show(`
            <div class="modal-header">
                <h2 class="modal-title">Edit User: ${escapeHtml(user.username)}</h2>
                <button class="modal-close" data-modal-close>✕</button>
            </div>
            <div class="modal-body">
                <div class="form-group">
                    <label class="form-label" for="edit-user-role">Role</label>
                    <select id="edit-user-role" class="form-select">
                        <option value="moderator" ${user.role === 'moderator' ? 'selected' : ''}>Moderator</option>
                        <option value="admin" ${user.role === 'admin' ? 'selected' : ''}>Admin</option>
                        <option value="owner" ${user.role === 'owner' ? 'selected' : ''}>Owner</option>
                    </select>
                </div>
                <div class="form-group">
                    <label class="form-label" for="edit-user-pw">New Password <span style="color: var(--text-muted); font-weight: 400; text-transform: none;">(leave blank to keep current)</span></label>
                    <input type="password" id="edit-user-pw" class="form-input" placeholder="New password (optional)">
                </div>
            </div>
            <div class="modal-footer">
                <button class="btn btn-secondary" data-modal-close>Cancel</button>
                <button class="btn btn-primary" id="save-user-btn">💾 Save Changes</button>
            </div>
        `);

        document.getElementById('save-user-btn').addEventListener('click', async () => {
            const role = document.getElementById('edit-user-role').value;
            const password = document.getElementById('edit-user-pw').value;

            const body = { role };
            if (password) body.password = password;

            try {
                await api.updateUser(userId, body);
                Toast.success('User updated successfully');
                Modal.hide();
                loadUsers();
            } catch (err) {
                Toast.error('Failed to update user: ' + err.message);
            }
        });
    }

    function deleteUser(userId, username) {
        Confirm.show({
            icon: '🗑️',
            title: 'Delete User',
            message: `Are you sure you want to delete <strong>${escapeHtml(username)}</strong>? This cannot be undone.`,
            confirmText: 'Delete',
            confirmClass: 'btn-danger',
            async onConfirm() {
                try {
                    await api.deleteUser(userId);
                    Toast.success(`User "${username}" deleted`);
                    loadUsers();
                } catch (err) {
                    Toast.error('Failed to delete user: ' + err.message);
                }
            }
        });
    }

    // ══════════════════════════════════════════════════════
    // SETTINGS
    // ══════════════════════════════════════════════════════
    function renderSettings() {
        DOM.settingsUsername.textContent = State.user?.username || '—';
        const roleEl = DOM.settingsRole;
        roleEl.innerHTML = '';
        const badge = document.createElement('span');
        badge.className = `role-badge ${State.user?.role || ''}`;
        badge.textContent = State.user?.role || '—';
        roleEl.appendChild(badge);
    }

    async function handleChangePassword(e) {
        e.preventDefault();

        const current = document.getElementById('current-password').value;
        const newPw = document.getElementById('new-password').value;
        const confirmPw = document.getElementById('confirm-password').value;

        if (!current || !newPw) {
            Toast.warning('Please fill in all fields');
            return;
        }

        if (newPw !== confirmPw) {
            Toast.error('New passwords do not match');
            return;
        }

        if (newPw.length < 6) {
            Toast.warning('New password must be at least 6 characters');
            return;
        }

        const btn = DOM.passwordForm.querySelector('button[type="submit"]');
        btn.disabled = true;
        btn.querySelector('.btn-text').style.display = 'none';
        btn.querySelector('.btn-loader').style.display = 'inline-block';

        try {
            await api.changePassword(current, newPw);
            Toast.success('Password changed successfully');
            DOM.passwordForm.reset();
        } catch (err) {
            Toast.error('Failed to change password: ' + err.message);
        } finally {
            btn.disabled = false;
            btn.querySelector('.btn-text').style.display = '';
            btn.querySelector('.btn-loader').style.display = 'none';
        }
    }

    // ══════════════════════════════════════════════════════
    // EVENT BINDINGS
    // ══════════════════════════════════════════════════════
    function bindEvents() {
        // Login
        DOM.loginForm.addEventListener('submit', handleLogin);
        DOM.logoutBtn.addEventListener('click', handleLogout);

        // Mobile sidebar
        DOM.menuToggle.addEventListener('click', () => {
            DOM.sidebar.classList.toggle('open');
            DOM.sidebarOverlay.classList.toggle('visible');
        });
        DOM.sidebarOverlay.addEventListener('click', () => {
            DOM.sidebar.classList.remove('open');
            DOM.sidebarOverlay.classList.remove('visible');
        });

        // Keys search (debounced)
        DOM.keysSearch.addEventListener('input', debounce(() => {
            State.keysSearch = DOM.keysSearch.value.trim();
            State.keysPage = 1;
            loadKeys();
        }, 300));

        // Filter tabs
        DOM.filterTabs.addEventListener('click', (e) => {
            const tab = e.target.closest('.filter-tab');
            if (!tab) return;
            DOM.filterTabs.querySelectorAll('.filter-tab').forEach(t => t.classList.remove('active'));
            tab.classList.add('active');
            State.keysFilter = tab.dataset.status;
            State.keysPage = 1;
            loadKeys();
        });

        // Generate
        DOM.generateForm.addEventListener('submit', handleGenerate);
        DOM.copyAllBtn.addEventListener('click', copyAllKeys);

        // Users
        DOM.addUserBtn.addEventListener('click', showAddUserModal);

        // Settings
        DOM.passwordForm.addEventListener('submit', handleChangePassword);

        // Keyboard shortcut: Escape to close modals
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape') {
                Modal.hide();
                Confirm.hide();
            }
        });
    }

    // ══════════════════════════════════════════════════════
    // PUBLIC API (for inline handlers)
    // ══════════════════════════════════════════════════════
    window.App = {
        copyKey: (key, btn) => copyToClipboard(key, btn),
        revokeKey: (key) => revokeKey(key),
        deleteKey: (key) => deleteKey(key),
        editKey: (key) => editKey(key),
        editUser: (id) => editUser(id),
        deleteUser: (id, username) => deleteUser(id, username),
        goToPage: (page) => {
            State.keysPage = page;
            loadKeys();
        },
    };

    // ══════════════════════════════════════════════════════
    // INITIALIZATION
    // ══════════════════════════════════════════════════════
    function init() {
        Toast.init();
        Modal.init();
        Confirm.init();
        bindEvents();
        checkAuth();
    }

    // Boot
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();
