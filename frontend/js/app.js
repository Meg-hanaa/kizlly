/* 
   KIZLLY — App Entry & Router
    */

const App = {
    init() {
        AuthManager.init();
        AlertManager.init();
        this.setupRouter();
        this.setupNavbarActiveLink();
    },

    setupRouter() {
        // Listen to hash changes
        window.addEventListener('hashchange', () => {
            const hash = window.location.hash || '#/upload';
            this.navigate(hash);
        });

        // Trigger on load
        const initialHash = window.location.hash || '#/home';
        this.navigate(initialHash);
    },

    navigate(hash) {
        const appContainer = document.getElementById('app');
        if (!appContainer) return;

        // Clear existing SVG/simulation elements to prevent memory leaks from force directed layout
        if (GraphView.simulation) {
            GraphView.simulation.stop();
            GraphView.simulation = null;
        }

        // Parse route parameters e.g., #/review/some-id
        const parts = hash.split('/');
        const primaryRoute = parts[1] || 'home';
        const parameter = parts[2] || null;

        // Update nav UI active class
        this.updateNavActive(primaryRoute);

        // Views router

        switch (primaryRoute) {
            case 'home':
                HomeView.render(appContainer);
                break;
            case 'upload':
                UploadView.render(appContainer);
                break;
            case 'review':
                if (parameter) {
                    UploadView.render(appContainer, parameter);
                } else {
                    window.location.hash = '#/upload';
                }
                break;
            case 'portfolio':
                DashboardView.render(appContainer);
                break;
            case 'graph':
                GraphView.render(appContainer);
                break;
            case 'audit':
                AuditView.render(appContainer);
                break;
            default:
                window.location.hash = '#/home';
        }
    },

    setupNavbarActiveLink() {
        const links = document.querySelectorAll('.nav-links a');
        links.forEach(link => {
            link.addEventListener('click', (e) => {
                const href = link.getAttribute('href');
                if (href.startsWith('#')) {
                    links.forEach(l => l.classList.remove('active'));
                    link.classList.add('active');
                }
            });
        });
    },

    updateNavActive(currentRoute) {
        const links = document.querySelectorAll('.nav-links a');
        links.forEach(link => {
            const href = link.getAttribute('href');
            if (href === `#/${currentRoute}`) {
                link.classList.add('active');
            } else {
                link.classList.remove('active');
            }
        });
    },

    showToast(message, type = 'info') {
        const toastContainer = document.getElementById('toast-container');
        if (!toastContainer) return;

        const toast = document.createElement('div');
        toast.className = `toast ${type}`;
        
        let symbol = '';
        if (type === 'success') symbol = '';
        if (type === 'error') symbol = '';
        if (type === 'warning') symbol = '';

        toast.innerHTML = `
            <span>${symbol}</span>
            <span style="margin-left: 8px;">${message}</span>
        `;

        toastContainer.appendChild(toast);

        // Slide in
        setTimeout(() => {
            toast.style.transform = 'translateX(0)';
            toast.style.opacity = '1';
        }, 100);

        // Remove after 4 seconds
        setTimeout(() => {
            toast.style.transform = 'translateX(120%)';
            toast.style.opacity = '0';
            setTimeout(() => toast.remove(), 300);
        }, 4000);
    }
};

// Start the application when the DOM is fully parsed and loaded
document.addEventListener('DOMContentLoaded', () => {
    App.init();
});
