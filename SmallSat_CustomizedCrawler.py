# -*- coding: utf-8 -*-

import os
import re
import time
import logging
import requests
from bs4 import BeautifulSoup
from tqdm import tqdm

def setup_logging(log_level=logging.INFO):
    logging.basicConfig(
        level=log_level,
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


def extract_paper_links_with_dates(soup, year):
    """Extracts all paper page links for the given year, mapping each to its date."""
    schedule_table = soup.find('table', class_='vcalendar')
    if not schedule_table:
        logging.error('No table with class vcalendar found!')
        # Print all tables for debugging
        for idx, t in enumerate(soup.find_all('table')):
            logging.info(f'Table {idx} HTML: {str(t)[:100]}')
        return {}
    paper_date_map = {}
    current_date = None
    # The logic below persists the last seen date (from a 'day' row)
    # and assigns it to all subsequent paper links (from 'vevent' rows)
    skipped_links = []
    for idx, row in enumerate(schedule_table.find_all('tr')):
        row_classes = row.get('class', [])
        logging.info(f"Row {idx} classes: {row_classes}, HTML: {str(row)[:100]}")
        # Use substring matching for robustness
        if any('day' in c for c in row_classes):
            date_text = row.get_text(strip=True)
            import datetime
            try:
                import re
                date_parts = date_text.split(', ')
                if len(date_parts) == 2:
                    # Use regex to extract month and day robustly
                    match = re.search(r'(\w+)\s+(\d+)', date_parts[1])
                    if match:
                        month = match.group(1)
                        day = int(match.group(2))
                        month_num = datetime.datetime.strptime(month, '%B').month
                        current_date = f"{year}{month_num:02d}{day:02d}"
                        logging.info(f"Set current_date: {current_date} for day row: {date_text}")
                    else:
                        logging.warning(f"Regex failed to parse month/day from: {date_parts[1]}")
                else:
                    logging.warning(f"Could not parse date from day row: {date_text}")
            except Exception as e:
                logging.warning(f"Exception parsing date from day row: {date_text}, error: {e}")
        elif any('vevent' in c for c in row_classes):
            link_tag = row.find('a', href=re.compile(rf'/smallsat/{year}/all{year}/\d+'))
            if link_tag:
                paper_link = link_tag.get('href')
                if current_date:
                    paper_date_map[paper_link] = current_date
                    logging.info(f"Assigned date {current_date} to paper link {paper_link}")
                else:
                    skipped_links.append(paper_link)
                    logging.info(f"Skipping paper link {paper_link} because no current_date has been set yet.")
    logging.info(f"Total papers mapped to dates: {len(paper_date_map)}")
    if skipped_links:
        logging.warning(f"Skipped {len(skipped_links)} paper links due to missing date: {skipped_links}")
    return paper_date_map

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



def main(year=2025, test_flag=False, log_level=logging.INFO, download_flag=True):
    """
    Downloads SmallSat papers and metadata for a given year.
    Args:
        year (int): Conference year to scrape.
        test_flag (bool): If True, only download/process three papers.
        log_level: Python logging level.
        download_flag (bool): If True, download PDF files; if False, skip PDF download.
    """
    setup_logging(log_level)
    base_url = f"https://digitalcommons.usu.edu/smallsat/{year}/all{year}/"
    logging.info(f"Fetching main page: {base_url}")
    soup = fetch_soup(base_url)
    if not soup:
        return
    # Use a local output folder within the working directory
    output_dir = os.path.join(os.getcwd(), str(year))
    os.makedirs(output_dir, exist_ok=True)
    if log_level == logging.DEBUG:
        with open(os.path.join(output_dir, "soup_debug.html"), "w", encoding="utf-8") as f:
            f.write(str(soup))
    paper_date_map = extract_paper_links_with_dates(soup, year)
    if not paper_date_map:
        logging.warning("No paper links found.")
        return
    # Prepare to collect data for Excel
    import pandas as pd
    excel_path = os.path.join(output_dir, f"papers_{year}.xlsx")
    papers_info = []
    processed_links = set()
    # If Excel file exists, read it and collect processed links
    if os.path.exists(excel_path):
        try:
            df_existing = pd.read_excel(excel_path)
            if 'Link' in df_existing.columns:
                processed_links = set(df_existing['Link'].astype(str))
                papers_info = df_existing.to_dict(orient='records')
            logging.info(f"Loaded {len(processed_links)} already processed papers from Excel.")
        except Exception as e:
            logging.error(f"Failed to read existing Excel file: {e}")
    count = 0
    paper_iter = paper_date_map.items()
    if log_level == logging.WARNING:
        paper_iter = tqdm(paper_iter, desc="Downloading papers", total=len(paper_date_map))
    for rel_link, paper_date in paper_iter:
        if rel_link in processed_links:
            logging.info(f"Skipping already processed paper: {rel_link}")
            continue
        full_link = f"https://digitalcommons.usu.edu{rel_link}" if rel_link.startswith('/') else rel_link
        logging.info(f"Fetching paper page: {full_link}")
        soup_temp = fetch_soup(full_link)
        if not soup_temp:
            continue
        article_title = get_article_title(soup_temp)
        # Extract abstract
        abstract = ""
        abstract_tag = soup_temp.find('div', id='abstract')
        if abstract_tag:
            abstract_p = abstract_tag.find('p')
            from bs4.element import Tag
            if isinstance(abstract_p, Tag):
                abstract = abstract_p.get_text(strip=True)
            elif isinstance(abstract_tag, Tag):
                abstract = abstract_tag.get_text(strip=True)
        else:
            # Fallback: try meta tag
            meta_abstract = soup_temp.find('meta', attrs={'name': 'description'})
            from bs4.element import Tag
            if isinstance(meta_abstract, Tag):
                content = meta_abstract.get('content', None)
                if content:
                    abstract = content
        papers_info.append({
            'Title': article_title,
            'Date': paper_date,
            'Abstract': abstract,
            'Link': rel_link
        })
        processed_links.add(rel_link)
        if log_level == logging.DEBUG:
            debug_html_path = os.path.join(output_dir, f"soup_debug_{article_title}.html")
            with open(debug_html_path, "w", encoding="utf-8") as f_debug:
                f_debug.write(str(soup_temp))
        pdf_url = find_pdf_link(soup_temp)
        if not pdf_url:
            logging.warning(f"PDF link not found for {article_title}")
            continue
        pdf_filename = f"{paper_date}_{article_title}.pdf"
        pdf_path = os.path.join(output_dir, pdf_filename)
        if download_flag:
            if not os.path.exists(pdf_path):
                download_pdf(pdf_url, pdf_path)
            else:
                logging.info(f"PDF already exists, skipping download: {pdf_filename}")
        count += 1
        # Write Excel after each paper
        try:
            df = pd.DataFrame(papers_info)
            df.to_excel(excel_path, index=False)
            logging.info(f"Updated paper info to Excel: {excel_path}")
        except Exception as e:
            logging.error(f"Failed to update Excel file: {e}")
        if test_flag and count >= 3:
            logging.info("Test flag set: downloaded three papers, exiting early.")
            break

    # Excel writing now happens after each paper download

if __name__ == "__main__":
    # Set test_flag to True to only download three papers and exit
    # Set log_level to logging.DEBUG to enable debug output and save HTML files
    # Set download_flag to False to skip PDF downloads
    main(year=2025, test_flag=False, log_level=logging.WARNING, download_flag=True)