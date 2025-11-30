import os
import re
import threading
import asyncio
import httpx
from flask import Flask, request, jsonify, render_template, send_file
import pandas as pd
from bs4 import BeautifulSoup
from io import BytesIO

# --- Configuration ---
app = Flask(__name__)
EXCEL_FILE = 'scraped_data.xlsx'
file_lock = threading.Lock()

# --- Regex ---
EMAIL_REGEX = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
PHONE_REGEX = r'(\+91|0)?[6-9][0-9]{9}'

# --- Async Scraping Engine ---
async def scrape_page_for_contacts(client, page_url):
    """
    Asynchronously scrapes a single page for email and phone numbers.
    """
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
        response = await client.get(page_url, timeout=15, headers=headers, follow_redirects=True)
        response.raise_for_status()
    except httpx.RequestError as e:
        print(f"Error fetching URL {page_url}: {e}")
        return {'url': page_url, 'emails': [], 'phones': [], 'error': f"Failed to fetch: {e}"}
    
    soup = BeautifulSoup(response.text, 'html.parser')
    text = soup.get_text()
    emails = set(re.findall(EMAIL_REGEX, text))
    phones = set(re.findall(PHONE_REGEX, text))
    return {'url': page_url, 'emails': list(emails), 'phones': list(phones)}

async def run_scraper(urls):
    """
    Sets up and runs the concurrent scraping tasks for the provided URLs.
    """
    async with httpx.AsyncClient() as client:
        tasks = [scrape_page_for_contacts(client, url) for url in urls]
        results = await asyncio.gather(*tasks)
    return results

# --- Synchronous Data Handling ---
def save_data(emails_to_save, phones_to_save):
    """
    Saves new, unique emails and phone numbers to the Excel file.
    """
    with file_lock:
        try:
            if os.path.exists(EXCEL_FILE):
                df = pd.read_excel(EXCEL_FILE)
                existing_emails = set(df['Email'].dropna())
                existing_phones = set(df['Mobile Number'].dropna())
            else:
                df = pd.DataFrame(columns=['Email', 'Mobile Number'])
                existing_emails = set()
                existing_phones = set()

            new_emails = [email for email in emails_to_save if email not in existing_emails]
            new_phones = [phone for phone in phones_to_save if phone not in existing_phones]

            if not new_emails and not new_phones:
                return

            new_data = {
                'Email': pd.Series(new_emails),
                'Mobile Number': pd.Series(new_phones)
            }
            new_df = pd.DataFrame(dict([(k, pd.Series(v)) for k,v in new_data.items()]))

            final_df = pd.concat([df, new_df], ignore_index=True)
            final_df.to_excel(EXCEL_FILE, index=False)
        except Exception as e:
            print(f"Error saving to Excel: {e}")

# --- API Endpoints ---
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/scrape', methods=['POST'])
def scrape():
    """
    Synchronous endpoint that calls the async scraper and aggregates results.
    """
    data = request.get_json()
    urls_raw = data.get('urls')
    if not urls_raw or not isinstance(urls_raw, list): return jsonify({'error': 'A list of URLs is required'}), 400

    urls_to_scrape = []
    for raw_url in urls_raw:
        url = raw_url.strip()
        if not url: continue
        if not url.startswith('http://') and not url.startswith('https://'):
            url = 'https://' + url
        urls_to_scrape.append(url)
    
    if not urls_to_scrape: return jsonify({'error': 'No valid URLs provided'}), 400

    # Run scraper and get results
    results = asyncio.run(run_scraper(urls_to_scrape))

    # Aggregate all emails and phones into two flat, unique lists
    all_emails = set()
    all_phones = set()
    for res in results:
        if res.get('error'): continue
        for email in res.get('emails', []):
            all_emails.add(email)
        for phone in res.get('phones', []):
            all_phones.add(phone)
    
    # Convert sets to lists for JSON response and saving
    email_list = list(all_emails)
    phone_list = list(all_phones)

    # Save data in a background thread
    threading.Thread(target=save_data, args=(email_list, phone_list)).start()

    return jsonify({'emails': email_list, 'phones': phone_list})

@app.route('/download/<filetype>')
def download_file(filetype):
    """Serves the collected data file for download."""
    with file_lock:
        if not os.path.exists(EXCEL_FILE): return "No data file found.", 404
        df = pd.read_excel(EXCEL_FILE)
        output = BytesIO()
        filename, mimetype = f"scraped_data.{filetype}", f"text/{filetype}"
        
        if filetype == 'excel':
            df.to_excel(output, index=False, sheet_name='Scraped Data')
            mimetype = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            filename = 'scraped_data.xlsx'
        elif filetype == 'csv':
            df.to_csv(output, index=False, encoding='utf-8')
        elif filetype == 'json':
            # For this simpler structure, a different JSON format might be better
            json_data = {
                "emails": df["Email"].dropna().tolist(),
                "mobile_numbers": df["Mobile Number"].dropna().tolist()
            }
            output.write(pd.io.json.dumps(json_data, indent=4).encode('utf-8'))
            mimetype = 'application/json'
        else:
            return "Invalid file type requested.", 400
        
        output.seek(0)
        return send_file(output, mimetype=mimetype, as_attachment=True, download_name=filename)

# --- Main ---
if __name__ == '__main__':
    app.run(debug=True)