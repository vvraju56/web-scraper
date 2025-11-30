document.addEventListener('DOMContentLoaded', () => {
    const form = document.getElementById('scrape-form');
    const urlInput = document.getElementById('url-input');
    const scrapeButton = document.getElementById('scrape-button');
    const loadingIndicator = document.getElementById('loading-indicator');
    const messageArea = document.getElementById('message-area');
    const resultsTableBody = document.querySelector('#results-table tbody');
    const downloadContainer = document.getElementById('download-container');
    const downloadExcelButton = document.getElementById('download-excel-button');
    const downloadCsvButton = document.getElementById('download-csv-button');
    const downloadJsonButton = document.getElementById('download-json-button');
    const darkModeToggle = document.getElementById('dark-mode-toggle');

    // --- Dark Mode ---
    const applyDarkMode = (isDark) => {
        if (isDark) {
            document.body.classList.add('dark-mode');
            darkModeToggle.textContent = 'Toggle Light Mode';
        } else {
            document.body.classList.remove('dark-mode');
            darkModeToggle.textContent = 'Toggle Dark Mode';
        }
    };

    const isDarkMode = localStorage.getItem('darkMode') === 'true';
    applyDarkMode(isDarkMode);

    darkModeToggle.addEventListener('click', () => {
        const newDarkModeState = !document.body.classList.contains('dark-mode');
        localStorage.setItem('darkMode', newDarkModeState);
        applyDarkMode(newDarkModeState);
    });

    // --- Form Submission ---
    form.addEventListener('submit', async (event) => {
        event.preventDefault();
        const urls = urlInput.value.split('\n').map(url => url.trim()).filter(url => url);
        if (urls.length === 0) return;

        // Reset UI
        scrapeButton.disabled = true;
        loadingIndicator.classList.remove('hidden');
        messageArea.innerHTML = '';
        messageArea.className = '';
        resultsTableBody.innerHTML = ''; 
        downloadContainer.classList.add('hidden');

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
            displayResults(data.emails, data.phones);
            displayMessage(`Scraping complete! Found ${data.emails.length} unique emails and ${data.phones.length} unique phones across all URLs.`, 'success');
        
        } catch (error) {
            displayMessage(`Error: ${error.message}`, 'error');
        } finally {
            scrapeButton.disabled = false;
            loadingIndicator.classList.add('hidden');
        }
    });

    // --- Display Logic ---
    function displayResults(emails, phones) {
        const maxRows = Math.max(emails.length, phones.length);
        if (maxRows > 0) {
            downloadContainer.classList.remove('hidden');
        } else {
            downloadContainer.classList.add('hidden');
        }

        for (let i = 0; i < maxRows; i++) {
            const row = resultsTableBody.insertRow();
            const emailCell = row.insertCell(0);
            const phoneCell = row.insertCell(1);
            emailCell.textContent = emails[i] || '';
            phoneCell.textContent = phones[i] || '';
        }
    }

    function displayMessage(message, type) {
        messageArea.textContent = message;
        messageArea.className = `message-${type}`;
    }

    // --- Download Listeners ---
    downloadExcelButton.addEventListener('click', () => { window.location.href = '/download/excel'; });
    downloadCsvButton.addEventListener('click', () => { window.location.href = '/download/csv'; });
    downloadJsonButton.addEventListener('click', () => { window.location.href = '/download/json'; });
});