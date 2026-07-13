/* 
   KIZLLY — Graph Visualization View (D3.js)
    */

const GraphView = {
    simulation: null,
    svg: null,

    async render(container) {
        if (!AuthManager.requireAuth()) {
            container.innerHTML = `
                <div class="empty-state">
                    <div style="font-size: 3rem;"></div>
                    <h3>Authentication Required</h3>
                    <p>Please sign in to access the contract intelligence graph.</p>
                </div>
            `;
            return;
        }

        container.innerHTML = `
            <div class="view-header flex-between">
                <div>
                    <h2>Contract Portfolio Graph</h2>
                    <p>Explore contract metadata, counterparties, clause classifications, and risk mappings in a semantic graph.</p>
                </div>
                
                <div class="legend" style="display:flex; gap:15px; font-size:0.85rem;">
                    <div style="display:flex; align-items:center; gap:5px;">
                        <span style="display:inline-block; width:12px; height:12px; border-radius:50%; background:#3b82f6;"></span> Contract
                    </div>
                    <div style="display:flex; align-items:center; gap:5px;">
                        <span style="display:inline-block; width:12px; height:12px; border-radius:50%; background:#ef4444;"></span> Vendor
                    </div>
                    <div style="display:flex; align-items:center; gap:5px;">
                        <span style="display:inline-block; width:12px; height:12px; border-radius:50%; background:#fbbf24;"></span> Clause
                    </div>
                    <div style="display:flex; align-items:center; gap:5px;">
                        <span style="display:inline-block; width:12px; height:12px; border-radius:50%; background:#a78bfa;"></span> Risk Type
                    </div>
                </div>
            </div>

            <div class="grid-3-1" style="height: calc(100vh - 200px); min-height: 500px; gap: 20px;">
                <!-- Graph SVG viewport -->
                <div class="card" style="padding:0; overflow:hidden; position:relative; height:100%;">
                    <svg id="d3-graph-viewport" style="width:100%; height:100%; display:block; background:#0b0f19;"></svg>
                    
                    <!-- Zoom Overlay Controls -->
                    <div style="position:absolute; bottom:20px; right:20px; display:flex; flex-direction:column; gap:5px; z-index:10;">
                        <button class="btn btn-outline btn-sm" id="zoom-in-btn" style="padding: 5px 10px; font-weight:bold; font-size:1.1rem; background:rgba(30,41,59,0.8);">+</button>
                        <button class="btn btn-outline btn-sm" id="zoom-out-btn" style="padding: 5px 10px; font-weight:bold; font-size:1.1rem; background:rgba(30,41,59,0.8);">-</button>
                        <button class="btn btn-outline btn-sm" id="zoom-fit-btn" style="padding: 5px 10px; font-size:0.8rem; background:rgba(30,41,59,0.8);">Fit</button>
                    </div>
                </div>

                <!-- Info sidebar -->
                <div class="card p-lg" style="height:100%; overflow-y:auto;">
                    <h3 style="margin-top:0;">Semantic Inspector</h3>
                    <div id="graph-inspector-content">
                        <p style="color:var(--text-secondary);">Click any node in the graph to inspect its metadata, attributes, and relationships.</p>
                    </div>
                </div>
            </div>
        `;

        await this.loadAndInitGraph();
    },

    async loadAndInitGraph() {
        const svgElement = document.getElementById('d3-graph-viewport');
        if (!svgElement) return;

        try {
            const data = await API.getGraphData();
            
            if (!data.nodes || data.nodes.length === 0) {
                const reviewContainer = svgElement.parentElement;
                reviewContainer.innerHTML = `
                    <div class="empty-state" style="padding: 100px 0;">
                        <span style="font-size: 4rem;"></span>
                        <h3>No Graph Data Yet</h3>
                        <p>Upload a contract and complete the review process to populate the graph store.</p>
                        <a href="#/upload" class="btn btn-primary" style="margin-top: 15px;">Upload Contract</a>
                    </div>
                `;
                return;
            }

            this.initD3Graph(svgElement, data);
        } catch (err) {
            App.showToast(`Graph load error: ${err.message}`, 'error');
        }
    },

    initD3Graph(svgElement, data) {
        const width = svgElement.clientWidth || 800;
        const height = svgElement.clientHeight || 500;

        const d3Svg = d3.select(svgElement);
        d3Svg.selectAll("*").remove(); // Clear previous drawing

        // Arrow marker definition for directed links
        d3Svg.append("defs").append("marker")
            .attr("id", "arrowhead")
            .attr("viewBox", "0 -5 10 10")
            .attr("refX", 20) // Position arrowhead relative to target node boundary
            .attr("refY", 0)
            .attr("markerWidth", 6)
            .attr("markerHeight", 6)
            .attr("orient", "auto")
            .append("path")
            .attr("d", "M0,-5L10,0L0,5")
            .attr("fill", "var(--text-muted)");

        // Group container that holds all zoomable contents
        const g = d3Svg.append("g");

        // D3 zoom configuration
        const zoom = d3.zoom()
            .scaleExtent([0.1, 4])
            .on("zoom", (event) => {
                g.attr("transform", event.transform);
            });

        d3Svg.call(zoom);

        // Bind zoom overlay buttons
        document.getElementById('zoom-in-btn')?.addEventListener('click', () => d3Svg.transition().call(zoom.scaleBy, 1.3));
        document.getElementById('zoom-out-btn')?.addEventListener('click', () => d3Svg.transition().call(zoom.scaleBy, 1 / 1.3));
        document.getElementById('zoom-fit-btn')?.addEventListener('click', () => {
            d3Svg.transition().call(zoom.transform, d3.zoomIdentity);
        });

        const nodes = data.nodes.map(n => ({
            id: n.id,
            label: n.label,
            type: n.type,
            properties: n.properties || {}
        }));

        // Filter out links where source or target is not in nodes list to avoid D3 "node not found" crashes
        const nodeIds = new Set(nodes.map(n => n.id));
        const links = data.edges
            .filter(e => nodeIds.has(e.source) && nodeIds.has(e.target))
            .map(e => ({
                source: e.source,
                target: e.target,
                type: e.type
            }));

        // Simulation parameters
        this.simulation = d3.forceSimulation(nodes)
            .force("link", d3.forceLink(links).id(d => d.id).distance(120))
            .force("charge", d3.forceManyBody().strength(-300))
            .force("center", d3.forceCenter(width / 2, height / 2))
            .force("collision", d3.forceCollide().radius(25));

        // Draw Links
        const link = g.append("g")
            .attr("class", "links")
            .selectAll("line")
            .data(links)
            .enter().append("line")
            .attr("stroke", "rgba(148, 163, 184, 0.25)")
            .attr("stroke-width", 1.5)
            .attr("marker-end", "url(#arrowhead)");

        // Link labels
        const linkLabel = g.append("g")
            .attr("class", "link-labels")
            .selectAll("text")
            .data(links)
            .enter().append("text")
            .attr("fill", "var(--text-muted)")
            .attr("font-size", "7.5px")
            .attr("text-anchor", "middle")
            .text(d => d.type);

        // Draw Nodes
        const node = g.append("g")
            .attr("class", "nodes")
            .selectAll("g")
            .data(nodes)
            .enter().append("g")
            .call(d3.drag()
                .on("start", (event, d) => {
                    if (!event.active) this.simulation.alphaTarget(0.3).restart();
                    d.fx = d.x;
                    d.fy = d.y;
                })
                .on("drag", (event, d) => {
                    d.fx = event.x;
                    d.fy = event.y;
                })
                .on("end", (event, d) => {
                    if (!event.active) this.simulation.alphaTarget(0);
                    d.fx = null;
                    d.fy = null;
                }));

        // Draw node circles with size & colors based on node types
        node.append("circle")
            .attr("r", d => this.getNodeRadius(d.type))
            .attr("fill", d => this.getNodeColor(d.type))
            .attr("stroke", "#0f172a")
            .attr("stroke-width", 1.5)
            .style("cursor", "pointer")
            .on("click", (event, d) => {
                event.stopPropagation();
                this.inspectNode(d);
                
                // Highlight node
                node.selectAll("circle").attr("stroke", "#0f172a").attr("stroke-width", 1.5);
                d3.select(event.currentTarget).attr("stroke", "var(--accent-teal)").attr("stroke-width", 3);
            });

        // Draw labels inside nodes
        node.append("text")
            .attr("dy", d => this.getNodeRadius(d.type) + 12)
            .attr("text-anchor", "middle")
            .attr("fill", "var(--text-primary)")
            .attr("font-size", "9.5px")
            .text(d => this.getNodeCaption(d))
            .style("pointer-events", "none");

        // Simulation tick updater
        this.simulation.on("tick", () => {
            link
                .attr("x1", d => d.source.x)
                .attr("y1", d => d.source.y)
                .attr("x2", d => d.target.x)
                .attr("y2", d => d.target.y);

            linkLabel
                .attr("x", d => (d.source.x + d.target.x) / 2)
                .attr("y", d => (d.source.y + d.target.y) / 2 - 4);

            node.attr("transform", d => `translate(${d.x},${d.y})`);
        });
    },

    getNodeRadius(type) {
        switch(type) {
            case 'Contract': return 16;
            case 'Vendor': return 14;
            case 'Clause': return 10;
            case 'RiskType': return 12;
            case 'Date': return 10;
            default: return 12;
        }
    },

    getNodeColor(type) {
        switch(type) {
            case 'Contract': return '#3b82f6'; // Blue
            case 'Vendor': return '#ef4444'; // Red
            case 'Clause': return '#fbbf24'; // Yellow
            case 'RiskType': return '#a78bfa'; // Purple
            case 'Date': return '#10b981'; // Green
            default: return '#94a3b8';
        }
    },

    getNodeCaption(d) {
        const props = d.properties;
        const name = props.name || props.title || props.id || props.date || d.id;
        return name.length > 15 ? name.substring(0, 15) + '...' : name;
    },

    inspectNode(node) {
        const sidebar = document.getElementById('graph-inspector-content');
        if (!sidebar) return;

        const props = node.properties;
        let propsHtml = '';

        for (const [key, value] of Object.entries(props)) {
            propsHtml += `
                <div style="margin-bottom:10px;">
                    <span style="font-size:0.75rem; color:var(--text-muted); display:block; text-transform:uppercase;">${key}</span>
                    <strong style="font-size:0.9rem; color:var(--text-primary); word-break:break-all;">${value}</strong>
                </div>
            `;
        }

        sidebar.innerHTML = `
            <div style="display:flex; align-items:center; gap:8px; margin-bottom:15px; padding-bottom:10px; border-bottom:1px solid var(--border-color);">
                <span style="display:inline-block; width:12px; height:12px; border-radius:50%; background:${this.getNodeColor(node.type)};"></span>
                <span style="text-transform:uppercase; font-size:0.8rem; font-weight:bold; color:var(--text-secondary);">${node.type} Node</span>
            </div>
            
            <h4 style="margin-top:0; color:var(--accent-teal); font-size:1.1rem; line-height:1.4;">${props.name || props.title || props.id || props.date || 'Unnamed Entity'}</h4>
            
            <div style="margin-top:20px;">
                ${propsHtml || '<span style="color:var(--text-muted);">No property metadata.</span>'}
            </div>
        `;
    }
};
window.GraphView = GraphView;
