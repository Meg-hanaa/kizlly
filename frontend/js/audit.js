/* 
   KIZLLY — Audit Trail & Privacy Log View
    */

const AuditView = {
    async render(container) {
        if (!AuthManager.requireAuth()) {
            container.innerHTML = `
                <div class="empty-state">
                    <div style="font-size: 3rem;"></div>
                    <h3>Authentication Required</h3>
                    <p>Please sign in to access the audit trails.</p>
                </div>
            `;
            return;
        }

        container.innerHTML = `
            <div class="view-header flex-between">
                <div>
                    <h2>Security & Privacy Audit ledger</h2>
                    <p>Immutable record of all pipeline actions, reviewer decisions, and external API requests.</p>
                </div>
                <span class="badge badge-high" style="padding: 6px 12px; font-weight:600;"> Append-Only Ledger</span>
            </div>

            <!-- Tabs -->
            <div class="tab-container" style="display:flex; gap:10px; margin-bottom:20px;">
                <button class="btn btn-primary" id="btn-tab-audit"> Pipeline Audit Log</button>
                <button class="btn btn-outline" id="btn-tab-privacy"> AI Data Privacy Log</button>
            </div>
            
            <div id="audit-log-content">
                <div class="spinner-container"><div class="spinner"></div></div>
            </div>
        `;

        this.setupTabHandlers();
        await this.loadAuditLogs();
    },

    setupTabHandlers() {
        const btnAudit = document.getElementById('btn-tab-audit');
        const btnPrivacy = document.getElementById('btn-tab-privacy');

        if (btnAudit && btnPrivacy) {
            btnAudit.addEventListener('click', async () => {
                btnAudit.className = 'btn btn-primary';
                btnPrivacy.className = 'btn btn-outline';
                await this.loadAuditLogs();
            });

            btnPrivacy.addEventListener('click', async () => {
                btnAudit.className = 'btn btn-outline';
                btnPrivacy.className = 'btn btn-primary';
                await this.loadPrivacyLogs();
            });
        }
    },

    async loadAuditLogs() {
        const contentDiv = document.getElementById('audit-log-content');
        if (!contentDiv) return;

        contentDiv.innerHTML = '<div class="spinner-container"><div class="spinner"></div></div>';

        try {
            const data = await API.getAuditLog();
            const entries = data.entries || [];

            if (entries.length === 0) {
                contentDiv.innerHTML = `
                    <div class="empty-state" style="padding: 50px 0;">
                        <span style="font-size: 2.5rem;"></span>
                        <p style="margin-top:10px;">The audit ledger is currently empty. Run a contract review to populate logs.</p>
                    </div>
                `;
                return;
            }

            contentDiv.innerHTML = `
                <div class="card p-lg" style="overflow-x:auto;">
                    <table class="audit-table">
                        <thead>
                            <tr>
                                <th>Timestamp</th>
                                <th>Pipeline ID</th>
                                <th>Pipeline Step</th>
                                <th>Action Performed</th>
                                <th>Ledger Details</th>
                                <th>Operator / Reviewer</th>
                            </tr>
                        </thead>
                        <tbody>
                            ${entries.map(e => {
                                const dateStr = new Date(e.timestamp).toLocaleString();
                                return `
                                    <tr>
                                        <td style="font-family:var(--font-mono); font-size:0.85rem; width:170px;">${dateStr}</td>
                                        <td style="font-family:var(--font-mono); font-size:0.85rem; color:var(--accent-teal);">${e.workflow_id}</td>
                                        <td><span class="badge ${this.getStepBadgeClass(e.step)}">${e.step}</span></td>
                                        <td><strong>${e.action.replace(/_/g, ' ')}</strong></td>
                                        <td style="font-size:0.9rem; max-width:300px; word-break:break-word;">${e.details}</td>
                                        <td>${e.reviewer_name || 'System Worker'}</td>
                                    </tr>
                                `;
                            }).join('')}
                        </tbody>
                    </table>
                </div>
            `;
        } catch (err) {
            contentDiv.innerHTML = `<p style="color:var(--accent-rose);">${err.message}</p>`;
        }
    },

    async loadPrivacyLogs() {
        const contentDiv = document.getElementById('audit-log-content');
        if (!contentDiv) return;

        contentDiv.innerHTML = '<div class="spinner-container"><div class="spinner"></div></div>';

        try {
            const data = await API.getPrivacyLog();
            const entries = data.entries || [];

            if (entries.length === 0) {
                contentDiv.innerHTML = `
                    <div class="empty-state" style="padding: 50px 0;">
                        <span style="font-size: 2.5rem;"></span>
                        <p style="margin-top:10px;">No external AI requests have been logged yet.</p>
                    </div>
                `;
                return;
            }

            contentDiv.innerHTML = `
                <div class="card p-lg" style="margin-bottom:20px;">
                    <h3 style="margin-top:0; color:var(--accent-teal);">Local-First Data Minimization Guarantee</h3>
                    <p style="font-size:0.9rem; line-height:1.5;">
                        To protect your enterprise data privacy, Kizlly employs local text embeddings (using <code>all-MiniLM-L6-v2</code>) and local vector indexing (using <code>FAISS</code>). 
                        <strong>Your complete contracts never leave this environment.</strong> Only tiny clause segments of 2-3 sentences are sent to external LLMs (Groq LLaMA 3.3 70B) for analysis. 
                        Every byte sent externally is logged below for absolute compliance audit trail.
                    </p>
                </div>

                <div class="card p-lg" style="overflow-x:auto;">
                    <table class="audit-table">
                        <thead>
                            <tr>
                                <th>Timestamp</th>
                                <th>Pipeline ID</th>
                                <th>External API</th>
                                <th>Method / Purpose</th>
                                <th>Data Sent (Chars)</th>
                                <th>Redacted Content sent</th>
                            </tr>
                        </thead>
                        <tbody>
                            ${entries.map(e => {
                                const dateStr = new Date(e.timestamp).toLocaleString();
                                return `
                                    <tr>
                                        <td style="font-family:var(--font-mono); font-size:0.85rem; width:170px;">${dateStr}</td>
                                        <td style="font-family:var(--font-mono); font-size:0.85rem; color:var(--accent-teal);">${e.workflow_id}</td>
                                        <td><span class="badge badge-medium">Groq Cloud</span></td>
                                        <td><code>${e.action}</code></td>
                                        <td style="font-family:var(--font-mono); font-weight:600;">${e.details.length} chars</td>
                                        <td style="font-family:var(--font-mono); font-size:0.8rem; max-width:400px; overflow:hidden; text-overflow:ellipsis; white-space:nowrap;" title="${e.details.replace(/"/g, '&quot;')}">
                                            ${e.details}
                                        </td>
                                    </tr>
                                `;
                            }).join('')}
                        </tbody>
                    </table>
                </div>
            `;
        } catch (err) {
            contentDiv.innerHTML = `<p style="color:var(--accent-rose);">${err.message}</p>`;
        }
    },

    getStepBadgeClass(step) {
        switch(step) {
            case 'upload': return 'badge-low';
            case 'ingest': return 'badge-low';
            case 'embed_and_search': return 'badge-medium';
            case 'risk_analysis': return 'badge-high';
            case 'human_approval': return 'badge-critical';
            case 'graph_write': return 'badge-success';
            default: return '';
        }
    }
};
window.AuditView = AuditView;
