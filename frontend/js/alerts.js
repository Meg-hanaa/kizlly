const AlertManager = {
    alerts: [],
    pollInterval: null,

    init() {
        // Start polling alerts every 10 seconds if authenticated
        if (this.pollInterval) clearInterval(this.pollInterval);
        
        this.pollInterval = setInterval(() => {
            if (localStorage.getItem('kizlly_token')) {
                this.loadAlerts();
            }
        }, 10000);

        // Fetch immediately
        if (localStorage.getItem('kizlly_token')) {
            this.loadAlerts();
        }
    },

    async loadAlerts() {
        try {
            const data = await API.getAlerts();
            this.alerts = data.alerts || [];
            this.renderUI();
        } catch (err) {
            console.error('Failed to load alerts:', err);
        }
    },

    renderUI() {
        // 1. Update Dashboard Header Bell if present
        const bellCountEl = document.getElementById('dashboardBellCount');
        const bellCountLabelEl = document.getElementById('dashboardBellCountLabel');
        const bellListEl = document.getElementById('dashboardBellList');
        
        const unseenAlerts = this.alerts.filter(a => a.status === 'unseen');

        if (bellCountEl) {
            if (unseenAlerts.length > 0) {
                bellCountEl.textContent = unseenAlerts.length;
                bellCountEl.style.display = 'inline-block';
            } else {
                bellCountEl.style.display = 'none';
            }
        }

        if (bellCountLabelEl) {
            bellCountLabelEl.textContent = `${unseenAlerts.length} unseen`;
        }

        if (bellListEl) {
            if (unseenAlerts.length === 0) {
                bellListEl.innerHTML = `
                    <div style="text-align: center; padding: 20px 0; color: var(--text-muted); font-size: 0.85rem;">
                        🔔 No upcoming renewals alerts
                    </div>
                `;
            } else {
                bellListEl.innerHTML = unseenAlerts.map(alert => {
                    let badgeClass = 'badge-low';
                    if (alert.days_remaining !== null) {
                        if (alert.days_remaining < 30) badgeClass = 'badge-critical';
                        else if (alert.days_remaining <= 60) badgeClass = 'badge-high';
                    }
                    
                    return `
                        <div class="alert-dropdown-item card p-sm" data-id="${alert.id}" style="cursor: pointer; display: flex; flex-direction: column; gap: 4px; border-left: 4px solid var(--border-color); transition: transform 0.2s;">
                            <div class="flex-between">
                                <span class="badge ${badgeClass}" style="font-size: 0.7rem; padding: 2px 6px;">${alert.time_label}</span>
                                <span style="font-size: 0.75rem; color: var(--text-muted);">${alert.alert_type.replace('_', ' ')}</span>
                            </div>
                            <strong style="font-size: 0.85rem; color: var(--text-primary);">${alert.contract_title}</strong>
                            <div style="font-size: 0.75rem; color: var(--text-secondary);">Vendor: ${alert.vendor_name}</div>
                        </div>
                    `;
                }).join('');

                // Add event listeners
                bellListEl.querySelectorAll('.alert-dropdown-item').forEach(item => {
                    item.addEventListener('click', async (e) => {
                        const alertId = item.getAttribute('data-id');
                        await this.markAsSeen(alertId);
                    });
                });
            }
        }

        // 2. Update Inline Dashboard alerts panel if present
        const inlinePanelEl = document.getElementById('alerts-panel');
        if (inlinePanelEl) {
            if (unseenAlerts.length === 0) {
                inlinePanelEl.innerHTML = '';
            } else {
                inlinePanelEl.innerHTML = `
                    <div class="card p-lg" style="border: 2px solid var(--border-color); background: var(--bg-tertiary); box-shadow: var(--shadow-md); margin-bottom: 24px;">
                        <h3 style="margin-top:0; margin-bottom: 12px; color: var(--text-primary); display: flex; align-items: center; gap: 8px;">
                            🔔 Upcoming Renewal Deadlines
                        </h3>
                        <div class="grid-3" style="gap: 12px;">
                            ${unseenAlerts.map(alert => {
                                let badgeClass = 'badge-low';
                                if (alert.days_remaining !== null) {
                                    if (alert.days_remaining < 30) badgeClass = 'badge-critical';
                                    else if (alert.days_remaining <= 60) badgeClass = 'badge-high';
                                }

                                return `
                                    <div class="alert-card card p-md" data-id="${alert.id}" style="cursor: pointer; background: var(--bg-secondary); border: 2px solid var(--border-color); box-shadow: var(--shadow-sm); display: flex; flex-direction: column; gap: 6px; justify-content: space-between; transition: transform 0.2s;">
                                        <div>
                                            <div class="flex-between" style="margin-bottom: 4px;">
                                                <span class="badge ${badgeClass}">${alert.time_label}</span>
                                                <span style="font-size:0.75rem; color:var(--text-muted); font-family:var(--font-mono);">${alert.alert_type.replace('_', ' ')}</span>
                                            </div>
                                            <strong style="font-size: 0.9rem; color: var(--text-primary); display:block; margin-top:4px;">${alert.contract_title}</strong>
                                            <span style="font-size: 0.8rem; color: var(--text-secondary);">Vendor: ${alert.vendor_name}</span>
                                        </div>
                                        <button class="btn btn-outline btn-sm" style="margin-top: 10px; width: 100%; font-size: 0.75rem; padding: 4px 8px;">Dismiss</button>
                                    </div>
                                `;
                            }).join('')}
                        </div>
                    </div>
                `;

                // Add event listeners to cards
                inlinePanelEl.querySelectorAll('.alert-card').forEach(card => {
                    card.addEventListener('click', async (e) => {
                        const alertId = card.getAttribute('data-id');
                        await this.markAsSeen(alertId);
                    });
                });
            }
        }
    },

    async markAsSeen(alertId) {
        try {
            await API.markAlertSeen(alertId);
            App.showToast('Alert marked as seen', 'success');
            
            // Reload alerts
            await this.loadAlerts();
            
            // If on portfolio dashboard view, trigger render to reload stats
            const appContainer = document.getElementById('app');
            const hash = window.location.hash || '#/home';
            if (hash.startsWith('#/portfolio')) {
                DashboardView.render(appContainer);
            }
        } catch (err) {
            App.showToast('Failed to mark alert as seen: ' + err.message, 'error');
        }
    }
};

window.AlertManager = AlertManager;
