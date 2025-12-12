// Modern JavaScript for WebScraper Pro
document.addEventListener('DOMContentLoaded', () => {
    // DOM Elements
    const form = document.getElementById('scrape-form');
    const urlInput = document.getElementById('url-input');
    const scrapeButton = document.getElementById('scrape-button');
    const loadingIndicator = document.getElementById('loading-indicator');
    const messageArea = document.getElementById('message-area');
    const resultsContainer = document.getElementById('results-container');
    const resultsTbody = document.getElementById('results-tbody');
    const downloadBtn = document.getElementById('download-btn');
    const clearBtn = document.getElementById('clear-btn');
    const themeToggle = document.getElementById('theme-toggle');
    
    // Stats Elements
    const totalEmails = document.getElementById('total-emails');
    const totalPhones = document.getElementById('total-phones');
    const totalUrls = document.getElementById('total-urls');
    
    // Button text elements
    const btnText = scrapeButton.querySelector('.btn-text');
    const btnLoading = scrapeButton.querySelector('.btn-loading');
    
    let currentResults = [];

    // Initialize animations
    initializeAnimations();
    
    // Theme Toggle
    themeToggle.addEventListener('click', () => {
        const icon = themeToggle.querySelector('i');
        if (icon.classList.contains('fa-moon')) {
            icon.classList.remove('fa-moon');
            icon.classList.add('fa-sun');
            // Add light theme styles here if needed
        } else {
            icon.classList.remove('fa-sun');
            icon.classList.add('fa-moon');
        }
    });

    // Smooth scroll to section
    function scrollToSection(sectionId) {
        const section = document.getElementById(sectionId);
        if (section) {
            section.scrollIntoView({ behavior: 'smooth' });
        }
    }

    // Form submission handler
    form.addEventListener('submit', async (event) => {
        event.preventDefault();
        
        const urls = urlInput.value
            .split('\n')
            .map(url => url.trim())
            .filter(url => url);
            
        if (urls.length === 0) {
            showMessage('Please enter at least one URL', 'error');
            return;
        }

        // Start loading state
        setLoadingState(true);
        hideResults();
        hideMessage();

        try {
            const response = await fetch('/scrape', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ urls: urls }),
            });

            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.error || 'Scraping failed');
            }

            const data = await response.json();
            
            if (data.success) {
                displayResults(data.data, data.summary);
                showMessage(`Success! Found ${data.summary.total_emails} emails and ${data.summary.total_phones} phones from ${data.summary.total_urls_scraped} pages.`, 'success');
                downloadBtn.style.display = 'inline-flex';
                clearBtn.style.display = 'inline-flex';
            } else {
                showMessage('Scraping completed but no results found', 'error');
            }

        } catch (error) {
            console.error('Scraping error:', error);
            showMessage(`Error: ${error.message}`, 'error');
        } finally {
            setLoadingState(false);
        }
    });

    // Set loading state
    function setLoadingState(isLoading) {
        scrapeButton.disabled = isLoading;
        loadingIndicator.style.display = isLoading ? 'block' : 'none';
        
        if (isLoading) {
            btnText.style.display = 'none';
            btnLoading.style.display = 'flex';
        } else {
            btnText.style.display = 'flex';
            btnLoading.style.display = 'none';
        }
    }

    // Display results in table
    function displayResults(data, summary) {
        currentResults = data;
        
        // Update stats
        animateCounter(totalEmails, summary.total_emails);
        animateCounter(totalPhones, summary.total_phones);
        animateCounter(totalUrls, summary.total_urls_scraped);
        
        // Clear existing results
        resultsTbody.innerHTML = '';
        
        if (data.length === 0) {
            const row = resultsTbody.insertRow();
            const cell = row.insertCell();
            cell.colSpan = 3;
            cell.textContent = 'No results found';
            cell.style.textAlign = 'center';
            cell.style.color = 'var(--text-muted)';
        } else {
            data.forEach((item, index) => {
                const row = resultsTbody.insertRow();
                row.style.animation = `fadeIn 0.3s ease ${index * 0.05}s`;
                
                // Type cell
                const typeCell = row.insertCell();
                const typeIcon = item.type === 'Email' ? 'fa-envelope' : 'fa-phone';
                const typeColor = item.type === 'Email' ? 'var(--accent-blue)' : 'var(--accent-purple)';
                typeCell.innerHTML = `
                    <span style="display: flex; align-items: center; gap: 0.5rem;">
                        <i class="fas ${typeIcon}" style="color: ${typeColor};"></i>
                        ${item.type}
                    </span>
                `;
                
                // Value cell
                const valueCell = row.insertCell();
                valueCell.textContent = item.value;
                
                // Source URL cell
                const sourceCell = row.insertCell();
                sourceCell.innerHTML = `
                    <a href="${item.source}" target="_blank" rel="noopener noreferrer">
                        ${shortenUrl(item.source)}
                    </a>
                `;
            });
        }
        
        resultsContainer.style.display = 'block';
    }

    // Animate counter
    function animateCounter(element, target) {
        const duration = 1000;
        const start = 0;
        const increment = target / (duration / 16);
        let current = start;
        
        const timer = setInterval(() => {
            current += increment;
            if (current >= target) {
                current = target;
                clearInterval(timer);
            }
            element.textContent = Math.floor(current);
        }, 16);
    }

    // Shorten URL for display
    function shortenUrl(url) {
        try {
            const urlObj = new URL(url);
            return urlObj.hostname + (urlObj.pathname !== '/' ? urlObj.pathname : '');
        } catch {
            return url.length > 30 ? url.substring(0, 30) + '...' : url;
        }
    }

    // Show message
    function showMessage(message, type) {
        messageArea.textContent = message;
        messageArea.className = `message-area message-${type}`;
        messageArea.style.display = 'block';
        
        // Auto-hide success messages after 5 seconds
        if (type === 'success') {
            setTimeout(() => {
                hideMessage();
            }, 5000);
        }
    }

    // Hide message
    function hideMessage() {
        messageArea.style.display = 'none';
    }

    // Hide results
    function hideResults() {
        resultsContainer.style.display = 'none';
        downloadBtn.style.display = 'none';
        clearBtn.style.display = 'none';
    }

    // Download button handler
    downloadBtn.addEventListener('click', () => {
        window.location.href = '/download';
    });

    // Clear button handler
    clearBtn.addEventListener('click', () => {
        hideResults();
        hideMessage();
        urlInput.value = '';
        currentResults = [];
        
        // Reset stats
        totalEmails.textContent = '0';
        totalPhones.textContent = '0';
        totalUrls.textContent = '0';
    });

    // Initialize animations
    function initializeAnimations() {
        // Animate hero stats on page load
        const observerOptions = {
            threshold: 0.5,
            rootMargin: '0px 0px -100px 0px'
        };

        const observer = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    const statNumbers = entry.target.querySelectorAll('.stat-number');
                    statNumbers.forEach(stat => {
                        const target = parseInt(stat.getAttribute('data-target'));
                        animateCounter(stat, target);
                    });
                    observer.unobserve(entry.target);
                }
            });
        }, observerOptions);

        const heroStats = document.querySelector('.hero-stats');
        if (heroStats) {
            observer.observe(heroStats);
        }

        // Add hover effects to feature cards
        const featureCards = document.querySelectorAll('.feature-card');
        featureCards.forEach(card => {
            card.addEventListener('mouseenter', () => {
                card.style.transform = 'translateY(-5px)';
            });
            
            card.addEventListener('mouseleave', () => {
                card.style.transform = 'translateY(0)';
            });
        });

        // Add ripple effect to buttons
        const buttons = document.querySelectorAll('button');
        buttons.forEach(button => {
            button.addEventListener('click', function(e) {
                const ripple = document.createElement('span');
                const rect = this.getBoundingClientRect();
                const size = Math.max(rect.width, rect.height);
                const x = e.clientX - rect.left - size / 2;
                const y = e.clientY - rect.top - size / 2;
                
                ripple.style.cssText = `
                    position: absolute;
                    width: ${size}px;
                    height: ${size}px;
                    border-radius: 50%;
                    background: rgba(255, 255, 255, 0.3);
                    left: ${x}px;
                    top: ${y}px;
                    pointer-events: none;
                    transform: scale(0);
                    animation: ripple 0.6s linear;
                `;
                
                this.style.position = 'relative';
                this.style.overflow = 'hidden';
                this.appendChild(ripple);
                
                setTimeout(() => {
                    ripple.remove();
                }, 600);
            });
        });
    }

    // Add ripple animation
    const style = document.createElement('style');
    style.textContent = `
        @keyframes ripple {
            to {
                transform: scale(4);
                opacity: 0;
            }
        }
    `;
    document.head.appendChild(style);

    // Handle URL input validation
    urlInput.addEventListener('input', () => {
        const urls = urlInput.value.split('\n');
        const validUrls = urls.filter(url => {
            const trimmed = url.trim();
            if (!trimmed) return true; // Allow empty lines
            try {
                new URL(trimmed.startsWith('http') ? trimmed : `https://${trimmed}`);
                return true;
            } catch {
                return false;
            }
        });
        
        if (urls.length !== validUrls.length) {
            urlInput.style.borderColor = 'var(--accent-pink)';
        } else {
            urlInput.style.borderColor = '';
        }
    });

    // Keyboard shortcuts
    document.addEventListener('keydown', (e) => {
        // Ctrl/Cmd + Enter to submit form
        if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
            if (document.activeElement === urlInput) {
                form.dispatchEvent(new Event('submit'));
            }
        }
        
        // Escape to clear results
        if (e.key === 'Escape') {
            hideResults();
            hideMessage();
        }
    });

    // Add smooth parallax effect to hero shapes
    window.addEventListener('scroll', () => {
        const scrolled = window.pageYOffset;
        const shapes = document.querySelectorAll('.floating-shape');
        
        shapes.forEach((shape, index) => {
            const speed = 0.5 + (index * 0.1);
            shape.style.transform = `translateY(${scrolled * speed}px)`;
        });
    });

    // Auto-resize textarea
    urlInput.addEventListener('input', function() {
        this.style.height = 'auto';
        this.style.height = Math.min(this.scrollHeight, 200) + 'px';
    });

    console.log('WebScraper Pro initialized successfully!');
});