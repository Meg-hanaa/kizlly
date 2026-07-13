/* 
   KIZLLY — API Client
   Backend communication layer with JWT auth
    */

const API = {
    BASE_URL: '', // Same-origin — configure if backend runs on a different port

    //  Core request wrapper 
    async request(method, path, body = null, isFormData = false) {
        const url = `${this.BASE_URL}${path}`;
        const headers = {};
        const token = localStorage.getItem('kizlly_token') || localStorage.getItem('kizlly_guest_token');
        // Authentication endpoints should not send bearer tokens
        const isAuthRoute = path.includes('/api/auth/');
        if (token && !isAuthRoute) {
            headers['Authorization'] = `Bearer ${token}`;
        }

        if (!isFormData && body) {
            headers['Content-Type'] = 'application/json';
        }

        const options = { method, headers };

        if (body) {
            options.body = isFormData ? body : JSON.stringify(body);
        }

        try {
            const response = await fetch(url, options);

            // Handle 401 — token expired or invalid
            if (response.status === 401) {
                let errorMsg = 'Session expired. Please sign in again.';
                try {
                    const errData = await response.json();
                    if (errData.detail) {
                        errorMsg = errData.detail;
                    }
                } catch (_) {}

                // Only clear session and redirect if this is NOT an auth attempt
                if (!path.includes('/api/auth/')) {
                    localStorage.removeItem('kizlly_token');
                    localStorage.removeItem('kizlly_user');
                    if (typeof AuthManager !== 'undefined') {
                        AuthManager.isAuthenticated = false;
                        AuthManager.updateNavbar();
                        
                        // Guest-Session validation: Only show login modal if we had a token that expired,
                        // do not show it automatically for guest-mode background polling
                        const isGuestToken = token && token.startsWith('guest_token_');
                        if (!isGuestToken) {
                            AuthManager.showLoginModal();
                        }
                    }
                }
                throw new Error(errorMsg);
            }

            // Handle non-OK responses
            if (!response.ok) {
                let errorMsg = `Request failed (${response.status})`;
                try {
                    const errData = await response.json();
                    errorMsg = errData.detail || errData.message || errData.error || errorMsg;
                } catch (_) { /* ignore parse errors */ }
                throw new Error(errorMsg);
            }

            // Handle 204 No Content
            if (response.status === 204) {
                return null;
            }

            return await response.json();
        } catch (err) {
            // Network errors
            if (err.name === 'TypeError' && err.message.includes('fetch')) {
                throw new Error('Network error — unable to reach the server. Please check your connection.');
            }
            throw err;
        }
    },

    // AUTH ENDPOINTS

    async login(username, password) {
        return this.request('POST', '/api/auth/login', { username, password });
    },

    async register(username, password, displayName) {
        return this.request('POST', '/api/auth/register', {
            username,
            password,
            display_name: displayName,
        });
    },

    // CONTRACT ENDPOINTS

    async uploadContract(file, vendorName, contractTitle, renewalDate) {
        const formData = new FormData();
        formData.append('file', file);
        formData.append('vendor_name', vendorName);
        formData.append('contract_title', contractTitle);
        if (renewalDate) {
            formData.append('renewal_date', renewalDate);
        }
        return this.request('POST', '/api/contracts/upload', formData, true);
    },

    async getContractStatus(contractId) {
        return this.request('GET', `/api/contracts/${contractId}/status`);
    },

    async getContractClauses(contractId) {
        return this.request('GET', `/api/contracts/${contractId}/clauses`);
    },

    async submitReview(contractId, payload) {
        const body = Array.isArray(payload) ? { decisions: payload } : payload;
        return this.request('POST', `/api/contracts/${contractId}/review`, body);
    },

    async getContracts() {
        return this.request('GET', '/api/contracts');
    },

    // PORTFOLIO / DASHBOARD ENDPOINTS (Graph-powered)

    async getDashboard() {
        return this.request('GET', '/api/portfolio/dashboard');
    },

    async getGraphData() {
        return this.request('GET', '/api/portfolio/graph');
    },

    async getVendorExposure() {
        return this.request('GET', '/api/portfolio/vendor-exposure');
    },

    async getRenewalRisk(days = 90) {
        return this.request('GET', `/api/portfolio/renewal-risk?days=${days}`);
    },

    async getClausePatterns() {
        return this.request('GET', '/api/portfolio/clause-patterns');
    },

    // AUDIT ENDPOINTS

    async getAuditLog(workflowId = null) {
        const path = workflowId
            ? `/api/audit/log?workflow_id=${encodeURIComponent(workflowId)}`
            : '/api/audit/log';
        return this.request('GET', path);
    },

    async getPrivacyLog() {
        return this.request('GET', '/api/privacy/transparency');
    },

    // ALERTS ENDPOINTS

    async getAlerts() {
        return this.request('GET', '/api/contracts/alerts');
    },

    async markAlertSeen(alertId) {
        return this.request('POST', `/api/contracts/alerts/${alertId}/seen`);
    },

    // HINGLISH EXPLANATION

    async getHinglishExplanation(clauseText) {
        return this.request('POST', '/api/explain/hinglish', { clause_text: clauseText });
    },
};
