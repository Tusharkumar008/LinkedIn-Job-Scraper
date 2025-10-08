from flask import Flask, render_template, request, jsonify, send_file
from flask_cors import CORS
import threading
import pandas as pd
from datetime import datetime
import os
from scraper import LinkedInScraper

app = Flask(__name__)
CORS(app)

# Global variables to track scraping status
scraper = None
scraping_status = {
    'is_running': False,
    'progress': 0,
    'message': '',
    'results': [],
    'error': False
}

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/start_scraping', methods=['POST'])
def start_scraping():
    global scraper, scraping_status
    
    if scraping_status['is_running']:
        return jsonify({'error': 'Scraping is already in progress'}), 400
    
    data = request.json
    company_name = data.get('companyName', '').strip()
    days_filter = data.get('daysFilter', 7)
    scroll_count = data.get('scrollCount', 50)
    
    if not company_name:
        return jsonify({'error': 'Company name is required'}), 400
    
    try:
        days_filter = int(days_filter)
        scroll_count = int(scroll_count)
        
        if days_filter <= 0 or scroll_count <= 0:
            return jsonify({'error': 'Days and scroll count must be positive'}), 400
    except ValueError:
        return jsonify({'error': 'Invalid number format'}), 400
    
    scraping_status = {
        'is_running': True,
        'progress': 0,
        'message': 'Initializing scraper...',
        'results': [],
        'error': False
    }
    
    def run_scraper():
        global scraper, scraping_status
        try:
            scraper = LinkedInScraper(company_name, days_filter, scroll_count)
            results = scraper.run()
            
            scraping_status['results'] = results
            scraping_status['progress'] = 100
            scraping_status['message'] = f'Scraping complete! Found {len(results)} posts'
            scraping_status['is_running'] = False
            
        except Exception as e:
            scraping_status['error'] = True
            scraping_status['message'] = f'Error: {str(e)}'
            scraping_status['is_running'] = False
            scraping_status['progress'] = 0
    
    thread = threading.Thread(target=run_scraper)
    thread.daemon = True
    thread.start()
    
    return jsonify({'success': True, 'message': 'Scraping started'})

@app.route('/scraping_status', methods=['GET'])
def get_status():
    global scraping_status
    return jsonify(scraping_status)

@app.route('/export_results', methods=['GET'])
def export_results():
    global scraping_status
    
    if not scraping_status['results']:
        return jsonify({'error': 'No results to export'}), 400
    
    try:
        df = pd.DataFrame(scraping_status['results'])
        
        filename = f"linkedin_scrape_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        filepath = os.path.join('exports', filename)
        
        os.makedirs('exports', exist_ok=True)
        
        df.to_excel(filepath, index=False)
        
        return send_file(filepath, as_attachment=True, download_name=filename)
        
    except Exception as e:
        return jsonify({'error': f'Export failed: {str(e)}'}), 500

if __name__ == '__main__':
    app.run(debug=True, port=5000)