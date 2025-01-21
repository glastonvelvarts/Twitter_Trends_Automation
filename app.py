from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from datetime import datetime
import pymongo
import uuid
import requests
from flask import Flask, jsonify, render_template_string
import os
from dotenv import load_dotenv
import random
from bs4 import BeautifulSoup

# Load environment variables
load_dotenv()

# Configuration
TWITTER_USERNAME = os.getenv('TWITTER_USERNAME')
TWITTER_PASSWORD = os.getenv('TWITTER_PASSWORD')
MONGO_URI = os.getenv('MONGO_URI')

# Initialize Flask app
app = Flask(__name__)

# MongoDB setup
client = pymongo.MongoClient(MONGO_URI)
db = client['twitter_trends']
collection = db['trending_topics']

def get_free_proxies():
    """Get a list of free proxies from free-proxy-list.net"""
    url = "https://free-proxy-list.net/"
    response = requests.get(url)
    soup = BeautifulSoup(response.text, 'html.parser')
    
    proxies = []
    # Get the table rows from the proxy list
    proxy_table = soup.find('table')
    for row in proxy_table.tbody.find_all('tr'):
        columns = row.find_all('td')
        if columns[6].text.strip() == 'yes':  # Check if HTTPS
            ip = columns[0].text.strip()
            port = columns[1].text.strip()
            proxies.append(f'{ip}:{port}')
    
    return proxies

def get_working_proxy():
    """Test proxies and return a working one"""
    proxies = get_free_proxies()
    for proxy in proxies:
        try:
            response = requests.get(
                'https://httpbin.org/ip',
                proxies={'https': f'https://{proxy}'},
                timeout=5
            )
            if response.status_code == 200:
                return proxy
        except:
            continue
    return None

def scrape_twitter_trends():
    """Scrape trending topics from Twitter using Selenium"""
    # Setup Chrome options
    chrome_options = Options()
    
    # Get and configure proxy
    proxy = get_working_proxy()
    if proxy:
        chrome_options.add_argument(f'--proxy-server=https://{proxy}')
    
    # Add additional options to help avoid detection
    chrome_options.add_argument('--disable-blink-features=AutomationControlled')
    chrome_options.add_argument('--disable-extensions')
    chrome_options.add_experimental_option('useAutomationExtension', False)
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    
    driver = webdriver.Chrome(options=chrome_options)
    
    try:
        # Login to Twitter
        driver.get("https://twitter.com/login")
        wait = WebDriverWait(driver, 20)
        
        # Login process
        username_input = wait.until(EC.presence_of_element_located((By.NAME, "text")))
        username_input.send_keys(TWITTER_USERNAME)
        driver.find_element(By.XPATH, "//span[text()='Next']").click()
        
        password_input = wait.until(EC.presence_of_element_located((By.NAME, "password")))
        password_input.send_keys(TWITTER_PASSWORD)
        driver.find_element(By.XPATH, "//span[text()='Log in']").click()
        
        # Wait for trends to load
        trends_section = wait.until(EC.presence_of_element_located((By.XPATH, "//div[text()=\"What's happening\"]")))
        trends = driver.find_elements(By.XPATH, "//div[contains(@data-testid, 'trend')]")[:5]
        
        # Extract trend names
        trend_names = [trend.text.split('\n')[0] for trend in trends]
        
        # Get current IP (will show the proxy IP if using one)
        ip_address = requests.get('https://api.ipify.org').text
        
        # Prepare data for MongoDB
        current_time = datetime.now()
        record = {
            "_id": str(uuid.uuid4()),
            "nameoftrend1": trend_names[0],
            "nameoftrend2": trend_names[1],
            "nameoftrend3": trend_names[2],
            "nameoftrend4": trend_names[3],
            "nameoftrend5": trend_names[4],
            "datetime": current_time,
            "ip_address": ip_address
        }
        
        # Save to MongoDB
        collection.insert_one(record)
        
        return record
        
    finally:
        driver.quit()

# HTML template (same as before)
HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Twitter Trends Scraper</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 40px; }
        .button { padding: 10px 20px; background: #1DA1F2; color: white; 
                  text-decoration: none; border-radius: 5px; }
        .results { margin-top: 20px; }
    </style>
</head>
<body>
    <h1>Twitter Trends Scraper</h1>
    
    {% if not results %}
    <a href="/scrape" class="button">Click here to run the script</a>
    {% else %}
    <div class="results">
        <h2>These are the most happening topics as on {{ results.datetime }}</h2>
        <ul>
            <li>{{ results.nameoftrend1 }}</li>
            <li>{{ results.nameoftrend2 }}</li>
            <li>{{ results.nameoftrend3 }}</li>
            <li>{{ results.nameoftrend4 }}</li>
            <li>{{ results.nameoftrend5 }}</li>
        </ul>
        <p>The IP address used for this query was {{ results.ip_address }}</p>
        
        <h3>JSON extract from MongoDB:</h3>
        <pre>{{ results | tojson(indent=2) }}</pre>
        
        <a href="/scrape" class="button">Click here to run the query again</a>
    </div>
    {% endif %}
</body>
</html>
"""

@app.route('/')
def home():
    return render_template_string(HTML_TEMPLATE)

@app.route('/scrape')
def scrape():
    results = scrape_twitter_trends()
    return render_template_string(HTML_TEMPLATE, results=results)

if __name__ == '__main__':
    app.run(debug=True)