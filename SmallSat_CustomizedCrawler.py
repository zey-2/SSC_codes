# -*- coding: utf-8 -*-

import os
import re
import time
import logging
import requests
from bs4 import BeautifulSoup

def setup_logging():
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )

def fetch_soup(url):
    """Fetches and parses HTML content from a URL."""
    try:
        response = requests.get(url)
        response.raise_for_status()
        return BeautifulSoup(response.text, features="lxml")
    except Exception as e:
        logging.error(f"Failed to fetch {url}: {e}")
        return None

def extract_paper_links(soup, year):
    """Extracts all paper page links for the given year."""
    pattern = rf'/smallsat/{year}/all{year}/\d+'
    return [link.get('href') for link in soup.find_all('a', href=re.compile(pattern))]

def get_article_title(soup):
    """Extracts the article title from the page's <title> tag."""
    if soup.title and soup.title.string:
        title_parts = soup.title.string.split(':')
        return title_parts[1].strip() if len(title_parts) > 1 else title_parts[0].strip()
    return "UnknownTitle"

def find_pdf_link(soup):
    """Finds the direct PDF download link in the soup."""
    pdf_link = soup.find('a', href=re.compile(r'https://digitalcommons\.usu\.edu/cgi/viewcontent\.cgi\?article=\d+&context=smallsat'))
    if pdf_link:
        url = pdf_link.get('href')
        if isinstance(url, str) and url:
            return url
    return None

def download_pdf(url, output_path, max_retries=5):
    """Downloads a PDF file with retry logic."""
    for attempt in range(1, max_retries + 1):
        try:
            response = requests.get(url, stream=True)
            response.raise_for_status()
            with open(output_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            logging.info(f"Downloaded: {output_path}")
            return True
        except Exception as e:
            logging.warning(f"Attempt {attempt} failed for {url}: {e}")
            time.sleep(0.5)
    logging.error(f"Failed to download after {max_retries} attempts: {url}")
    return False


def main(year=2025, output_dir='D:/SSC2025/', debug_flag=True):
    setup_logging()
    base_url = f"https://digitalcommons.usu.edu/smallsat/{year}/all{year}/"
    logging.info(f"Fetching main page: {base_url}")
    soup = fetch_soup(base_url)
    if not soup:
        return
    if debug_flag:
        with open("soup_debug.html", "w", encoding="utf-8") as f:
            f.write(str(soup))
    paper_links = extract_paper_links(soup, year)
    if not paper_links:
        logging.warning("No paper links found.")
        return
    os.makedirs(output_dir, exist_ok=True)
    for rel_link in paper_links:
        full_link = f"https://digitalcommons.usu.edu{rel_link}" if rel_link.startswith('/') else rel_link
        logging.info(f"Fetching paper page: {full_link}")
        soup_temp = fetch_soup(full_link)
        if not soup_temp:
            continue
        article_title = get_article_title(soup_temp)
        if debug_flag:
            debug_html_path = os.path.join(output_dir, f"soup_debug_{article_title}.html")
            with open(debug_html_path, "w", encoding="utf-8") as f_debug:
                f_debug.write(str(soup_temp))
        pdf_url = find_pdf_link(soup_temp)
        if not pdf_url:
            logging.warning(f"PDF link not found for {article_title}")
            continue
        pdf_path = os.path.join(output_dir, f"{article_title}.pdf")
        download_pdf(pdf_url, pdf_path)

if __name__ == "__main__":
    # Set debug_flag to True to save HTML files, False to skip
    main(year=2025, output_dir='D:/SSC2025/', debug_flag=True)