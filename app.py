import os
import re
import threading
import asyncio
import httpx
from flask import Flask, request, jsonify, render_template, send_file
from flask_cors import CORS
import pandas as pd
from bs4 import BeautifulSoup
from io import BytesIO
from datetime import datetime
from urllib.parse import urljoin, urlparse
import time

app = Flask(__name__)
CORS(app)

EXCEL_FILE = 'scraped_data.xlsx'
file_lock = threading.Lock()

EMAIL_REGEX = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
PHONE_REGEX = r'(\+\d{1,3}[-.\s]?)?\(?\d{1,4}\)?[-.\s]?\d{1,4}[-.\s]?\d{1,9}'

async def scrape_page_for_contacts(client, page_url):
    """Enhanced async scraping with better error handling and data extraction"""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
        response = await client.get(page_url, timeout=20, headers=headers, follow_redirects=True)
        response.raise_for_status()
    except Exception as e:
        return {'url': page_url, 'emails': [], 'phones': [], 'error': str(e)}
    
    soup = BeautifulSoup(response.text, 'html.parser')
    
    # Remove script and style elements
    for script in soup(["script", "style"]):
        script.decompose()
    
    text = soup.get_text()
    
    # Enhanced email extraction
    emails = set()
    email_matches = re.findall(EMAIL_REGEX, text)
    for email in email_matches:
        email = email.lower().strip()
        if len(email) > 5 and '.' in email.split('@')[1]:
            emails.add(email)
    
    # Enhanced phone extraction
    phones = set()
    phone_matches = re.findall(PHONE_REGEX, text)
    for phone in phone_matches:
        phone = re.sub(r'[^\d+]', '', phone)
        if len(phone) >= 10:
            phones.add(phone)
    
    return {
        'url': page_url,
        'emails': list(emails),
        'phones': list(phones),
        'timestamp': datetime.now().isoformat()
    }

async def discover_internal_links(client, base_url, max_pages=10):
    """Discover internal links from the main page"""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
        response = await client.get(base_url, timeout=20, headers=headers, follow_redirects=True)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        base_domain = urlparse(base_url).netloc
        
        links = set([base_url])
        
        for link in soup.find_all('a', href=True):
            href = link['href']
            full_url = urljoin(base_url, href)
            parsed_url = urlparse(full_url)
            
            if parsed_url.netloc == base_domain and len(links) < max_pages:
                links.add(full_url)
        
        return list(links)[:max_pages]
    except:
        return [base_url]

async def run_scraper(urls):
    """Enhanced scraper with internal link discovery"""
    async with httpx.AsyncClient() as client:
        all_urls_to_scrape = []
        
        # Discover internal links for each provided URL
        for url in urls:
            discovered_urls = await discover_internal_links(client, url)
            all_urls_to_scrape.extend(discovered_urls)
        
        # Remove duplicates
        all_urls_to_scrape = list(set(all_urls_to_scrape))
        
        # Scrape all discovered URLs
        tasks = [scrape_page_for_contacts(client, url) for url in all_urls_to_scrape]
        results = await asyncio.gather(*tasks)
        
    return results

def save_data_with_sources(scraped_results):
    """Save data with source URL tracking and timestamps"""
    with file_lock:
        try:
            data_rows = []
            
            for result in scraped_results:
                if result.get('error'):
                    continue
                    
                source_url = result['url']
                timestamp = result.get('timestamp', datetime.now().isoformat())
                
                # Add emails
                for email in result.get('emails', []):
                    data_rows.append({
                        'Timestamp': timestamp,
                        'Type': 'Email',
                        'Value': email,
                        'Source URL': source_url
                    })
                
                # Add phones
                for phone in result.get('phones', []):
                    data_rows.append({
                        'Timestamp': timestamp,
                        'Type': 'Phone',
                        'Value': phone,
                        'Source URL': source_url
                    })
            
            if not data_rows:
                return
            
            new_df = pd.DataFrame(data_rows)
            
            # Load existing data if file exists
            if os.path.exists(EXCEL_FILE):
                existing_df = pd.read_excel(EXCEL_FILE)
                # Remove duplicates based on Value + Source URL
                combined_df = pd.concat([existing_df, new_df], ignore_index=True)
                combined_df = combined_df.drop_duplicates(subset=['Value', 'Source URL'], keep='first')
            else:
                combined_df = new_df
            
            # Sort by timestamp
            combined_df = combined_df.sort_values('Timestamp', ascending=False)
            combined_df.to_excel(EXCEL_FILE, index=False)
            
        except Exception as e:
            print(f"Error saving to Excel: {e}")

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/scrape', methods=['POST'])
def scrape():
    """Enhanced scraping endpoint with better data structure"""
    data = request.get_json()
    urls_raw = data.get('urls')
    
    if not urls_raw or not isinstance(urls_raw, list):
        return jsonify({'error': 'A list of URLs is required'}), 400

    urls_to_scrape = []
    for raw_url in urls_raw:
        url = raw_url.strip()
        if not url:
            continue
        if not url.startswith('http://') and not url.startswith('https://'):
            url = 'https://' + url
        urls_to_scrape.append(url)
    
    if not urls_to_scrape:
        return jsonify({'error': 'No valid URLs provided'}), 400

    # Run enhanced scraper
    results = asyncio.run(run_scraper(urls_to_scrape))
    
    # Process results for response
    response_data = []
    all_emails = set()
    all_phones = set()
    
    for result in results:
        if result.get('error'):
            continue
            
        source_url = result['url']
        
        for email in result.get('emails', []):
            if email not in all_emails:
                all_emails.add(email)
                response_data.append({
                    'type': 'Email',
                    'value': email,
                    'source': source_url
                })
        
        for phone in result.get('phones', []):
            if phone not in all_phones:
                all_phones.add(phone)
                response_data.append({
                    'type': 'Phone',
                    'value': phone,
                    'source': source_url
                })
    
    # Save data in background
    threading.Thread(target=save_data_with_sources, args=(results,)).start()
    
    return jsonify({
        'success': True,
        'data': response_data,
        'summary': {
            'total_emails': len(all_emails),
            'total_phones': len(all_phones),
            'total_urls_scraped': len([r for r in results if not r.get('error')])
        }
    })

@app.route('/download')
def download_excel():
    """Download the latest Excel file"""
    with file_lock:
        if not os.path.exists(EXCEL_FILE):
            return jsonify({'error': 'No data file found'}), 404
        
        return send_file(
            EXCEL_FILE,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name=f'scraped_data_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx'
        )

@app.route('/health')
def health_check():
    """Health check endpoint for deployment"""
    return jsonify({'status': 'healthy', 'timestamp': datetime.now().isoformat()})

if __name__ == '__main__':
    app.run(debug=True)