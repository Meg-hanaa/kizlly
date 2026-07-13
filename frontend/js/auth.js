/* 
   KIZLLY — Authentication Manager
    */

const AuthManager = {
    currentUser: null,
    token: null,
    isAuthenticated: false,

    init() {
        this.token = localStorage.getItem('kizlly_token');
        const userStr = localStorage.getItem('kizlly_user');
        
        if (this.token && userStr) {
            try {
                this.currentUser = JSON.parse(userStr);
                this.isAuthenticated = true;
            } catch (e) {
                this.logout();
            }
        } else {
            // Check if guest token already exists
            const guestToken = localStorage.getItem('kizlly_guest_token');
            if (guestToken) {
                this.token = guestToken;
                this.currentUser = {
                    username: localStorage.getItem('kizlly_guest_username') || 'guest',
                    display_name: 'Guest Reviewer'
                };
                this.isAuthenticated = true;
            } else {
                // Generate a temporary persistent guest token for guest mode
                const randomId = Math.random().toString(36).substring(2, 9);
                const guestUser = 'guest_' + randomId;
                const tempToken = 'guest_token_' + randomId;
                localStorage.setItem('kizlly_guest_token', tempToken);
                localStorage.setItem('kizlly_guest_username', guestUser);
                this.token = tempToken;
                this.currentUser = {
                    username: guestUser,
                    display_name: 'Guest Reviewer'
                };
                this.isAuthenticated = true;
            }
        }
        this.updateNavbar();
    },

    showLoginModal() {
        const modal = document.getElementById('authModal');
        if (modal) {
            modal.classList.add('active');
            modal.setAttribute('aria-hidden', 'false');
        }
    },

    hideLoginModal() {
        const modal = document.getElementById('authModal');
        if (modal) {
            modal.classList.remove('active');
            modal.setAttribute('aria-hidden', 'true');
            // Reset forms
            document.getElementById('loginForm')?.reset();
            document.getElementById('registerForm')?.reset();
            const loginError = document.getElementById('loginError');
            const registerError = document.getElementById('registerError');
            if (loginError) loginError.textContent = '';
            if (registerError) registerError.textContent = '';
        }
    },

    toggleAuthForm(event) {
        if (event) event.preventDefault();
        const loginForm = document.getElementById('loginForm');
        const registerForm = document.getElementById('registerForm');
        const modalTitle = document.getElementById('authModalTitle');
        const toggleText = document.getElementById('authToggleText');

        if (!loginForm || !registerForm || !modalTitle || !toggleText) return;

        if (loginForm.style.display === 'none') {
            loginForm.style.display = 'block';
            registerForm.style.display = 'none';
            modalTitle.textContent = 'Sign in to Kizlly';
            toggleText.innerHTML = `Don't have an account? <a href="#" onclick="AuthManager.toggleAuthForm(event)" id="authToggleLink">Create one</a>`;
        } else {
            loginForm.style.display = 'none';
            registerForm.style.display = 'block';
            modalTitle.textContent = 'Create Reviewer Account';
            toggleText.innerHTML = `Already have an account? <a href="#" onclick="AuthManager.toggleAuthForm(event)" id="authToggleLink">Sign In</a>`;
        }
    },

    async handleLoginSubmit(event) {
        event.preventDefault();
        const usernameInput = document.getElementById('loginUsername');
        const passwordInput = document.getElementById('loginPassword');
        const errorDiv = document.getElementById('loginError');

        if (!usernameInput || !passwordInput || !errorDiv) return false;

        const username = usernameInput.value.trim();
        const password = passwordInput.value;

        try {
            const response = await API.login(username, password);
            this.saveSession(response);
            this.hideLoginModal();
            App.showToast(`Logged in as ${response.display_name}`, 'success');
            App.navigate(window.location.hash || '#/upload');
        } catch (err) {
            errorDiv.textContent = err.message;
        }
        return false;
    },

    async handleRegisterSubmit(event) {
        event.preventDefault();
        const displayNameInput = document.getElementById('regDisplayName');
        const usernameInput = document.getElementById('regUsername');
        const passwordInput = document.getElementById('regPassword');
        const errorDiv = document.getElementById('registerError');

        if (!displayNameInput || !usernameInput || !passwordInput || !errorDiv) return false;

        const displayName = displayNameInput.value.trim();
        const username = usernameInput.value.trim();
        const password = passwordInput.value;

        try {
            const response = await API.register(username, password, displayName);
            this.saveSession(response);
            this.hideLoginModal();
            App.showToast(`Account created for ${response.display_name}`, 'success');
            App.navigate(window.location.hash || '#/upload');
        } catch (err) {
            errorDiv.textContent = err.message;
        }
        return false;
    },

    saveSession(response) {
        this.token = response.access_token;
        this.currentUser = {
            username: response.username,
            display_name: response.display_name
        };
        this.isAuthenticated = true;
        localStorage.setItem('kizlly_token', this.token);
        localStorage.setItem('kizlly_user', JSON.stringify(this.currentUser));
        this.updateNavbar();
        // Restart alert polling now that user is authenticated
        if (typeof AlertManager !== 'undefined') {
            AlertManager.init();
        }
    },

    updateNavbar() {
        const navbarUser = document.getElementById('navbarUser');
        if (!navbarUser) return;

        const isGuest = this.currentUser && this.currentUser.username.startsWith('guest_');

        if (this.isAuthenticated && this.currentUser && !isGuest) {
            navbarUser.innerHTML = `
                <div class="user-profile" style="display:flex; align-items:center; gap:12px;">
                    <span id="username-display" style="font-size:0.9rem; font-weight:500;">${this.currentUser.display_name}</span>
                    <button class="btn btn-outline btn-sm" id="logoutBtn" onclick="AuthManager.logout()">Sign Out</button>
                </div>
            `;
        } else if (isGuest) {
            navbarUser.innerHTML = `
                <div class="user-profile" style="display:flex; align-items:center; gap:12px;">
                    <span id="username-display" style="font-size:0.9rem; font-weight:500; opacity:0.8; font-style:italic;">Guest Mode</span>
                    <button class="btn btn-outline btn-sm" id="loginBtn" onclick="AuthManager.showLoginModal()">Sign In</button>
                </div>
            `;
        } else {
            navbarUser.innerHTML = `
                <button class="btn btn-outline btn-sm" id="loginBtn" onclick="AuthManager.showLoginModal()">
                    Sign In
                </button>
            `;
        }
    },

    logout() {
        this.currentUser = null;
        this.token = null;
        this.isAuthenticated = false;
        localStorage.removeItem('kizlly_token');
        localStorage.removeItem('kizlly_user');
        localStorage.removeItem('kizlly_guest_token');
        localStorage.removeItem('kizlly_guest_username');
        this.updateNavbar();
        // Stop alert polling so we don't flood 401 errors
        if (typeof AlertManager !== 'undefined' && AlertManager.pollInterval) {
            clearInterval(AlertManager.pollInterval);
            AlertManager.pollInterval = null;
        }
        App.showToast('Logged out successfully.', 'info');
        // Restart in guest mode by re-running init
        this.init();
        window.location.hash = '#/home';
    },

    requireAuth() {
        return true;
    }
};
window.AuthManager = AuthManager;
