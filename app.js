document.addEventListener('DOMContentLoaded', () => {
    initTheme();
    fetchJobs();
    setupSearch();
});

// Theme Management
function initTheme() {
    const toggleBtn = document.getElementById('theme-toggle');
    const root = document.documentElement;
    const moonIcon = document.getElementById('moon-icon');
    
    // Check saved theme
    const savedTheme = localStorage.getItem('theme') || 'dark';
    root.setAttribute('data-theme', savedTheme);
    updateIcon(savedTheme, moonIcon);

    toggleBtn.addEventListener('click', () => {
        const currentTheme = root.getAttribute('data-theme');
        const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
        
        root.setAttribute('data-theme', newTheme);
        localStorage.setItem('theme', newTheme);
        updateIcon(newTheme, moonIcon);
    });
}

function updateIcon(theme, icon) {
    if (theme === 'light') {
        icon.innerHTML = '<circle cx="12" cy="12" r="5"></circle><line x1="12" y1="1" x2="12" y2="3"></line><line x1="12" y1="21" x2="12" y2="23"></line><line x1="4.22" y1="4.22" x2="5.64" y2="5.64"></line><line x1="18.36" y1="18.36" x2="19.78" y2="19.78"></line><line x1="1" y1="12" x2="3" y2="12"></line><line x1="21" y1="12" x2="23" y2="12"></line><line x1="4.22" y1="19.78" x2="5.64" y2="18.36"></line><line x1="18.36" y1="5.64" x2="19.78" y2="4.22"></line>';
    } else {
        icon.innerHTML = '<path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"></path>';
    }
}

// Data Fetching and Rendering
let allJobs = [];

async function fetchJobs() {
    try {
        // Fetch the generated JSON file
        const response = await fetch('data/jobs.json');
        if (!response.ok) throw new Error('Network response was not ok');
        
        allJobs = await response.json();
        renderJobs(allJobs);
        
    } catch (error) {
        console.error('Error fetching jobs:', error);
        document.querySelectorAll('.jobs-grid').forEach(grid => {
            grid.innerHTML = '<div class="job-card" style="text-align:center;color:var(--danger)">Error loading data. Please try again later.</div>';
        });
    }
}

function renderJobs(jobs) {
    const latestGrid = document.getElementById('latest-jobs-grid');
    const admitGrid = document.getElementById('admit-cards-grid');
    const resultsGrid = document.getElementById('results-grid');

    // Clear skeletons
    latestGrid.innerHTML = '';
    admitGrid.innerHTML = '';
    resultsGrid.innerHTML = '';

    // Categorize
    const latest = jobs.filter(j => j.notificationType === 'recruitment' || j.notificationType === 'notification');
    const admitCards = jobs.filter(j => j.notificationType === 'admit_card');
    const results = jobs.filter(j => j.notificationType === 'result');

    // Render
    renderGrid(latest, latestGrid, 'No new jobs found.');
    renderGrid(admitCards, admitGrid, 'No new admit cards.');
    renderGrid(results, resultsGrid, 'No new results.');
}

function renderGrid(jobsArray, gridElement, emptyMessage) {
    if (jobsArray.length === 0) {
        gridElement.innerHTML = `<div class="job-card" style="text-align:center;color:var(--text-muted)">${emptyMessage}</div>`;
        return;
    }

    jobsArray.forEach(job => {
        const card = document.createElement('div');
        card.className = 'job-card';
        
        // Clean up title (remove brackets if present, e.g. "[SSC]")
        let cleanTitle = job.title.replace(/^\[.*?\]\s*/, '');
        
        // Link to the newly created dedicated details page!
        let actionLink = `job-details.html?id=${job.id}`;
        let actionText = 'View Full Details';
        
        // Format Date
        let dateStr = 'Recently Updated';
        if (job.importantDates && job.importantDates.notificationDate) {
            try {
                const d = new Date(job.importantDates.notificationDate);
                dateStr = d.toLocaleDateString('en-IN', { day: 'numeric', month: 'short', year: 'numeric' });
            } catch(e) {}
        } else if (job.lastUpdated) {
            try {
                const d = new Date(job.lastUpdated);
                dateStr = d.toLocaleDateString('en-IN', { day: 'numeric', month: 'short', year: 'numeric' });
            } catch(e) {}
        }

        // Vacancy Badge
        let vacancyBadge = job.totalVacancies ? `<span style="background:rgba(16, 185, 129, 0.1);color:var(--success);padding:2px 8px;border-radius:10px;font-size:11px;font-weight:700">${job.totalVacancies} Posts</span>` : '';

        card.innerHTML = `
            <div class="job-org">
                <span>${job.organizationShort || 'GOVT'}</span>
                ${vacancyBadge}
            </div>
            <h3 class="job-title">${cleanTitle}</h3>
            <div class="job-meta">
                <div class="meta-item">
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="4" width="18" height="18" rx="2" ry="2"></rect><line x1="16" y1="2" x2="16" y2="6"></line><line x1="8" y1="2" x2="8" y2="6"></line><line x1="3" y1="10" x2="21" y2="10"></line></svg>
                    ${dateStr}
                </div>
            </div>
            <div class="job-actions">
                <a href="${actionLink}" target="_blank" rel="noopener noreferrer" class="btn btn-primary">
                    ${actionText}
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M5 12h14M12 5l7 7-7 7"/></svg>
                </a>
            </div>
        `;
        gridElement.appendChild(card);
    });
}

// Search functionality
function setupSearch() {
    const searchInput = document.getElementById('global-search');
    
    searchInput.addEventListener('input', (e) => {
        const term = e.target.value.toLowerCase();
        
        if (!term) {
            renderJobs(allJobs);
            return;
        }
        
        const filtered = allJobs.filter(job => {
            return (
                job.title.toLowerCase().includes(term) ||
                (job.organization && job.organization.toLowerCase().includes(term)) ||
                (job.organizationShort && job.organizationShort.toLowerCase().includes(term))
            );
        });
        
        renderJobs(filtered);
    });
}
