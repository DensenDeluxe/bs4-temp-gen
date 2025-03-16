#!/usr/bin/env python3
import os
import sys
import time
import pickle
import logging
import difflib
import random
import re
import argparse
import threading
import concurrent.futures
from queue import Queue
import requests
from tqdm import tqdm
from bs4 import BeautifulSoup
from urllib.parse import urlparse, urljoin
from colorama import init, Fore, Style
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# For headless browser usage
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC

# Initialize Colorama for colored console output
init(autoreset=True)

# Standard configuration values
DEFAULT_PROJECTS_DIR = "projects"
DEFAULT_KEYWORDS_FILE = "bs4-search-items.txt"

# Global lock for shared Selenium driver
selenium_lock = threading.Lock()

def print_matrix_header():
    ascii_art = """
888                   d8888         888                                                                     
888                  d8P888         888                                                                     
888                 d8P 888         888                                                                     
88888b.  .d8888b   d8P  888         888888 .d88b.  88888b.d88b.  88888b.          .d88b.   .d88b.  88888b.  
888 "88b 88K      d88   888         888   d8P  Y8b 888 "888 "88b 888 "88b        d88P"88b d8P  Y8b 888 "88b 
888  888 "Y8888b. 8888888888 888888 888   88888888 888  888  888 888  888 888888 888  888 88888888 888  888 
888 d88P      X88       888         Y88b. Y8b.     888  888  888 888 d88P        Y88b 888 Y8b.     888  888 
88888P"   88888P'       888          "Y888 "Y8888  888  888  888 88888P"          "Y88888  "Y8888  888  888 
                                                                 888                  888                   
                                                                 888             Y8b d88P                   
                                                                 888              "Y88P"                    
"""
    # Print the ASCII art once at the very top. It remains fixed.
    print(ascii_art)
    return ascii_art

def load_keywords(filename):
    if os.path.exists(filename):
        with open(filename, "r", encoding="utf-8") as f:
            keywords = [line.strip() for line in f if line.strip()]
        logging.debug(f"[KEYWORDS] Loaded {len(keywords)} keywords from {filename}.")
        return keywords
    else:
        logging.error(f"[KEYWORDS] Keywords file {filename} not found.")
        return []

def extract_domain(url):
    parsed = urlparse(url)
    domain = parsed.netloc
    if domain.startswith("www."):
        domain = domain[4:]
    return domain

def check_project_existence(url, project_dir):
    domain = extract_domain(url)
    project_path = os.path.join(project_dir, domain)
    exists = os.path.exists(project_path)
    logging.debug(f"[PROJECT] Checking project for domain '{domain}': {'found' if exists else 'not found'}.")
    return exists, project_path

def create_project_structure(project_path):
    os.makedirs(project_path, exist_ok=True)
    mhtml_path = os.path.join(project_path, "downloaded_mhtml")
    os.makedirs(mhtml_path, exist_ok=True)
    logging.debug(f"[PROJECT] Created project structure at {project_path}.")
    return mhtml_path

def prioritize_urls(url_list):
    """[CRAWLING] Prioritizes URLs based on depth to favor shallower pages."""
    return sorted(url_list, key=lambda url: (url.count("/"), url))

def is_cloudflare_error_page(content):
    """[HTTP] Checks if content indicates a Cloudflare error."""
    if not content:
        return True
    markers = ["cf-error-details", "Email Protection", "Cloudflare Ray ID:"]
    return any(marker in content for marker in markers)

def prepare_for_comparison(html_content):
    """[PARSING] Normalize HTML by removing variable content."""
    soup = BeautifulSoup(html_content, "lxml")
    for tag in soup(["script", "style"]):
        tag.decompose()
    for tag in soup.find_all(True):
        attrs = list(tag.attrs.keys())
        for attr in attrs:
            if attr == "id" or attr == "style" or attr.startswith("on") or attr.startswith("data-"):
                del tag.attrs[attr]
    normalized = re.sub(r"\d+", "0", soup.prettify())
    logging.debug("[PARSING] Prepared HTML for comparison.")
    return normalized

def get_page_content(url, session, headers, selenium_only=False, shared_driver=None, no_delay=False,
                     page_timeout=10, selenium_timeout=15, retry_count=3):
    logging.debug(f"[HTTP] Requesting URL: {url}")
    if selenium_only:
        return get_content_with_selenium(url, headers, shared_driver, selenium_timeout)
    for attempt in range(retry_count):
        try:
            response = session.get(url, headers=headers, timeout=page_timeout)
            content = response.text
            logging.debug(f"[HTTP] Received response for {url} (attempt {attempt+1}).")
            if is_cloudflare_error_page(content):
                logging.debug(f"[HTTP] Cloudflare detected for {url}. Switching to Selenium.")
                return get_content_with_selenium(url, headers, shared_driver, selenium_timeout)
            return content
        except Exception as e:
            logging.warning(f"[HTTP] Attempt {attempt+1} for {url} failed: {e}")
            if not no_delay:
                time.sleep(2)
    logging.debug(f"[HTTP] Falling back to Selenium for {url} after {retry_count} failed attempts.")
    return get_content_with_selenium(url, headers, shared_driver, selenium_timeout)

def get_content_with_selenium(url, headers, shared_driver=None, selenium_timeout=15):
    logging.debug(f"[SELENIUM] Requesting URL via Selenium: {url}")
    if shared_driver:
        try:
            with selenium_lock:
                shared_driver.get(url)
                WebDriverWait(shared_driver, selenium_timeout).until(
                    lambda d: d.execute_script('return document.readyState') == 'complete'
                )
                content = shared_driver.page_source
            logging.debug(f"[SELENIUM] Received content for {url} via shared driver.")
            return content
        except Exception as e:
            logging.error(f"[SELENIUM] Error with shared driver for {url}: {e}")
            return ""
    else:
        try:
            options = Options()
            options.add_argument("--headless")
            options.add_argument("--disable-gpu")
            options.add_argument(f'user-agent={headers["User-Agent"]}')
            driver = webdriver.Chrome(options=options)
            driver.set_page_load_timeout(selenium_timeout)
            driver.get(url)
            WebDriverWait(driver, selenium_timeout).until(
                lambda d: d.execute_script('return document.readyState') == 'complete'
            )
            content = driver.page_source
            driver.quit()
            logging.debug(f"[SELENIUM] Received content for {url} via temporary driver.")
            return content
        except Exception as e:
            logging.error(f"[SELENIUM] Error with Selenium for {url}: {e}")
            return ""

def crawl_website(url, download_dir, strategy="bfs", sort_links=True, max_pages=-1, max_depth=-1, no_delay=False,
                  selenium_only=False, max_workers=5, page_timeout=10, selenium_timeout=15, retry_count=3,
                  keywords=None, use_keywords=False):
    domain = extract_domain(url)
    logging.info(f"[CRAWLING] Starting crawl for domain '{domain}'.")
    visited = set()
    to_visit = [(url, 0)]
    downloaded_files = []
    session = requests.Session()
    retry_strategy = Retry(
        total=retry_count,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["HEAD", "GET", "OPTIONS"],
        backoff_factor=1
    )
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    headers = {"User-Agent": "Mozilla/5.0 (compatible; BS4TemplateGenerator/1.0)"}
    shared_driver = None
    if selenium_only:
        options = Options()
        options.add_argument("--headless")
        options.add_argument("--disable-gpu")
        options.add_argument(f'user-agent={headers["User-Agent"]}')
        try:
            shared_driver = webdriver.Chrome(options=options)
            logging.info("[SELENIUM] Shared Selenium driver initialized.")
        except Exception as e:
            logging.error(f"[SELENIUM] Error initializing shared driver: {e}")
            selenium_only = False

    pbar = tqdm(desc=f"{Fore.GREEN}Downloading pages{Style.RESET_ALL}", ncols=80)
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        while to_visit and (max_pages == -1 or len(downloaded_files) < max_pages):
            batch = []
            while to_visit and len(batch) < max_workers:
                url_item, depth = to_visit.pop(0) if strategy == "bfs" else to_visit.pop()
                if url_item in visited:
                    continue
                batch.append((url_item, depth))
                visited.add(url_item)
            if not batch:
                continue
            futures = {
                executor.submit(
                    get_page_content,
                    url_item, session, headers, selenium_only, shared_driver, no_delay, page_timeout, selenium_timeout, retry_count
                ): (url_item, depth) for (url_item, depth) in batch
            }
            for future in concurrent.futures.as_completed(futures):
                current_url, current_depth = futures[future]
                try:
                    content = future.result()
                except Exception as exc:
                    logging.error(f"[CRAWLING] Error processing {current_url}: {exc}")
                    continue
                if not no_delay:
                    time.sleep(random.uniform(1, 3))
                if content and not is_cloudflare_error_page(content):
                    if use_keywords and keywords:
                        if not any(kw.lower() in content.lower() for kw in keywords):
                            logging.debug(f"[CRAWLING] Skipping {current_url} due to keyword filter.")
                            continue
                    file_index = len(downloaded_files) + 1
                    filename = os.path.join(download_dir, f"page_{file_index}.mhtml")
                    try:
                        with open(filename, "w", encoding="utf-8") as f:
                            f.write(content)
                        logging.debug(f"[CRAWLING] Saved {current_url} as {filename}.")
                    except Exception as e:
                        logging.error(f"[CRAWLING] Error writing file {filename}: {e}")
                        continue
                    downloaded_files.append(filename)
                    pbar.update(1)
                    soup = BeautifulSoup(content, "lxml")
                    new_links = []
                    for link in soup.find_all("a", href=True):
                        href = link["href"]
                        absolute_url = urljoin(current_url, href)
                        if extract_domain(absolute_url) == domain and absolute_url not in visited:
                            new_links.append(absolute_url)
                    if sort_links:
                        new_links = prioritize_urls(new_links)
                    for link in new_links:
                        if max_depth == -1 or current_depth + 1 <= max_depth:
                            to_visit.append((link, current_depth + 1))
                    logging.debug(f"[CRAWLING] {len(new_links)} new links found at depth {current_depth+1}.")
                    if max_pages != -1 and len(downloaded_files) >= max_pages:
                        break
                else:
                    logging.info(f"[CRAWLING] Ignored {current_url} due to Cloudflare error or empty content.")
    pbar.close()
    if shared_driver:
        try:
            shared_driver.quit()
            logging.info("[SELENIUM] Shared Selenium driver terminated.")
        except Exception as e:
            logging.error(f"[SELENIUM] Error quitting shared driver: {e}")
    logging.info(f"[CRAWLING] Crawl complete. {len(downloaded_files)} pages downloaded.")
    return downloaded_files

def read_supported_files(directory):
    logging.info(f"[PARSING] Reading supported files from '{directory}'.")
    supported_exts = (".mhtml", ".html", ".htm")
    files = [os.path.join(directory, f) for f in os.listdir(directory) if f.lower().endswith(supported_exts)]
    documents = {}
    for file in tqdm(files, desc=f"{Fore.GREEN}Reading downloaded file formats...{Style.RESET_ALL}", ncols=80):
        try:
            with open(file, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
                normalized_html = prepare_for_comparison(content)
                html_lines = normalized_html.splitlines()
                documents[file] = html_lines
            logging.debug(f"[PARSING] File '{file}' processed ({len(html_lines)} lines).")
        except Exception as e:
            logging.error(f"[PARSING] Error reading '{file}': {e}")
    logging.info(f"[PARSING] {len(documents)} files successfully read.")
    return documents

def normalize_html_lines(lines):
    """[PARSING] Normalizes HTML lines by stripping whitespace and omitting empty lines."""
    return [line.strip() for line in lines if line.strip()]

def lcs(seq1, seq2):
    n, m = len(seq1), len(seq2)
    dp = [[0] * (m + 1) for _ in range(n + 1)]
    for i in range(n):
        for j in range(m):
            if seq1[i] == seq2[j]:
                dp[i+1][j+1] = dp[i][j] + 1
            else:
                dp[i+1][j+1] = max(dp[i+1][j], dp[i][j+1])
    i, j = n, m
    lcs_seq = []
    while i > 0 and j > 0:
        if seq1[i-1] == seq2[j-1]:
            lcs_seq.append(seq1[i-1])
            i -= 1
            j -= 1
        elif dp[i-1][j] >= dp[i][j-1]:
            i -= 1
        else:
            j -= 1
    return list(reversed(lcs_seq))

def compute_common_sequence(documents):
    logging.info("[COMMON] Computing common sequence from documents.")
    common_seq = None
    for filename, lines in documents.items():
        normalized = normalize_html_lines(lines)
        if common_seq is None:
            common_seq = normalized
            logging.debug(f"[COMMON] Started common sequence with '{filename}'.")
        else:
            common_seq = lcs(common_seq, normalized)
            logging.debug(f"[COMMON] Updated common sequence after '{filename}' to {len(common_seq)} lines.")
    logging.info(f"[COMMON] Common sequence computed with {len(common_seq)} lines.")
    return common_seq

def compute_variable_lines(doc_lines, common_seq):
    diff = difflib.ndiff(common_seq, doc_lines)
    variable_lines = [line[2:] for line in diff if line.startswith("+ ")]
    logging.debug(f"[COMMON] Computed {len(variable_lines)} variable lines.")
    return variable_lines

def aggregate_variable_lines(documents, common_seq):
    logging.info("[COMMON] Aggregating variable lines from documents.")
    variable_all = []
    for filename, lines in documents.items():
        var_lines = compute_variable_lines(lines, common_seq)
        logging.debug(f"[COMMON] {filename}: {len(var_lines)} variable lines found.")
        variable_all.extend(var_lines)
    seen = set()
    variable_ordered = []
    for line in variable_all:
        if line not in seen and line.strip():
            seen.add(line)
            variable_ordered.append(line)
    logging.info(f"[COMMON] Aggregated {len(variable_ordered)} unique variable lines.")
    return variable_ordered

def generate_bs4_template(common_seq, variable_lines):
    logging.info(f"[TEMPLATE] Generating BS4 template with {len(common_seq)} common and {len(variable_lines)} variable lines.")
    template = '''"""
Automatically generated BS4 template

=== Common (static) HTML structure from all supported files ===
'''
    for line in common_seq:
        template += line + "\n"
    template += '''
=== Variable sections (data that differ) ===
'''
    for line in variable_lines:
        safe_line = line.strip().replace('"""', '\"\"\"')
        if safe_line:
            template += "# " + safe_line + "\n"
    template += '''
=== Final extraction template ===

The function "extract_relevant_data" is a starting point for extracting
relevant data from HTML using BeautifulSoup. Customize as needed.
"""

from bs4 import BeautifulSoup

def extract_relevant_data(html_content):
    soup = BeautifulSoup(html_content, 'lxml')
    # Example: Extract an element by its class or tag
    # title = soup.find("h1", class_="product-title").get_text(strip=True)
    # price = soup.find("span", class_="price").get_text(strip=True)
    # Add further extractions as needed
    return soup.get_text(separator=" ", strip=True)

if __name__ == '__main__':
    with open("example.mhtml", "r", encoding="utf-8", errors="ignore") as f:
        html = f.read()
    data = extract_relevant_data(html)
    print(data)
'''
    return template

def load_cache():
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, "rb") as f:
                cache = pickle.load(f)
            logging.debug("[CACHE] Cache successfully loaded.")
            return cache
        except Exception as e:
            logging.error(f"[CACHE] Error loading cache: {e}")
    return {}

def save_cache(cache):
    try:
        with open(CACHE_FILE, "wb") as f:
            pickle.dump(cache, f)
        logging.debug("[CACHE] Cache successfully saved.")
    except Exception as e:
        logging.error(f"[CACHE] Error saving cache: {e}")

def files_have_changed(documents, cached_info):
    for filepath in documents.keys():
        mtime = os.path.getmtime(filepath)
        if filepath not in cached_info or cached_info[filepath] != mtime:
            logging.debug(f"[CACHE] File changed: {filepath}")
            return True
    return False

def update_cache_info(documents):
    cache_info = {}
    for filepath in documents.keys():
        cache_info[filepath] = os.path.getmtime(filepath)
    logging.debug("[CACHE] Cache info updated.")
    return cache_info

def configure_project_logging(project_path):
    """[LOG] Configures logging to store the log file within the project folder."""
    log_path = os.path.join(project_path, "log.txt")
    for handler in logging.root.handlers[:]:
        logging.root.removeHandler(handler)
    logging.basicConfig(
        filename=log_path,
        level=logging.DEBUG,
        format="%(asctime)s - %(levelname)s - %(message)s",
        filemode="a"
    )
    logging.debug("[LOG] Project logging configured.")

def main(args):
    start_time = time.time()
    # Print the fixed ASCII art at the top
    print_matrix_header()
    logging.info("[MAIN] Starting BS4 Template Generator...")
    
    project_url = input("Please enter the project URL: ").strip()
    logging.debug(f"[MAIN] Project URL entered: {project_url}")
    exists, project_path = check_project_existence(project_url, args.project_dir)
    
    download_dir = os.path.join(project_path, "downloaded_mhtml")
    if not exists:
        project_path = os.path.join(args.project_dir, extract_domain(project_url))
        create_project_structure(project_path)
        downloaded_files = crawl_website(
            project_url,
            download_dir,
            strategy=args.strategy,
            sort_links=True,
            max_pages=args.max_pages,
            max_depth=args.max_depth,
            no_delay=args.no_delay,
            selenium_only=args.selenium_only,
            max_workers=args.max_workers,
            page_timeout=args.page_timeout,
            selenium_timeout=args.selenium_timeout,
            retry_count=args.retry_count,
            keywords=load_keywords(args.keyword_file) if args.use_keywords else None,
            use_keywords=args.use_keywords
        )
        if not downloaded_files:
            logging.error("[MAIN] No pages downloaded. Exiting.")
            sys.exit(1)
    else:
        downloaded_files = [os.path.join(download_dir, f) for f in os.listdir(download_dir)]
        logging.info(f"[MAIN] Project already exists; {len(downloaded_files)} pages found in {download_dir}.")
    
    configure_project_logging(project_path)
    global CACHE_FILE, OUTPUT_FILE
    CACHE_FILE = os.path.join(project_path, "cache.pkl")
    OUTPUT_FILE = args.output if args.output else os.path.join(project_path, "bs4code.txt")
    
    if not os.path.exists(download_dir):
        logging.error("[MAIN] Download directory not found in project. Exiting.")
        sys.exit(1)
    
    documents = read_supported_files(download_dir)
    if not documents:
        logging.error("[PARSING] No supported files found. Exiting.")
        sys.exit(1)
    
    cache = load_cache() if not args.no_cache else {}
    cached_info = cache.get("file_info", {})
    cached_common = cache.get("common_seq", None)
    cached_variables = cache.get("variable_lines", None)
    
    if cached_common is not None and not files_have_changed(documents, cached_info):
        logging.debug("[CACHE] No changes detected; using cached data.")
        common_seq = cached_common
        variable_lines = cached_variables
    else:
        logging.debug("[CACHE] Changes detected or no cache available; recalculating common sequence.")
        common_seq = compute_common_sequence(documents)
        if common_seq is None:
            logging.error("[COMMON] Common sequence is None. Exiting.")
            sys.exit(1)
        logging.debug(f"[COMMON] Common sequence has {len(common_seq)} lines.")
        variable_lines = aggregate_variable_lines(documents, common_seq)
        cache["file_info"] = update_cache_info(documents)
        cache["common_seq"] = common_seq
        cache["variable_lines"] = variable_lines
        if not args.no_cache:
            save_cache(cache)
    
    logging.debug("[TEMPLATE] Generating BS4 code template.")
    bs4_template = generate_bs4_template(common_seq, variable_lines)
    try:
        with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
            f.write(bs4_template)
        logging.info(f"[TEMPLATE] BS4 template written to '{OUTPUT_FILE}'.")
    except Exception as e:
        logging.error(f"[TEMPLATE] Error writing to '{OUTPUT_FILE}': {e}")
    
    elapsed = time.time() - start_time
    logging.info(f"[MAIN] Total time: {elapsed:.2f} seconds")
    print(f"Total time: {elapsed:.2f} seconds")

if __name__ == "__main__":
    # Initial console logging (will later be adjusted by --verbose)
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    parser = argparse.ArgumentParser(
        description="BS4 Template Generator with advanced crawling and extraction features"
    )
    parser.add_argument("--verbose", choices=["off", "v", "vv", "vvv", "infinite"], default="vvv",
                        help="Console verbosity level: off, v, vv, vvv, infinite")
    parser.add_argument("--strategy", choices=["bfs", "dfs"], default="bfs",
                        help="Crawling strategy: breadth-first (bfs) or depth-first (dfs)")
    parser.add_argument("--max-pages", type=int, default=100,
                        help="Maximum number of pages to crawl (-1 for infinite)")
    parser.add_argument("--max-depth", type=int, default=-1,
                        help="Maximum crawling depth (-1 for infinite)")
    parser.add_argument("--max-workers", type=int, default=5,
                        help="Number of concurrent workers for crawling")
    parser.add_argument("--no-delay", action="store_true",
                        help="Disable random delays during crawling")
    parser.add_argument("--selenium-only", action="store_true",
                        help="Force using Selenium for all page fetches")
    parser.add_argument("--use-keywords", action="store_true",
                        help="Use keywords from the keyword file to filter pages")
    parser.add_argument("--page-timeout", type=int, default=10,
                        help="Timeout (in seconds) for HTTP requests")
    parser.add_argument("--selenium-timeout", type=int, default=15,
                        help="Timeout (in seconds) for Selenium page loads")
    parser.add_argument("--retry-count", type=int, default=3,
                        help="Number of retries for failed HTTP requests")
    parser.add_argument("--no-cache", action="store_true",
                        help="Disable caching (force re-crawl and re-computation)")
    parser.add_argument("--project-dir", type=str, default=DEFAULT_PROJECTS_DIR,
                        help="Directory for storing project data")
    parser.add_argument("--keyword-file", type=str, default=DEFAULT_KEYWORDS_FILE,
                        help="File containing search keywords")
    parser.add_argument("--output", type=str,
                        help="Output file for the generated BS4 template")
    args = parser.parse_args()

    # Set console verbosity based on --verbose
    verbose_mapping = {
        "off": logging.CRITICAL + 10,
        "v": logging.WARNING,
        "vv": logging.INFO,
        "vvv": logging.DEBUG,
        "infinite": logging.NOTSET
    }
    logging.getLogger().setLevel(verbose_mapping[args.verbose])
    
    try:
        main(args)
    except KeyboardInterrupt:
        logging.info("[MAIN] Process aborted by user. Exiting cleanly...")
        sys.exit(0)
