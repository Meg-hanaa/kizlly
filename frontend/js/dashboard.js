/* 
   KIZLLY — Portfolio Dashboard View
    */

const DashboardView = {
    async render(container) {
        if (!AuthManager.requireAuth()) {
            container.innerHTML = `
                <div class="empty-state">
                    <div style="font-size: 3rem;"></div>
                    <h3>Authentication Required</h3>
                    <p>Please sign in to access the portfolio dashboard.</p>
                </div>
            `;
            return;
        }

        container.innerHTML = `
            <div class="view-header flex-between">
                <div>
                    <h2>Portfolio Risk Intelligence</h2>
                    <p>Aggregated contract risk metrics powered by Cypher graph queries.</p>
                </div>
<<<<<<< HEAD
                <span class="badge badge-low" style="padding: 6px 12px; font-weight:600;"> Graph-Native Store (Neo4j)</span>
            </div>
            
=======
                <div style="display: flex; align-items: center; gap: 16px;">
                    <!-- Notification Bell -->
                    <div class="bell-container" id="dashboardBellContainer" style="position: relative;">
                        <button class="btn btn-outline" id="dashboardBellBtn" style="padding: 8px 12px; display: flex; align-items: center; gap: 6px; position: relative;">
                            🔔 <span id="dashboardBellCount" class="badge badge-critical" style="padding: 2px 6px; font-size: 0.75rem; border-radius: 50%; display: none;">0</span>
                        </button>
                        <div id="dashboardBellDropdown" class="card" style="display: none; position: absolute; right: 0; top: 45px; width: 320px; z-index: 100; border: 2px solid var(--border-color); box-shadow: var(--shadow-md); padding: 12px; background: var(--bg-secondary); text-align: left;">
                            <h4 style="margin: 0 0 10px 0; display: flex; justify-content: space-between; align-items: center;">
                                <span>Renewal Alerts</span>
                                <span class="badge badge-low" id="dashboardBellCountLabel" style="font-size:0.75rem;">0 unseen</span>
                            </h4>
                            <div id="dashboardBellList" style="max-height: 250px; overflow-y: auto; display: flex; flex-direction: column; gap: 8px;">
                                <!-- Alerts -->
                            </div>
                        </div>
                    </div>
                    <span class="badge badge-low" style="padding: 6px 12px; font-weight:600;"> Graph-Native Store (Neo4j)</span>
                </div>
            </div>
            
            <div id="alerts-panel"></div>
            
>>>>>>> 72c1ebc (Implement contract renewal alerts, fix graph visualization, layouts, and backend query routing)
            <div id="dashboard-content">
                <div class="spinner-container"><div class="spinner"></div></div>
            </div>
        `;

<<<<<<< HEAD
=======
        // Setup dropdown toggle
        const bellBtn = document.getElementById('dashboardBellBtn');
        const bellDropdown = document.getElementById('dashboardBellDropdown');
        if (bellBtn && bellDropdown) {
            bellBtn.addEventListener('click', (e) => {
                e.stopPropagation();
                const isShowing = bellDropdown.style.display === 'block';
                bellDropdown.style.display = isShowing ? 'none' : 'block';
            });
            document.addEventListener('click', () => {
                bellDropdown.style.display = 'none';
            });
            bellDropdown.addEventListener('click', (e) => {
                e.stopPropagation(); // Avoid closing when clicking inside
            });
        }

        // Trigger immediate Alerts fetch and rendering
        if (typeof AlertManager !== 'undefined') {
            AlertManager.loadAlerts();
        }

>>>>>>> 72c1ebc (Implement contract renewal alerts, fix graph visualization, layouts, and backend query routing)
        try {
            const stats = await API.getDashboard();
            const vendors = await API.getVendorExposure();
            const renewals = await API.getRenewalRisk(90);
            
            const dashboardContent = document.getElementById('dashboard-content');
            if (!dashboardContent) return;

            dashboardContent.innerHTML = `
                <!-- Metric Cards -->
                <div class="grid-4" style="margin-bottom: 24px;">
                    <div class="card p-lg flex-between">
                        <div>
                            <span style="font-size:0.85rem; color:var(--text-secondary); display:block; margin-bottom:5px;">Total Contracts</span>
                            <span style="font-size: 2.2rem; font-weight:700; color:var(--text-primary); font-family:var(--font-mono);">${stats.total_contracts}</span>
                        </div>
                        <div style="font-size: 2.5rem; opacity:0.8;">📂</div>
                    </div>
                    
                    <div class="card p-lg flex-between">
                        <div>
                            <span style="font-size:0.85rem; color:var(--text-secondary); display:block; margin-bottom:5px;">Active Vendors</span>
                            <span style="font-size: 2.2rem; font-weight:700; color:var(--text-primary); font-family:var(--font-mono);">${stats.active_vendors}</span>
                        </div>
                        <div style="font-size: 2.5rem; opacity:0.8;"></div>
                    </div>
                    
                    <div class="card p-lg flex-between">
                        <div>
                            <span style="font-size:0.85rem; color:var(--text-secondary); display:block; margin-bottom:5px;">Flagged Clauses</span>
                            <span style="font-size: 2.2rem; font-weight:700; color:var(--accent-amber); font-family:var(--font-mono);">${stats.flagged_clauses}</span>
                        </div>
                        <div style="font-size: 2.5rem; opacity:0.8; color:var(--accent-amber);"></div>
                    </div>
                    
                    <div class="card p-lg flex-between">
                        <div>
                            <span style="font-size:0.85rem; color:var(--text-secondary); display:block; margin-bottom:5px;">Approved / Rejected</span>
                            <span style="font-size: 1.8rem; font-weight:700; font-family:var(--font-mono);">
                                <span style="color:var(--accent-emerald);">${stats.approved_clauses}</span>
                                <span style="color:var(--text-muted);">/</span>
                                <span style="color:var(--accent-rose);">${stats.rejected_clauses}</span>
                            </span>
                        </div>
                        <div style="font-size: 2.5rem; opacity:0.8; color:var(--accent-emerald);"></div>
                    </div>
                </div>

                <div class="grid-2-1" style="margin-bottom: 24px;">
                    <!-- Vendor Exposure -->
                    <div class="card p-lg">
                        <h3 style="margin-top:0; margin-bottom: 20px;">Vendor Concentration Risk</h3>
                        <div id="vendor-exposure-chart">
                            ${this.renderVendorExposure(vendors.vendors || [])}
                        </div>
                    </div>

                    <!-- Risk Distribution -->
                    <div class="card p-lg">
                        <h3 style="margin-top:0; margin-bottom: 20px;">Risk Category Distribution</h3>
                        <div id="risk-distribution-list">
                            ${this.renderRiskDistribution(stats.risk_distribution || {})}
                        </div>
                    </div>
                </div>

                <div class="grid-1" style="margin-bottom: 24px;">
                    <!-- Renewal Timeline -->
                    <div class="card p-lg">
                        <h3 style="margin-top:0; margin-bottom: 20px;">Renewal Cascade Risks (Next 90 Days)</h3>
                        <div id="renewal-timeline-list">
                            ${this.renderRenewalTimeline(renewals.renewals || [])}
                        </div>
                    </div>
                </div>
            `;
        } catch (err) {
            const dashboardContent = document.getElementById('dashboard-content');
            if (dashboardContent) {
                dashboardContent.innerHTML = `<p style="color:var(--accent-rose);">${err.message}</p>`;
            }
        }
    },

    renderVendorExposure(vendors) {
        if (vendors.length === 0) {
            return `
                <div class="empty-state" style="padding: 40px 0;">
                    <span style="font-size: 2rem;">📊</span>
                    <p style="margin-top:10px;">No vendor exposure data. Run contracts through the pipeline.</p>
                </div>
            `;
        }

        // Get max exposure to scale the progress bars
        const maxExposure = Math.max(...vendors.map(v => v.totalExposure || 1));

        return vendors.map(v => {
            const percentage = (((v.totalExposure || 0) / maxExposure) * 100).toFixed(0);
            const formattedExposure = new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', maximumFractionDigits: 0 }).format(v.totalExposure || 0);
            
            return `
                <div style="margin-bottom: 15px;">
                    <div class="flex-between" style="font-size: 0.9rem; margin-bottom: 5px;">
                        <strong>${v.vendor || 'Unknown Vendor'}</strong>
                        <span style="font-family: var(--font-mono); font-weight:600;">
                            ${formattedExposure} <span style="font-size: 0.75rem; color:var(--text-secondary);">(${v.contractCount} ${v.contractCount === 1 ? 'contract' : 'contracts'})</span>
                        </span>
                    </div>
                    <div style="background:var(--bg-tertiary); height:8px; border-radius:4px; overflow:hidden;">
                        <div style="background:linear-gradient(90deg, var(--accent-teal), var(--accent-purple)); width:${percentage}%; height:100%; border-radius:4px;"></div>
                    </div>
                </div>
            `;
        }).join('');
    },

    renderRiskDistribution(riskDist) {
        const categories = Object.keys(riskDist);
        if (categories.length === 0) {
            return `
                <div class="empty-state" style="padding: 40px 0;">
                    <span style="font-size: 2rem;"></span>
                    <p style="margin-top:10px;">No risk classifications logged yet.</p>
                </div>
            `;
        }

        const totalFlags = Object.values(riskDist).reduce((a, b) => a + b, 0);

        return categories.map(cat => {
            const count = riskDist[cat];
            const percentage = ((count / totalFlags) * 100).toFixed(0);
            
            return `
                <div style="margin-bottom: 12px; display:flex; align-items:center; justify-content:space-between;">
                    <div style="display:flex; align-items:center; gap:8px;">
                        <span style="display:inline-block; width:10px; height:10px; border-radius:50%; background:var(--accent-amber);"></span>
                        <span style="font-size:0.9rem;">${cat}</span>
                    </div>
                    <div style="display:flex; align-items:center; gap:12px;">
                        <span class="badge badge-medium" style="font-family:var(--font-mono);">${count}</span>
                        <span style="font-size:0.8rem; color:var(--text-secondary); width:35px; text-align:right;">${percentage}%</span>
                    </div>
                </div>
            `;
        }).join('');
    },

    renderRenewalTimeline(renewals) {
        if (renewals.length === 0) {
            return `
                <div class="empty-state" style="padding: 40px 0;">
                    <span style="font-size: 2rem;"></span>
                    <p style="margin-top:10px;">No renewal dates scheduled in the next 90 days.</p>
                </div>
            `;
        }

        return `
            <table class="audit-table">
                <thead>
                    <tr>
                        <th>Urgency</th>
                        <th>Contract Title</th>
                        <th>Vendor</th>
                        <th>Renewal Date</th>
                        <th>Exposure Value</th>
                    </tr>
                </thead>
                <tbody>
                    ${renewals.map(r => {
                        let urgencyBadge = '';
                        if (r.urgency === 'URGENT') {
                            urgencyBadge = '<span class="badge badge-critical"> URGENT (30d)</span>';
                        } else if (r.urgency === 'SOON') {
                            urgencyBadge = '<span class="badge badge-high"> SOON (60d)</span>';
                        } else {
                            urgencyBadge = '<span class="badge badge-low"> UPCOMING (90d)</span>';
                        }

                        const formattedVal = new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', maximumFractionDigits: 0 }).format(r.value || 0);

                        return `
                            <tr>
                                <td>${urgencyBadge}</td>
                                <td><strong>${r.title}</strong></td>
                                <td>${r.vendor}</td>
                                <td style="font-family:var(--font-mono); font-size:0.9rem;">${r.renewal_date}</td>
                                <td style="font-family:var(--font-mono); font-weight:600;">${formattedVal}</td>
                            </tr>
                        `;
                    }).join('')}
                </tbody>
            </table>
        `;
    }
};
window.DashboardView = DashboardView;
