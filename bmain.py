from flask import Flask, request, jsonify
import requests
from bs4 import BeautifulSoup
from collections import Counter
import re
import xml.etree.ElementTree as ET
from datetime import datetime

app = Flask(__name__)

def safe_request(url):
    try:
        return requests.get(url, timeout=5, headers={'User-Agent': 'Mozilla/5.0'}).text
    except:
        return None

def parse_date_for_sort(date_str):
    if not date_str or date_str == 'N/A':
        return float('-inf')  # Push "N/A" to end
    try:
        # Try parsing as full date (e.g., "2023-03-15")
        dt = datetime.strptime(date_str, '%Y-%m-%d')
        return dt.timestamp()
    except:
        try:
            # Try parsing as month-year (e.g., "Mar 2023")
            dt = datetime.strptime(date_str, '%b %Y')
            return dt.timestamp()
        except:
            # Fallback to just year (e.g., "2023")
            parts = date_str.split(' ')
            if parts[-1].isdigit():
                return datetime(int(parts[-1]), 1, 1).timestamp()
            return float('-inf')

def scrape_arxiv(keyword, limit=10, offset=0):
    url = f"https://arxiv.org/search/?query={keyword}&searchtype=all&start={offset}"
    html = safe_request(url)
    if not html:
        return []
    soup = BeautifulSoup(html, 'html.parser')
    results = []
    for item in soup.select('li.arxiv-result')[offset:offset + limit]:
        title_elem = item.select_one('.title')
        link_elem = item.select_one('a[href^="/abs"]')
        link = 'https://arxiv.org' + link_elem.get('href') if link_elem else None
        if link:
            results.append({
                'title': title_elem.text.strip() if title_elem else 'N/A',
                'link': link,
                'date': item.select_one('.is-size-7').text.strip() if item.select_one('.is-size-7') else 'N/A',
                'author': item.select_one('.authors').text.strip() if item.select_one('.authors') else 'N/A',
                'source_link': 'https://arxiv.org'
            })
    return results

def scrape_pubmed(keyword, limit=10, offset=0):
    url = f"https://pubmed.ncbi.nlm.nih.gov/?term={keyword}&page={offset // limit + 1}"
    html = safe_request(url)
    if not html:
        return []
    soup = BeautifulSoup(html, 'html.parser')
    results = []
    for item in soup.select('article')[offset % limit:offset % limit + limit]:
        title_elem = item.select_one('.docsum-title')
        link = 'https://pubmed.ncbi.nlm.nih.gov' + title_elem.get('href') if title_elem and title_elem.get('href') else None
        if link:
            results.append({
                'title': title_elem.text.strip() if title_elem else 'N/A',
                'link': link,
                'date': item.select_one('.docsum-journal-citation').text.split('.')[1].strip() if item.select_one('.docsum-journal-citation') else 'N/A',
                'author': item.select_one('.docsum-authors').text.strip() if item.select_one('.docsum-authors') else 'N/A',
                'source_link': 'https://pubmed.ncbi.nlm.nih.gov'
            })
    return results

def scrape_core(keyword, limit=10, offset=0):
    url = f"https://core.ac.uk/search?q={keyword}&page={offset // limit + 1}"
    html = safe_request(url)
    if not html:
        return []
    soup = BeautifulSoup(html, 'html.parser')
    results = []
    for item in soup.select('.search-item')[offset % limit:offset % limit + limit]:
        title_elem = item.select_one('h3 a')
        link = title_elem.get('href') if title_elem else None
        if link and link.startswith('http'):
            results.append({
                'title': title_elem.text.strip() if title_elem else 'N/A',
                'link': link,
                'date': item.select_one('.search-item-date').text.strip() if item.select_one('.search-item-date') else 'N/A',
                'author': 'N/A',
                'source_link': 'https://core.ac.uk'
            })
    return results

def fetch_semantic_scholar(keyword, limit=10, offset=0):
    url = f"https://api.semanticscholar.org/graph/v1/paper/search?query={keyword}&limit={limit}&offset={offset}"
    try:
        resp = requests.get(url, timeout=5).json()
        results = []
        for p in resp.get('data', []):
            link = p.get('url')
            if link and link.startswith('http'):
                results.append({
                    'title': p['title'],
                    'link': link,
                    'date': str(p['year']),
                    'author': ', '.join(a['name'] for a in p['authors']),
                    'source_link': 'https://www.semanticscholar.org'
                })
        return results
    except:
        return []

def fetch_dblp(keyword, limit=10, offset=0):
    url = f"https://dblp.org/search/publ/api?q={keyword}&format=xml&h={limit}&first={offset}"
    html = safe_request(url)
    if not html:
        return []
    try:
        root = ET.fromstring(html)
        results = []
        for h in root.findall('.//hit'):
            link = h.findtext('ee')
            if link and link.startswith('http'):
                results.append({
                    'title': h.findtext('title') or 'N/A',
                    'link': link,
                    'date': h.findtext('year') or 'N/A',
                    'author': h.findtext('author') or 'N/A',
                    'source_link': 'https://dblp.org'
                })
        return results
    except:
        return []

def scrape_google_scholar(keyword, limit=10, offset=0):
    url = f"https://scholar.google.com/scholar?q={keyword}&start={offset}"
    html = safe_request(url)
    if not html:
        return []
    soup = BeautifulSoup(html, 'html.parser')
    results = []
    for item in soup.select('.gs_rt')[0:limit]:
        title_elem = item.select_one('a')
        link = title_elem.get('href') if title_elem and title_elem.get('href').startswith('http') else None
        if link:
            results.append({
                'title': title_elem.text.strip() if title_elem else 'N/A',
                'link': link,
                'date': item.select_one('.gs_a').text.split(' - ')[0].strip() if item.select_one('.gs_a') else 'N/A',
                'author': item.select_one('.gs_a').text.split(' - ')[1].strip() if item.select_one('.gs_a') else 'N/A',
                'source_link': 'https://scholar.google.com'
            })
    return results

def scrape_ssrn(keyword, limit=10, offset=0):
    url = f"https://www.ssrn.com/index.cfm/en/search-results/?form_name=BasicSearch&search_term={keyword}&start={offset}"
    html = safe_request(url)
    if not html:
        return []
    soup = BeautifulSoup(html, 'html.parser')
    results = []
    for item in soup.select('.result-row')[0:limit]:
        title_elem = item.select_one('.title a')
        link = 'https://www.ssrn.com' + title_elem.get('href') if title_elem and title_elem.get('href') else None
        if link:
            results.append({
                'title': title_elem.text.strip() if title_elem else 'N/A',
                'link': link,
                'date': item.select_one('.date').text.strip() if item.select_one('.date') else 'N/A',
                'author': item.select_one('.authors').text.strip() if item.select_one('.authors') else 'N/A',
                'source_link': 'https://www.ssrn.com'
            })
    return results

def scrape_researchgate(keyword, limit=10, offset=0):
    url = f"https://www.researchgate.net/search/publication?q={keyword}&start={offset}"
    html = safe_request(url)
    if not html:
        return []
    soup = BeautifulSoup(html, 'html.parser')
    results = []
    for item in soup.select('.nova-legacy-e-link')[0:limit]:
        title_elem = item
        link = title_elem.get('href') if title_elem and title_elem.get('href').startswith('http') else None
        if link:
            results.append({
                'title': title_elem.text.strip() if title_elem else 'N/A',
                'link': link,
                'date': 'N/A',
                'author': 'N/A',
                'source_link': 'https://www.researchgate.net'
            })
    return results

@app.route('/trends')
def get_trends():
    keyword = request.args.get('keyword', 'javascript')
    limit = int(request.args.get('limit', 10))
    offset = int(request.args.get('offset', 0))
    try:
        results = (scrape_arxiv(keyword, limit, offset) + scrape_pubmed(keyword, limit, offset) + 
                   scrape_core(keyword, limit, offset) + fetch_semantic_scholar(keyword, limit, offset) + 
                   fetch_dblp(keyword, limit, offset) + scrape_google_scholar(keyword, limit, offset) + 
                   scrape_ssrn(keyword, limit, offset) + scrape_researchgate(keyword, limit, offset))
        # Sort by date, newest first, "N/A" last
        results.sort(key=lambda x: parse_date_for_sort(x['date']), reverse=True)
        words = re.findall(r'\w+', ' '.join(r['title'].lower() for r in results))
        stopwords = {'the', 'and', 'of', 'to'}
        terms = Counter(w for w in words if w not in stopwords).most_common(20)
        return jsonify({'results': results, 'terms': dict(terms)})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)