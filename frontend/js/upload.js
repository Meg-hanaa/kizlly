/* 
   KIZLLY — Upload & Review View
    */

const UploadView = {
    pollingIntervals: {},

    async render(container, contractId = null) {
        if (!AuthManager.requireAuth()) {
            container.innerHTML = `
                <div class="empty-state">
                    <div style="font-size: 3rem;"></div>
                    <h3>Authentication Required</h3>
                    <p>Please sign in to access the contract review platform.</p>
                </div>
            `;
            return;
        }

        if (contractId) {
            await this.renderReview(container, contractId);
        } else {
            await this.renderUploadList(container);
        }
    },

    async renderUploadList(container) {
        container.innerHTML = `
            <div class="view-header">
                <h2>Contract Review Pipeline</h2>
                <p>Ingest new contracts, monitor extraction progress, and review flagged risks.</p>
            </div>
            
            <div class="grid-2-1">
                <!-- Upload Panel -->
                <div class="card p-lg">
                    <h3 style="margin-top:0;">Upload Contract</h3>
                    <form id="upload-form">
                        <!-- Drag and Drop Upload Box -->
                        <div class="form-group">
                            <label for="file-input" style="font-weight: 600; display: block; margin-bottom: 8px;">Contract Document (PDF, DOCX, TXT) *</label>
                            <div id="drop-zone" class="upload-zone">
                                <span class="upload-zone-icon">📁</span>
                                <div class="upload-zone-title">Drag & Drop File Here</div>
                                <div class="upload-zone-subtitle" style="margin-bottom: 12px;">or drag your contract directly into this area (Max 10MB)</div>
                                <button type="button" class="btn btn-outline btn-sm" style="pointer-events: none; margin: 0 auto;">Browse Files</button>
                                <input type="file" id="file-input" accept=".pdf,.docx,.doc,.txt" required style="display: none;" />
                            </div>
                            <div id="file-name-preview" style="font-size: 0.85rem; color: var(--accent-teal); font-weight: 600; margin-top: 8px; display: none;"></div>
                        </div>
                        
                        <div class="form-group">
                            <label for="vendor-name">Counterparty / Vendor Name</label>
                            <input type="text" id="vendor-name" placeholder="Leave blank to read directly from document (e.g., Acme Corp)" />
                        </div>

                        <div class="form-group">
                            <label for="contract-title">Contract Title / Reference</label>
                            <input type="text" id="contract-title" placeholder="Leave blank to read directly from document (e.g., MSA 2026)" />
                        </div>
                        
                        <div class="form-group">
                            <label for="renewal-date">Target Renewal Date</label>
                            <div style="display: flex; gap: 8px; align-items: center;">
                                <input type="datetime-local" id="renewal-date" style="flex-grow: 1;" placeholder="Leave blank to read directly from document" />
                                <button type="button" id="set-demo-date-btn" class="btn btn-outline btn-sm" style="white-space: nowrap;">⚡ Set Test Date (3m)</button>
                            </div>
                            <span style="font-size:0.75rem; color:var(--text-secondary); margin-top:4px; display:block;">Leave blank to extract automatically from the document, select a date, or set to 3 minutes in the future for testing.</span>
                        </div>

                        <button type="submit" class="btn btn-primary" style="width:100%; margin-top: 10px;"> Start Ingestion Pipeline</button>
                    </form>
                </div>
                <!-- Active Pipelines List -->
                <div class="card p-lg">
                    <h3 style="margin-top:0;">Active Pipelines</h3>
                    <div id="pipelines-list" class="pipelines-list">
                        <div class="spinner-container"><div class="spinner"></div></div>
                    </div>
                </div>
            </div>
        `;

        this.setupUploadHandlers();
        await this.loadActivePipelines();
    },

    setupUploadHandlers() {
        const fileInput = document.getElementById('file-input');
        const uploadForm = document.getElementById('upload-form');
        const dropZone = document.getElementById('drop-zone');
        const filePreview = document.getElementById('file-name-preview');

        if (dropZone && fileInput) {
            // Click trigger
            dropZone.addEventListener('click', () => fileInput.click());

            // Drag effects
            dropZone.addEventListener('dragover', (e) => {
                e.preventDefault();
                dropZone.classList.add('drag-over');
            });

            ['dragleave', 'dragend'].forEach(type => {
                dropZone.addEventListener(type, () => {
                    dropZone.classList.remove('drag-over');
                });
            });

            // Handle drop
            dropZone.addEventListener('drop', (e) => {
                e.preventDefault();
                dropZone.classList.remove('drag-over');

                if (e.dataTransfer.files.length) {
                    fileInput.files = e.dataTransfer.files;
                    updateFilePreview(e.dataTransfer.files[0]);
                }
            });

            // Handle standard browse selection
            fileInput.addEventListener('change', () => {
                if (fileInput.files.length) {
                    updateFilePreview(fileInput.files[0]);
                }
            });

            const updateFilePreview = (file) => {
                if (filePreview) {
                    filePreview.textContent = `Selected: ${file.name} (${(file.size / 1024).toFixed(1)} KB)`;
                    filePreview.style.display = 'block';
                }
            };
        }

        // Demo date generator
        const setDemoBtn = document.getElementById('set-demo-date-btn');
        if (setDemoBtn) {
            setDemoBtn.addEventListener('click', (e) => {
                e.stopPropagation();
                const now = new Date();
                const future = new Date(now.getTime() + 3 * 60 * 1000); // 3 minutes in future
                
                const year = future.getFullYear();
                const month = String(future.getMonth() + 1).padStart(2, '0');
                const day = String(future.getDate()).padStart(2, '0');
                const hours = String(future.getHours()).padStart(2, '0');
                const minutes = String(future.getMinutes()).padStart(2, '0');
                
                const formatted = `${year}-${month}-${day}T${hours}:${minutes}`;
                document.getElementById('renewal-date').value = formatted;
                App.showToast('Test renewal date set to 3 minutes in the future!', 'success');
            });
        }

        if (uploadForm && fileInput) {
            uploadForm.addEventListener('submit', async (e) => {
                e.preventDefault();
                const file = fileInput.files[0];
                if (!file) {
                    App.showToast('Please select a file to upload.', 'error');
                    return;
                }

                const vendorName = document.getElementById('vendor-name').value.trim();
                const contractTitle = document.getElementById('contract-title').value.trim();
                const renewalDate = document.getElementById('renewal-date').value;

                try {
                    App.showToast('Uploading contract and starting workflow...', 'info');
                    const res = await API.uploadContract(file, vendorName, contractTitle, renewalDate);
                    App.showToast(res.message, 'success');
                    
                    // Reset upload state
                    uploadForm.reset();
                    if (filePreview) {
                        filePreview.style.display = 'none';
                        filePreview.textContent = '';
                    }
                    
                    await this.loadActivePipelines();
                } catch (err) {
                    App.showToast(err.message, 'error');
                }
            });
        }
    },


    async loadActivePipelines() {
        const listContainer = document.getElementById('pipelines-list');
        if (!listContainer) return;

        try {
            const data = await API.getContracts();
            const contracts = data.contracts || [];

            if (contracts.length === 0) {
                listContainer.innerHTML = `
                    <div class="empty-state" style="padding: 20px 0;">
                        <span style="font-size: 2rem;"></span>
                        <p style="margin: 10px 0 0 0;">No active contract pipelines. Upload a document to start.</p>
                    </div>
                `;
                return;
            }

            listContainer.innerHTML = contracts.map(c => {
                const dateStr = new Date(c.contract_meta?.upload_time || c.created_at).toLocaleString();
                const badgeClass = this.getStatusBadgeClass(c.status);
                const statusText = this.getStatusText(c.status);
                
                let reviewAction = '';
                if (c.status === 'paused_for_review') {
                    reviewAction = `<a href="#/review/${c.contract_id}" class="btn btn-outline btn-sm" style="margin-top: 8px; display: inline-block; padding: 4px 10px; font-size: 0.8rem;"> Review Risks</a>`;
                }

                // Setup polling for running pipelines
                if (c.status === 'running' || c.status === 'pending') {
                    this.startPolling(c.contract_id);
                }

                return `
                    <div class="pipeline-item card p-md" style="margin-bottom: 12px; border-left: 4px solid var(--border-color);">
                        <div class="flex-between" style="align-items: flex-start;">
                            <div>
                                <h4 style="margin:0 0 4px 0; font-weight:600;">${c.contract_meta?.title || c.filename || 'Untitled Contract'}</h4>
                                <div style="font-size: 0.8rem; color: var(--text-secondary); margin-bottom: 4px;">
                                    Vendor: <strong>${c.contract_meta?.vendor_name || 'Unknown'}</strong>
                                </div>
                                <div style="font-size: 0.75rem; color: var(--text-muted);">Uploaded: ${dateStr}</div>
                            </div>
                            <span class="badge ${badgeClass}">${statusText}</span>
                        </div>
                        ${reviewAction}
                    </div>
                `;
            }).join('');
        } catch (err) {
            listContainer.innerHTML = `<p style="color:var(--accent-rose);">${err.message}</p>`;
        }
    },

    startPolling(contractId) {
        if (this.pollingIntervals[contractId]) return;

        this.pollingIntervals[contractId] = setInterval(async () => {
            try {
                const statusData = await API.getContractStatus(contractId);
                
                // If it's no longer running/pending, reload the list and clear interval
                if (statusData.status !== 'running' && statusData.status !== 'pending') {
                    clearInterval(this.pollingIntervals[contractId]);
                    delete this.pollingIntervals[contractId];
                    
                    App.showToast(`Contract "${statusData.contract_meta?.title || 'Untitled'}" is ready for your review!`, 'info');
                    
                    const listContainer = document.getElementById('pipelines-list');
                    if (listContainer) {
                        this.loadActivePipelines();
                    }
                }
            } catch (e) {
                clearInterval(this.pollingIntervals[contractId]);
                delete this.pollingIntervals[contractId];
            }
        }, 3000);
    },

    getStatusBadgeClass(status) {
        switch(status) {
            case 'pending': return 'badge-low';
            case 'running': return 'badge-medium';
            case 'paused_for_review': return 'badge-high';
            case 'completed': return 'badge-success';
            case 'failed': return 'badge-critical';
            default: return '';
        }
    },

    getStatusText(status) {
        switch(status) {
            case 'pending': return 'Pending';
            case 'running': return 'Processing';
            case 'paused_for_review': return 'Needs Review';
            case 'completed': return 'Completed';
            case 'failed': return 'Failed';
            default: return status;
        }
    },

    //  Review Interface 
    async renderReview(container, contractId) {
        container.innerHTML = `
            <div class="view-header">
                <h2>Reviewing: <span id="review-title-display">Loading...</span></h2>
                <p>Verify AI risk detections, read Hinglish simplifications, and approve clauses to populate graph store.</p>
            </div>
            <div id="review-container">
                <div class="spinner-container"><div class="spinner"></div></div>
            </div>
        `;

        const reviewContainer = document.getElementById('review-container');
        try {
            const workflow = await API.getContractStatus(contractId);
            const clausesData = await API.getContractClauses(contractId);
            
            const titleDisplay = document.getElementById('review-title-display');
            if (titleDisplay) titleDisplay.textContent = workflow.contract_meta?.title || workflow.contract_meta?.filename || 'Contract';

            // Store loaded workflow for use in submitReview
            this._currentWorkflow = workflow;


            if (!reviewContainer) return;

            const stepsHtml = this.renderWorkflowSteps(workflow.steps || []);
            const privacyLogs = clausesData.privacy_logs || [];
            const totalChars = privacyLogs.reduce((acc, log) => acc + log.chars_sent, 0);
            const totalChunks = privacyLogs.reduce((acc, log) => acc + log.chunk_count, 0);

            let risksHtml = '';
            if (clausesData.risk_flags && clausesData.risk_flags.length > 0) {
                risksHtml = clausesData.risk_flags.map((flag, index) => {
                    const sevClass = this.getSeverityClass(flag.severity);
                    return `
                        <div class="card risk-card p-lg" data-clause-id="${flag.clause_id}" style="margin-bottom: 20px;">
                            <div class="flex-between" style="margin-bottom: 12px;">
                                <span class="badge ${sevClass}" style="text-transform: uppercase;">${flag.severity} Risk: ${flag.risk_type}</span>
                                <span style="font-size: 0.8rem; color: var(--text-muted);">Category: ${flag.category} | Confidence: ${(flag.ai_confidence * 100).toFixed(0)}%</span>
                            </div>
                            
                            <blockquote class="clause-quote">
                                "${flag.clause_text}"
                            </blockquote>
                            
                            <div class="ai-explanation" style="margin-top: 15px;">
                                <strong> AI Explainer:</strong>
                                <p style="margin: 5px 0 0 0; font-size: 0.95rem; color: var(--text-primary); line-height: 1.5;">${flag.explanation}</p>
                            </div>
                            
                            <div id="hinglish-explanation-${flag.clause_id}" class="hinglish-explanation" style="display:none; margin-top:15px; padding: 12px; background: rgba(139, 92, 246, 0.05); border-left: 3px solid var(--accent-purple); border-radius: 4px;">
                                <strong> Hinglish Explanation:</strong>
                                <p class="hinglish-text" style="margin: 5px 0 0 0; font-size: 0.95rem; line-height: 1.5; color: var(--text-primary);"></p>
                            </div>

                            <div style="margin-top: 15px; display: flex; gap: 10px; align-items: center;">
                                <button class="btn btn-outline btn-sm hinglish-toggle" onclick="UploadView.toggleHinglish('${flag.clause_id}', \`${encodeURIComponent(flag.clause_text)}\`)"> Explain in Hinglish</button>
                            </div>

                            <div style="margin-top: 20px; border-top: 1px solid var(--border-color); padding-top: 15px;">
                                <label style="display:block; margin-bottom:8px; font-size:0.85rem; font-weight:600; color:var(--text-secondary);">Decision Support Remarks</label>
                                <textarea class="reviewer-comment" placeholder="Add comments, counter-proposals or reasons for decision..." style="width:100%; height:60px; margin-bottom: 12px; font-size:0.9rem; padding: 8px;"></textarea>
                                
                                <div class="flex-between">
                                    <div style="display: flex; gap: 10px;">
                                        <button class="btn btn-success btn-sm approve-btn" onclick="UploadView.setDecision('${flag.clause_id}', 'approved')">Approve Clause</button>
                                        <button class="btn btn-danger btn-sm reject-btn" onclick="UploadView.setDecision('${flag.clause_id}', 'rejected')">Flag for Negotiation</button>
                                    </div>
                                    <span class="decision-status" id="decision-${flag.clause_id}" style="font-weight: 600; font-size:0.9rem; color: var(--text-muted);">Awaiting Decision</span>
                                </div>
                            </div>
                        </div>
                    `;
                }).join('');
            } else {
                risksHtml = `
                    <div class="card p-lg text-center" style="padding: 40px;">
                        <span style="font-size: 3rem;"></span>
                        <h4 style="margin: 15px 0 5px 0;">No Flagged Risks Found</h4>
                        <p style="margin: 0; color: var(--text-secondary);">This contract looks clean. No high-severity clauses were automatically flagged.</p>
                    </div>
                `;
            }

            reviewContainer.innerHTML = `
                <!-- Durable Pipeline State -->
                <div class="card p-lg" style="margin-bottom: 24px;">
                    <h3 style="margin-top:0;">Durable Workflow Pipeline</h3>
                    ${stepsHtml}
                    
                    <div style="margin-top: 20px; padding-top: 15px; border-top: 1px solid var(--border-color); display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:10px;">
                        <div>
                            <span class="badge badge-low"> Local-First Privacy Claim</span>
                            <span style="font-size:0.85rem; color:var(--text-secondary); margin-left:8px;">
                                Only <strong>${totalChunks}</strong> small chunks (<strong>${totalChars}</strong> characters total) ever left your machine.
                            </span>
                        </div>
                        <a href="#/audit" style="font-size:0.85rem; color:var(--accent-teal); text-decoration:none;">🔍 Inspect Privacy Transparency Log</a>
                    </div>
                </div>

                <!-- Flagged Clauses -->
                <div style="margin-bottom: 20px;" class="flex-between">
                    <h3>Flagged Risks & Contradictions</h3>
                    <div style="display:flex; gap:10px;">
                        <button class="btn btn-outline btn-sm" onclick="UploadView.bulkDecision('approved')">Approve All</button>
                        <button class="btn btn-outline btn-sm" onclick="UploadView.bulkDecision('rejected')">Flag All</button>
                    </div>
                </div>

                <div id="risk-flags-list">
                    ${risksHtml}
                </div>

                <!-- Action Bar -->
                <div class="card p-lg" style="margin-top: 30px; display: flex; justify-content: space-between; align-items: center; background: var(--bg-tertiary);">
                    <div>
                        <strong style="color:#000000; display:block; margin-bottom:4px;">Ready to Commit to Graph Ledger?</strong>
                        <span style="font-size:0.8rem; color:#000000;">Approving and committing writes the data model to Neo4j. Rejected clauses are marked as negotiation-critical.</span>
                    </div>
                    <button class="btn btn-primary" onclick="UploadView.submitReview('${contractId}')"> Commit Decisions & Resume Pipeline</button>
                </div>
            `;

            // Track decisions locally on the view object
            this.currentDecisions = {};
            clausesData.risk_flags?.forEach(f => {
                this.currentDecisions[f.clause_id] = {
                    clause_id: f.clause_id,
                    decision: 'flagged',
                    comment: ''
                };
            });

        } catch (err) {
            reviewContainer.innerHTML = `<p style="color:var(--accent-rose);">${err.message}</p>`;
        }
    },

    renderWorkflowSteps(steps) {
        const stepLabels = [
            "Document Ingest",
            "Embed & FAISS Index",
            "Risk & Contradictions",
            "Human Approval Checkpoint",
            "Neo4j Ledger Write",
            "Audit Trail Finalize"
        ];

        const stepKeys = ["ingest", "embed_and_search", "risk_analysis", "human_approval", "graph_write", "audit_finalize"];
        const stepsArray = Array.isArray(steps) ? steps : stepKeys.map(key => ({
            status: steps[key] || 'queued',
            retry_count: 0
        }));
        let html = '<div class="workflow-steps-progress" style="display:flex; justify-content:space-between; margin-top:20px; position:relative;">';
        
        // Background line
        html += '<div style="position:absolute; top:15px; left:0; right:0; height:2px; background:var(--bg-tertiary); z-index:1;"></div>';

        stepsArray.forEach((step, index) => {
            let statusClass = 'step-pending';
            let statusSymbol = index + 1;

            if (step.status === 'succeeded') {
                statusClass = 'step-succeeded';
                statusSymbol = '✓';
            } else if (step.status === 'running') {
                statusClass = 'step-running';
            } else if (step.status === 'failed') {
                statusClass = 'step-failed';
                statusSymbol = '✗';
            } else if (step.status === 'awaiting_approval') {
                statusClass = 'step-awaiting';
                statusSymbol = '⏸';
            }

            html += `
                <div style="display:flex; flex-direction:column; align-items:center; z-index:2; width:15%;">
                    <div class="step-circle ${statusClass}" style="width:32px; height:32px; border-radius:50%; display:flex; align-items:center; justify-content:center; font-weight:bold; font-size:0.85rem; margin-bottom:8px; border:2px solid var(--bg-primary);">
                        ${statusSymbol}
                    </div>
                    <span style="font-size:0.75rem; text-align:center; color:${step.status === 'running' || step.status === 'awaiting_approval' ? 'var(--accent-teal)' : 'var(--text-secondary)'}; font-weight:${step.status === 'running' ? 'bold' : 'normal'}">
                        ${stepLabels[index]}
                    </span>
                    ${step.retry_count > 0 ? `<span style="font-size:0.65rem; color:var(--accent-amber);">Retry: ${step.retry_count}</span>` : ''}
                </div>
            `;
        });

        html += '</div>';
        return html;
    },

    getSeverityClass(severity) {
        switch(severity) {
            case 'Critical': return 'badge-critical';
            case 'High': return 'badge-high';
            case 'Medium': return 'badge-medium';
            case 'Low': return 'badge-low';
            default: return '';
        }
    },

    setDecision(clauseId, decision) {
        const card = document.querySelector(`.risk-card[data-clause-id="${clauseId}"]`);
        const statusSpan = document.getElementById(`decision-${clauseId}`);
        const comment = card.querySelector('.reviewer-comment').value.trim();

        this.currentDecisions[clauseId] = {
            clause_id: clauseId,
            decision: decision,
            comment: comment
        };

        if (statusSpan) {
            if (decision === 'approved') {
                statusSpan.textContent = 'Approved';
                statusSpan.style.color = 'var(--accent-emerald)';
            } else {
                statusSpan.textContent = 'Flagged for Negotiation';
                statusSpan.style.color = 'var(--accent-rose)';
            }
        }
    },

    bulkDecision(decision) {
        Object.keys(this.currentDecisions).forEach(clauseId => {
            this.setDecision(clauseId, decision);
        });
    },

    async toggleHinglish(clauseId, encodedText) {
        const explDiv = document.getElementById(`hinglish-explanation-${clauseId}`);
        if (!explDiv) return;

        if (explDiv.style.display === 'block') {
            explDiv.style.display = 'none';
            return;
        }

        const textPara = explDiv.querySelector('.hinglish-text');
        textPara.textContent = 'Translating and simplifying to Hinglish...';
        explDiv.style.display = 'block';

        try {
            const rawText = decodeURIComponent(encodedText);
            const formData = new FormData();
            formData.append('clause_text', rawText);
            
            const res = await API.request('POST', '/api/explain/hinglish', formData, true);
            textPara.textContent = res.explanation;
        } catch (err) {
            textPara.textContent = `Hinglish explainer error: ${err.message}`;
        }
    },

    async submitReview(contractId) {
        const decisionsArray = Object.values(this.currentDecisions);
        
        try {
            App.showToast('Submitting decisions and resuming workflow...', 'info');

            // Read metadata from the already-loaded workflow object (not missing DOM fields)
            const meta = this._currentWorkflow?.contract_meta || {};
            
            const payload = {
                decisions: decisionsArray,
                vendor_name: meta.vendor_name || null,
                contract_title: meta.title || null,
                renewal_date: meta.renewal_date || null
            };

            const res = await API.submitReview(contractId, payload);
            App.showToast(res.message, 'success');
            
            // Go back to upload pipelines view
            window.location.hash = '#/upload';
        } catch (err) {
            App.showToast(err.message, 'error');
        }
    }
};
window.UploadView = UploadView;
