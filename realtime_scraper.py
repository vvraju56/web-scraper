import requests
from bs4 import BeautifulSoup
import re
import pandas as pd
import time

def extract_data(text):
    """Extracts emails and mobile numbers from a given text."""
    email_pattern = r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"
    mobile_pattern = r"\b(?:\+?\d{1,3}[-.\s]?)?\d{10}\b"
    
    emails = list(set(re.findall(email_pattern, text)))
    mobiles = list(set(re.findall(mobile_pattern, text)))
    
    return emails, mobiles

def scrape_site(url):
    """Scrapes a website for text content."""
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'}
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()  # Raise an exception for bad status codes
        soup = BeautifulSoup(response.text, "html.parser")
        return soup.get_text()
    except requests.exceptions.RequestException as e:
        print(f"Error scraping {url}: {e}")
        return None

def save_to_excel(data, filename="scraped_output.xlsx"):
    """Saves a list of dictionaries to an Excel file."""
    df = pd.DataFrame(data)
    try:
        # Check if the file already exists
        with pd.ExcelWriter(filename, mode='a', engine='openpyxl', if_sheet_exists='overlay') as writer:
            # Check if the sheet 'Sheet1' exists
            if 'Sheet1' in writer.sheets:
                startrow = writer.sheets['Sheet1'].max_row
                if startrow > 0 and 'Sheet1' in writer.book.sheetnames: # if sheet has content
                    header = False
                else:
                    header = True
                df.to_excel(writer, index=False, header=header, startrow=startrow if startrow > 0 else 0, sheet_name='Sheet1')

            else:
                df.to_excel(writer, index=False, sheet_name='Sheet1')

    except FileNotFoundError:
        df.to_excel(filename, index=False, sheet_name='Sheet1')


import sys

def main():
    print("=== Real-time Web Scraping Tool (Email + Mobile Extractor) ===")
    if len(sys.argv) > 1:
        url = sys.argv[1]
        print(f"URL to scrape: {url}")
    else:
        url = input("\nEnter URL to scrape: ")
    
    interval = 5  # Default interval set to 5 seconds to avoid interactive input

    scraped_data = []
    # Load existing data to avoid duplicates
    try:
        existing_df = pd.read_excel("scraped_output.xlsx")
        for index, row in existing_df.iterrows():
            if 'Type' in row and 'Value' in row:
                scraped_data.append(row.to_dict())
            elif 'Email' in row and pd.notna(row['Email']):
                scraped_data.append({'Timestamp': pd.Timestamp.now(), 'Type': 'Email', 'Value': row['Email']})
            elif 'Mobile Number' in row and pd.notna(row['Mobile Number']):
                scraped_data.append({'Timestamp': pd.Timestamp.now(), 'Type': 'Mobile', 'Value': row['Mobile Number']})
    except FileNotFoundError:
        pass


    try:
        while True:
            print(f"\nScraping {url}...")
            text = scrape_site(url)
            
            if text:
                emails, mobiles = extract_data(text)
                
                new_data = []
                for email in emails:
                    if email not in [item['Value'] for item in scraped_data if item['Type'] == 'Email']:
                        new_data.append({'Timestamp': pd.Timestamp.now(), 'Type': 'Email', 'Value': email})
                
                for mobile in mobiles:
                    if mobile not in [item['Value'] for item in scraped_data if item['Type'] == 'Mobile']:
                        new_data.append({'Timestamp': pd.Timestamp.now(), 'Type': 'Mobile', 'Value': mobile})

                if new_data:
                    scraped_data.extend(new_data)
                    save_to_excel(new_data)
                    print(f"Found {len(new_data)} new items.")
                else:
                    print("No new data found.")
            
            time.sleep(interval)

    except KeyboardInterrupt:
        print("\nScraping stopped. Exiting.")

if __name__ == "__main__":
    main()
