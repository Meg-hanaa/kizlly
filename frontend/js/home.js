/* =================================================================
   KIZLLY - Landing Page View (Gen Z Bento Grid & Editorial Typography)
   ================================================================= */

const HomeView = {
    currentLang: 'en',

    translations: {
        en: {
            heroTitle: "Transform Contracts into Active Risk Portfolios",
            heroSub: "Kizlly maps contract clauses into a secure semantic graph, tracking concentration risk, liabilities, and renewal timelines across your entire vendor ecosystem.",
            getStarted: "Enter Workspace",
            learnMore: "Explore Features",
            uploadDoc: "Upload Document",
            private: "Private Local Embeddings",
            privateSub: "Confidential document analysis",
            enterprise: "Durable Workflows",
            enterpriseSub: "Built on retry-resilient state machines",
            multiLang: "Multi-Language Support",
            multiLangSub: "English and Hindi explanations",
            
            // Features Section Title
            featuresPill: "Core Capabilities",
            featuresSub: "Everything you need to understand documents",
            featuresLead: "Built for teams and professionals who require absolute accuracy.",

            // Problem
            problemTitle: "The Challenge of Contract Review",
            problemSub: "How traditional methods compare to modern automated analysis.",
            chatgpt: "Public AI Services",
            chatgptDesc: "Fast and convenient, but exposes confidential contract details and proprietary terms to public servers.",
            manual: "Manual Review",
            manualDesc: "Confidential, but requires hours of legal review and remains prone to missed liability clauses.",
            lawyer: "Outside Counsel",
            lawyerDesc: "Highly accurate, but expensive hourly billing and slow turnaround times.",
            lexiSolution: "Kizlly Solution",
            lexiSolutionDesc: "Immediate results, absolute privacy via local ingestion, and durable state tracking.",
        },
        hi: {
            heroTitle: "अनुबंधों को सक्रिय जोखिम पोर्टफोलियो में बदलें",
            heroSub: "Kizlly अनुबंध खंडों को एक सुरक्षित शब्दार्थ ग्राफ में मैप करता है, जो आपके पूरे विक्रेता पारिस्थितिकी तंत्र में देयता और नवीनीकरण समयसीमा को ट्रैक करता है।",
            getStarted: "कार्यक्षेत्र में प्रवेश करें",
            learnMore: "सुविधाएँ देखें",
            uploadDoc: "दस्तावेज़ अपलोड करें",
            private: "निजी स्थानीय एम्बेडिंग",
            privateSub: "गोपनीय दस्तावेज़ विश्लेषण",
            enterprise: "टिकाऊ वर्कफ़्लो",
            enterpriseSub: "पुनः प्रयास करने योग्य स्टेट मशीन",
            multiLang: "बहु-भाषा समर्थन",
            multiLangSub: "अंग्रेजी और हिंदी अनुवाद",
            
            // Features Section Title
            featuresPill: "मुख्य विशेषताएं",
            featuresSub: "दस्तावेजों को समझने के लिए आवश्यक सब कुछ",
            featuresLead: "उन पेशेवरों के लिए निर्मित जिन्हें पूर्ण सटीकता की आवश्यकता है।",

            // Problem
            problemTitle: "अनुबंध समीक्षा की चुनौती",
            problemSub: "पारंपरिक तरीके आधुनिक स्वचालित विश्लेषण की तुलना में कैसे प्रदर्शन करते हैं।",
            chatgpt: "सार्वजनिक AI सेवाएं",
            chatgptDesc: "तेज़ और सुविधाजनक, लेकिन आपके गोपनीय अनुबंध विवरण को सार्वजनिक सर्वर पर लीक करता है।",
            manual: "मैनुअल समीक्षा",
            manualDesc: "गोपनीय, लेकिन समीक्षा में घंटों लगते हैं और जोखिमों को अनदेखा करने की संभावना बनी रहती है।",
            lawyer: "बाहरी वकील",
            lawyerDesc: "सटीक, लेकिन महंगी फीस और परिणाम मिलने में दो से तीन दिन का समय लगता है।",
            lexiSolution: "Kizlly समाधान",
            lexiSolutionDesc: "तत्काल परिणाम, स्थानीय इनजेशन के माध्यम से पूर्ण गोपनीयता, और टिकाऊ स्थिति ट्रैकिंग।",
        }
    },

    render(container) {
        const t = this.translations[this.currentLang];

        container.innerHTML = `
            <!-- Hero Landing Section (Cozy Slate Haze) -->
            <section class="relative overflow-hidden bg-[radial-gradient(circle_at_center,rgba(243,239,233,0.85)_0%,var(--bg-primary)_100%)] border-b border-neutral-200/60" style="padding: 50px 0 60px 0;">
                <div style="max-width: 1200px; margin: 0 auto; padding: 0 20px; text-align: center;">

                    <!-- Centered Header & Subhead (Aesthetic Typo) -->
                    <h1 style="font-size: 3.6rem; font-weight: 800; line-height: 1.05; letter-spacing: -2px; margin: 0 auto 24px auto; font-family: 'Inter', sans-serif; max-width: 800px; color: var(--text-primary);">
                        ${this.currentLang === 'en' ? `
                            Transform Contracts into Active <span style="background: linear-gradient(90deg, var(--accent-teal), #c48d82); -webkit-background-clip:text; -webkit-text-fill-color:transparent;">Risk Portfolios</span>
                        ` : `
                            अनुबंधों को सक्रिय <span style="background: linear-gradient(90deg, var(--accent-teal), #c48d82); -webkit-background-clip:text; -webkit-text-fill-color:transparent;">जोखिम पोर्टफोलियो</span> में बदलें
                        `}
                    </h1>

                    <p style="color:var(--text-secondary); font-size: 1.1rem; line-height:1.6; max-width: 600px; margin: 0 auto 40px auto; font-family:'Inter',sans-serif;">
                        ${t.heroSub}
                    </p>

                    <div style="display:flex; justify-content:center; gap:15px; margin-bottom: 60px;">
                        <a href="#/upload" class="btn btn-primary" style="background:var(--accent-teal); padding:12px 36px; font-weight:600; border-radius:8px; display:inline-flex; align-items:center; color: #fff;">
                            ${t.getStarted}
                        </a>
                        <a href="#features-anchor" class="btn btn-outline" style="padding:12px 36px; font-weight:600; border-radius:8px; border-color:var(--border-color); color:var(--text-primary); background: var(--bg-secondary);">
                            ${t.learnMore}
                        </a>
                    </div>

                    <!-- retro Operating System Interactive Showcase Frame (Light grid theme) -->
                    <div style="max-width: 850px; margin: 0 auto; background: var(--bg-secondary); border: 2px solid var(--border-color); border-radius: 12px; box-shadow: var(--shadow-lg); overflow: hidden; text-align: left;">
                        <!-- Header bar with window controls -->
                        <div style="background: var(--accent-teal); padding: 10px 16px; border-bottom: 2px solid var(--border-color); display: flex; align-items: center; justify-content: space-between;">
                            <div style="display: flex; align-items: center; gap: 8px;">
                                <div style="width: 10px; height: 10px; border-radius: 50%; background: var(--bg-secondary); border: 1.5px solid var(--border-color);"></div>
                                <span style="margin-left: 6px; font-size: 0.75rem; color: #ffffff; font-family: var(--font-mono); font-weight: 700;">C:\\KIZLLY\\workspace</span>
                            </div>
                            <div style="width: 18px; height: 18px; background: var(--accent-rose); border: 2px solid var(--border-color); border-radius: 3px; display: flex; align-items: center; justify-content: center; color: #ffffff; font-size: 0.75rem; font-weight: 900; line-height: 1; cursor: pointer; user-select: none;">×</div>
                        </div>
                        
                        <!-- Showcase Body (Visual SaaS layout mockup) -->
                        <div class="grid-2" style="padding: 24px; gap: 20px; background: var(--bg-primary);">
                            <!-- Left: Interactive Portfolio Graph Visualizer mock -->
                            <div style="background: var(--bg-secondary); border-radius: 8px; border: 1px solid var(--border-color); padding: 20px; min-height: 250px; display: flex; flex-direction: column; justify-content: center; align-items: center; position: relative;">
                                <span style="font-size: 0.7rem; font-weight: 700; color: var(--text-secondary); position: absolute; top: 15px; left: 15px; letter-spacing: 1px;">PORTFOLIO RISK LEDGER</span>
                                <svg width="240" height="160" viewBox="0 0 240 160" style="display:block;">
                                    <line x1="120" y1="80" x2="70" y2="50" stroke="rgba(18,18,18,0.12)" stroke-width="1.5" />
                                    <line x1="120" y1="80" x2="170" y2="50" stroke="rgba(18,18,18,0.12)" stroke-width="1.5" />
                                    <line x1="120" y1="80" x2="120" y2="130" stroke="rgba(195,151,151,0.2)" stroke-width="1.5" />
                                    <line x1="70" y1="50" x2="40" y2="90" stroke="rgba(50,43,39,0.06)" stroke-width="1" />
                                    <line x1="170" y1="50" x2="200" y2="90" stroke="rgba(50,43,39,0.06)" stroke-width="1" />
                                    
                                    <circle cx="120" cy="80" r="14" fill="var(--accent-teal)" stroke="#ffffff" stroke-width="2" />
                                    <circle cx="70" cy="50" r="10" fill="var(--accent-rose)" stroke="#ffffff" stroke-width="2" />
                                    <circle cx="170" cy="50" r="11" fill="var(--accent-purple)" stroke="#ffffff" stroke-width="2" />
                                    <circle cx="120" cy="130" r="8" fill="var(--accent-amber)" stroke="#ffffff" stroke-width="2" />
                                    <circle cx="40" cy="90" r="6" fill="#a68a80" />
                                    <circle cx="200" cy="90" r="6" fill="#a68a80" />
                                </svg>
                            </div>
                            
                            <!-- Right: Running Pipeline status mock -->
                            <div style="display: flex; flex-direction: column; gap: 15px;">
                                <div style="background: var(--bg-secondary); border-radius: 8px; border: 1px solid var(--border-color); padding: 15px;">
                                    <span style="font-size: 0.7rem; color: var(--text-secondary); display: block; margin-bottom: 6px; letter-spacing: 0.5px; font-weight:700;">ACTIVE PIPELINE</span>
                                    <div style="display: flex; align-items: center; gap: 10px;">
                                        <div class="spinner" style="width: 14px; height: 14px; border-width: 2px; border-color: var(--accent-teal) transparent transparent transparent;"></div>
                                        <span style="font-size: 0.85rem; font-weight: 600; color: var(--text-primary);">Running: Risk &amp; Contradiction Audit</span>
                                    </div>
                                    <div style="background: var(--bg-primary); height: 4px; border-radius: 2px; margin-top: 12px; overflow: hidden;">
                                        <div style="background: var(--accent-teal); width: 65%; height: 100%;"></div>
                                    </div>
                                </div>
                                <div class="grid-2" style="gap: 12px;">
                                    <div style="background: var(--bg-secondary); border-radius: 8px; border: 1px solid var(--border-color); padding: 15px;">
                                        <span style="font-size: 0.7rem; color: var(--text-secondary); display: block; font-weight:700; margin-bottom:4px;">VENDORS MAP</span>
                                        <strong style="font-size: 1.25rem; color: var(--text-primary); font-family: var(--font-mono);">18</strong>
                                    </div>
                                    <div style="background: var(--bg-secondary); border-radius: 8px; border: 1px solid var(--border-color); padding: 15px;">
                                        <span style="font-size: 0.7rem; color: var(--text-secondary); display: block; font-weight:700; margin-bottom:4px;">DEYATA RISKS</span>
                                        <strong style="font-size: 1.25rem; color: var(--accent-amber); font-family: var(--font-mono);">4</strong>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>

                    <!-- 3 Core Trust Pillars below showcase -->
                    <div class="grid-3" style="max-width: 1000px; margin: 50px auto 0 auto; gap: 20px;">
                        <div class="card p-lg text-center" style="background: var(--bg-secondary); border-color:var(--border-color); box-shadow: 0 4px 12px rgba(0,0,0,0.01);">
                            <div style="width:36px; height:36px; border-radius:50%; background:rgba(18,18,18,0.04); display:flex; align-items:center; justify-content:center; color:var(--accent-teal); margin: 0 auto 12px auto;">
                                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="11" width="18" height="11" rx="2" ry="2"/><path d="M7 11V7a5 5 0 0 1 10 0v4"/></svg>
                            </div>
                            <h4 style="margin:0 0 4px 0; font-size:0.85rem; font-weight:700; color:var(--text-primary);">${t.private}</h4>
                            <p style="margin:0; font-size:0.75rem; color:var(--text-secondary);">${t.privateSub}</p>
                        </div>
                        <div class="card p-lg text-center" style="background: var(--bg-secondary); border-color:var(--border-color); box-shadow: 0 4px 12px rgba(0,0,0,0.01);">
                            <div style="width:36px; height:36px; border-radius:50%; background:rgba(18,18,18,0.04); display:flex; align-items:center; justify-content:center; color:var(--accent-teal); margin: 0 auto 12px auto;">
                                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 2v20M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6"/></svg>
                            </div>
                            <h4 style="margin:0 0 4px 0; font-size:0.85rem; font-weight:700; color:var(--text-primary);">${t.enterprise}</h4>
                            <p style="margin:0; font-size:0.75rem; color:var(--text-secondary);">${t.enterpriseSub}</p>
                        </div>
                        <div class="card p-lg text-center" style="background: var(--bg-secondary); border-color:var(--border-color); box-shadow: 0 4px 12px rgba(0,0,0,0.01);">
                            <div style="width:36px; height:36px; border-radius:50%; background:rgba(18,18,18,0.04); display:flex; align-items:center; justify-content:center; color:var(--accent-teal); margin: 0 auto 12px auto;">
                                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 12a9 9 0 0 1-9 9m9-9a9 9 0 0 0-9-9m9 9H3m9 9a9 9 0 0 1-9-9m9 9c1.657 0 3-4.03 3-9s-1.343-9-3-9m0 18c-1.657 0-3-4.03-3-9s1.343-9 3-9"/></svg>
                            </div>
                            <h4 style="margin:0 0 4px 0; font-size:0.85rem; font-weight:700; color:var(--text-primary);">${t.multiLang}</h4>
                            <p style="margin:0; font-size:0.75rem; color:var(--text-secondary);">${t.multiLangSub}</p>
                        </div>
                    </div>

                </div>
            </section>

            <!-- Bento Grid Section (High-end Studio Layout) -->
            <section id="features-anchor" style="padding: 100px 0; background: var(--bg-secondary); border-bottom: 1px solid var(--border-color);">
                <div style="max-width: 1200px; margin: 0 auto; padding: 0 20px;">
                    
                    <div style="text-align:center; max-width:600px; margin:0 auto 60px auto;">
                        <span style="color:var(--accent-teal); font-weight:700; font-size:0.75rem; letter-spacing:3px; text-transform:uppercase; display:block; margin-bottom:12px;">
                            ${t.featuresPill}
                        </span>
                        <h2 style="font-size:2.4rem; font-weight:800; letter-spacing:-1.5px; color:var(--text-primary); margin:0 0 16px 0;">
                            ${t.featuresSub}
                        </h2>
                        <p style="color:var(--text-secondary); font-size:0.95rem; margin:0;">
                            ${t.featuresLead}
                        </p>
                    </div>

                    <!-- Bento Grid Container -->
                    <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 24px;">
                        
                        <!-- Block 1: Hinglish Explainer (Large - spans 2 columns) -->
                        <div class="card" style="grid-column: span 2; background: var(--bg-primary); padding: 0; overflow: hidden; display: flex; flex-direction: column; justify-content: space-between; min-height: 340px;">
                            <!-- OS Header -->
                            <div style="background: var(--accent-teal); padding: 8px 16px; border-bottom: 2px solid var(--border-color); display: flex; align-items: center; justify-content: space-between;">
                                <div style="display: flex; align-items: center; gap: 6px;">
                                    <div style="width: 8px; height: 8px; border-radius: 50%; background: var(--bg-secondary); border: 1.5px solid var(--border-color);"></div>
                                    <span style="font-size: 0.7rem; color: #ffffff; font-family: var(--font-mono); font-weight: 700;">C:\\KIZLLY\\hinglish_explainer.exe</span>
                                </div>
                                <div style="width: 14px; height: 14px; background: var(--accent-rose); border: 1.5px solid var(--border-color); border-radius: 2px; display: flex; align-items: center; justify-content: center; color: #ffffff; font-size: 0.6rem; font-weight: 900; line-height: 1; cursor: pointer; user-select: none;">×</div>
                            </div>
                            
                            <!-- Card Body -->
                            <div style="padding: 24px; display: flex; flex-direction: column; justify-content: space-between; flex: 1;">
                                <div>
                                    <h3 style="font-size: 1.3rem; font-weight: 800; color: var(--text-primary); margin: 0 0 10px 0;">Understand what you sign, instantly</h3>
                                    <p style="color: var(--text-secondary); font-size: 0.85rem; line-height: 1.5; max-width: 500px; margin: 0 0 20px 0;">
                                        Translates complex, dense legal jargon into the everyday, conversational Hindi-English mix spoken in corporate India.
                                    </p>
                                </div>
                                <!-- visual mock -->
                                <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 15px; background: var(--bg-secondary); border: 2px solid var(--border-color); border-radius: 8px; padding: 15px; box-shadow: var(--shadow-sm);">
                                    <div style="border-right: 2px solid var(--border-color); padding-right: 15px;">
                                        <span style="font-size: 0.65rem; font-weight: 700; color: var(--text-muted); display: block; margin-bottom: 6px;">LEGAL CONTRACT ENGLISH</span>
                                        <p style="font-size: 0.75rem; color: var(--text-primary); line-height: 1.4; margin: 0; font-style: italic;">
                                            "Vendor liability is restricted to direct claims, cap not exceeding fifty thousand rupees."
                                        </p>
                                    </div>
                                    <div style="padding-left: 5px;">
                                        <span style="font-size: 0.65rem; font-weight: 700; color: var(--accent-teal); display: block; margin-bottom: 6px;">KIZLLY HINGLISH EXPLAINER</span>
                                        <p style="font-size: 0.75rem; color: var(--text-primary); line-height: 1.4; margin: 0; font-weight: 600;">
                                            Agar koi direct nuksan hota hai, toh provider maximum ₹50,000 bharega.
                                        </p>
                                    </div>
                                </div>
                            </div>
                        </div>

                        <!-- Block 2: Decision Brief (Medium - spans 1 column) -->
                        <div class="card" style="grid-column: span 1; background: var(--bg-primary); padding: 0; overflow: hidden; display: flex; flex-direction: column; justify-content: space-between; min-height: 340px;">
                            <!-- OS Header -->
                            <div style="background: var(--accent-teal); padding: 8px 16px; border-bottom: 2px solid var(--border-color); display: flex; align-items: center; justify-content: space-between;">
                                <div style="display: flex; align-items: center; gap: 6px;">
                                    <div style="width: 8px; height: 8px; border-radius: 50%; background: var(--bg-secondary); border: 1.5px solid var(--border-color);"></div>
                                    <span style="font-size: 0.7rem; color: #ffffff; font-family: var(--font-mono); font-weight: 700;">C:\\KIZLLY\\decision_brief.exe</span>
                                </div>
                                <div style="width: 14px; height: 14px; background: var(--accent-rose); border: 1.5px solid var(--border-color); border-radius: 2px; display: flex; align-items: center; justify-content: center; color: #ffffff; font-size: 0.6rem; font-weight: 900; line-height: 1; cursor: pointer; user-select: none;">×</div>
                            </div>
                            
                            <!-- Card Body -->
                            <div style="padding: 24px; display: flex; flex-direction: column; justify-content: space-between; flex: 1;">
                                <div>
                                    <h3 style="font-size: 1.3rem; font-weight: 800; color: var(--text-primary); margin: 0 0 10px 0;">Decision Brief</h3>
                                    <p style="color: var(--text-secondary); font-size: 0.85rem; line-height: 1.5; margin: 0 0 20px 0;">
                                        Instant summaries detailing key terms and liability flags before executing reviews.
                                    </p>
                                </div>
                                <!-- visual checklist -->
                                <div style="background: var(--bg-secondary); border: 2px solid var(--border-color); border-radius: 8px; padding: 15px; display: flex; flex-direction: column; gap: 8px; box-shadow: var(--shadow-sm);">
                                    <div style="display: flex; align-items: center; gap: 8px; font-size: 0.75rem; color: var(--text-primary); font-weight: 600;">
                                        <span style="color: var(--accent-teal); font-weight: 900;">[✓]</span> Liability Limit Audited
                                    </div>
                                    <div style="display: flex; align-items: center; gap: 8px; font-size: 0.75rem; color: var(--text-primary); font-weight: 600;">
                                        <span style="color: var(--accent-teal); font-weight: 900;">[✓]</span> Renewal Cliff Extracted
                                    </div>
                                    <div style="display: flex; align-items: center; gap: 8px; font-size: 0.75rem; color: var(--text-primary); font-weight: 600;">
                                        <span style="color: var(--accent-teal); font-weight: 900;">[✓]</span> Conflict Checks Cleared
                                    </div>
                                </div>
                            </div>
                        </div>

                        <!-- Block 3: Contradiction Check (Medium - spans 1 column) -->
                        <div class="card" style="grid-column: span 1; background: var(--bg-primary); padding: 0; overflow: hidden; display: flex; flex-direction: column; justify-content: space-between; min-height: 340px;">
                            <!-- OS Header -->
                            <div style="background: var(--accent-amber); padding: 8px 16px; border-bottom: 2px solid var(--border-color); display: flex; align-items: center; justify-content: space-between;">
                                <div style="display: flex; align-items: center; gap: 6px;">
                                    <div style="width: 8px; height: 8px; border-radius: 50%; background: var(--bg-secondary); border: 1.5px solid var(--border-color);"></div>
                                    <span style="font-size: 0.7rem; color: #ffffff; font-family: var(--font-mono); font-weight: 700;">C:\\KIZLLY\\conflict_alert.sys</span>
                                </div>
                                <div style="width: 14px; height: 14px; background: var(--accent-rose); border: 1.5px solid var(--border-color); border-radius: 2px; display: flex; align-items: center; justify-content: center; color: #ffffff; font-size: 0.6rem; font-weight: 900; line-height: 1; cursor: pointer; user-select: none;">×</div>
                            </div>
                            
                            <!-- Card Body -->
                            <div style="padding: 24px; display: flex; flex-direction: column; justify-content: space-between; flex: 1;">
                                <div>
                                    <h3 style="font-size: 1.3rem; font-weight: 800; color: var(--text-primary); margin: 0 0 10px 0;">Contradiction Check</h3>
                                    <p style="color: var(--text-secondary); font-size: 0.85rem; line-height: 1.5; margin: 0 0 20px 0;">
                                        Compares active invoices against master terms to identify pricing conflicts.
                                    </p>
                                </div>
                                <!-- contradiction comparison visual -->
                                <div style="background: var(--bg-secondary); border: 2px solid var(--border-color); border-radius: 8px; padding: 12px; display: flex; flex-direction: column; gap: 8px; font-size: 0.7rem; box-shadow: var(--shadow-sm);">
                                    <div style="background: var(--bg-primary); padding: 6px; border-radius: 4px; border-left: 3px solid var(--accent-teal); border: 1px solid var(--border-color);">
                                        <strong>Agreement A:</strong> Net 30 payment term.
                                    </div>
                                    <div style="background: var(--accent-rose-dim); padding: 6px; border-radius: 4px; border-left: 3px solid var(--accent-rose); border: 1px solid var(--border-color);">
                                        <strong>Agreement B:</strong> Invoices due net 15.
                                    </div>
                                </div>
                            </div>
                        </div>

                        <!-- Block 4: Portfolio Ledger Graph (Large - spans 2 columns) -->
                        <div class="card" style="grid-column: span 2; background: var(--bg-primary); padding: 0; overflow: hidden; display: flex; flex-direction: column; justify-content: space-between; min-height: 340px;">
                            <!-- OS Header -->
                            <div style="background: var(--accent-teal); padding: 8px 16px; border-bottom: 2px solid var(--border-color); display: flex; align-items: center; justify-content: space-between;">
                                <div style="display: flex; align-items: center; gap: 6px;">
                                    <div style="width: 8px; height: 8px; border-radius: 50%; background: var(--bg-secondary); border: 1.5px solid var(--border-color);"></div>
                                    <span style="font-size: 0.7rem; color: #ffffff; font-family: var(--font-mono); font-weight: 700;">C:\\KIZLLY\\graph_exposure.exe</span>
                                </div>
                                <div style="width: 14px; height: 14px; background: var(--accent-rose); border: 1.5px solid var(--border-color); border-radius: 2px; display: flex; align-items: center; justify-content: center; color: #ffffff; font-size: 0.6rem; font-weight: 900; line-height: 1; cursor: pointer; user-select: none;">×</div>
                            </div>
                            
                            <!-- Card Body -->
                            <div style="padding: 24px; display: flex; flex-direction: column; justify-content: space-between; flex: 1;">
                                <div>
                                    <h3 style="font-size: 1.3rem; font-weight: 800; color: var(--text-primary); margin: 0 0 10px 0;">Active Exposure Mapping</h3>
                                    <p style="color: var(--text-secondary); font-size: 0.85rem; line-height: 1.5; max-width: 500px; margin: 0 0 20px 0;">
                                        Connects agreements, clauses, and counter-parties in a single graph database to map renewal cliffs and vendor exposure.
                                    </p>
                                </div>
                                <!-- visual network row -->
                                <div style="background: var(--bg-secondary); border: 2px solid var(--border-color); border-radius: 8px; padding: 15px; display: flex; justify-content: space-around; align-items: center; font-size: 0.75rem; font-weight: 700; color: var(--text-primary); box-shadow: var(--shadow-sm);">
                                    <span style="padding: 6px 12px; border: 2px solid var(--border-color); border-radius: 4px; background: var(--bg-primary);">Contract 01</span>
                                    <span style="color: var(--text-muted); font-size:0.65rem;">── (:WITH_VENDOR) ──</span>
                                    <span style="padding: 6px 12px; border: 2px solid var(--border-color); border-radius: 4px; background: var(--bg-primary);">Vendor A</span>
                                    <span style="color: var(--text-muted); font-size:0.65rem;">── (:EXPOSED_TO) ──</span>
                                    <span style="padding: 6px 12px; border: 2px solid var(--border-color); border-radius: 4px; background: var(--accent-rose-dim); color: var(--accent-rose); border-color: var(--accent-rose);">Liability Cliff</span>
                                </div>
                            </div>
                        </div>

                    </div>
                </div>
            </section>

            <!-- Comparisons Section -->
            <section style="padding: 80px 0; background: var(--bg-primary); border-bottom: 1px solid var(--border-color);">
                <div style="max-width: 1200px; margin: 0 auto; padding: 0 20px;">
                    <div style="text-align:center; max-width:600px; margin:0 auto 50px auto;">
                        <h2 style="font-size:2.2rem; font-weight:800; letter-spacing:-1.5px; color:var(--text-primary); margin:0 0 16px 0;">
                            ${t.problemTitle}
                        </h2>
                        <p style="color:var(--text-secondary); font-size:0.95rem; margin:0;">
                            ${t.problemSub}
                        </p>
                    </div>

                    <div class="grid-3" style="gap:25px;">
                        <div class="card p-lg" style="background: var(--bg-secondary); border-color:var(--border-color); box-shadow: 0 4px 12px rgba(0,0,0,0.01);">
                            <h3 style="font-size:1.1rem; color:var(--text-primary); margin:0 0 12px 0;">${t.manual}</h3>
                            <p style="color:var(--text-secondary); font-size:0.85rem; line-height:1.6; margin:0;">${t.manualDesc}</p>
                        </div>

                        <div class="card p-lg" style="background: var(--bg-secondary); border-color:var(--border-color); box-shadow: 0 4px 12px rgba(0,0,0,0.01);">
                            <h3 style="font-size:1.1rem; color:var(--accent-rose); margin:0 0 12px 0;">${t.chatgpt}</h3>
                            <p style="color:var(--text-secondary); font-size:0.85rem; line-height:1.6; margin:0;">${t.chatgptDesc}</p>
                        </div>

                        <div class="card p-lg" style="background: var(--bg-secondary); border: 1.5px solid var(--accent-teal); box-shadow: 0 10px 30px rgba(166,138,128,0.04);">
                            <h3 style="font-size:1.1rem; color:var(--accent-teal); margin:0 0 12px 0;">${t.lexiSolution}</h3>
                            <p style="color:var(--text-primary); font-weight:500; font-size:0.85rem; line-height:1.6; margin:0;">${t.lexiSolutionDesc}</p>
                        </div>
                    </div>
                </div>
            </section>
        `;

        this.setupLangSwitch(container);
    },

    setupLangSwitch(container) {
        const btn = document.getElementById('lang-switch-global-btn');
        if (btn) {
            btn.textContent = this.currentLang === 'en' ? 'Hindi' : 'English';
            btn.onclick = () => {
                this.currentLang = this.currentLang === 'en' ? 'hi' : 'en';
                this.render(container);
            };
        }
    }
};
window.HomeView = HomeView;
