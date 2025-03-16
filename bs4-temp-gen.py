#!/usr/bin/env python3
import os
import sys
import time
import locale
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

# Für Headless-Browser
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC

# Colorama initialisieren (für farbige Konsolenausgaben)
init(autoreset=True)

# Standardwerte für Konfigurationen
DEFAULT_PROJECTS_DIR = "projects"
DEFAULT_KEYWORDS_FILE = "bs4-search-items.txt"

# Übersetzungsdictionary für Ausgaben (10 häufigste Sprachen)
translations = {
    "header": {
        "en": "Starting BS4 Template Generator...",
        "de": "Starte BS4-Template-Generator...",
        "es": "Iniciando el Generador de Plantillas BS4...",
        "fr": "Démarrage du Générateur de Template BS4...",
        "it": "Avvio del Generatore di Template BS4...",
        "pt": "Iniciando o Gerador de Template BS4...",
        "ru": "Запуск генератора шаблонов BS4...",
        "ja": "BS4テンプレートジェネレーターを起動しています...",
        "ko": "BS4 템플릿 생성기를 시작합니다...",
        "zh": "启动 BS4 模板生成器..."
    },
    "read_files": {
        "en": "Reading all downloaded and supported file formats...",
        "de": "Liest alle heruntergeladenen und unterstützten Dateiformate ein...",
        "es": "Leyendo todos los formatos de archivo descargados...",
        "fr": "Lecture de tous les formats de fichiers téléchargés...",
        "it": "Lettura di tutti i formati di file scaricati...",
        "pt": "Lendo todos os formatos de arquivo baixados...",
        "ru": "Чтение всех загруженных und unterstützten Formate...",
        "ja": "すべてのダウンロード済みファイル形式を読み込みます...",
        "ko": "다운로드된 모든 파일 형식을 읽습니다...",
        "zh": "读取所有下载的文件格式..."
    },
    "cache_loaded": {
        "en": "Cache successfully loaded.",
        "de": "Cache erfolgreich geladen.",
        "es": "Cache cargado con éxito.",
        "fr": "Cache chargé avec succès.",
        "it": "Cache caricato con successo.",
        "pt": "Cache carregado com sucesso.",
        "ru": "Кэш успешно загружен.",
        "ja": "キャッシュが正常に読み込まれました。",
        "ko": "캐시가 성공적으로 로드되었습니다.",
        "zh": "缓存加载成功。"
    },
    "cache_updated": {
        "en": "Cache successfully saved.",
        "de": "Cache erfolgreich gespeichert.",
        "es": "Cache guardado con éxito.",
        "fr": "Cache enregistré avec succès.",
        "it": "Cache salvato con successo.",
        "pt": "Cache salvo com sucesso.",
        "ru": "Кэш успешно сохранён.",
        "ja": "キャッシュが正常に保存されました。",
        "ko": "캐시가 성공적으로 저장되었습니다.",
        "zh": "缓存保存成功。"
    },
    "no_changes": {
        "en": "No changes detected – using cached data.",
        "de": "Keine Änderungen festgestellt – benutze den Cache.",
        "es": "No se detectaron cambios – usando datos en caché.",
        "fr": "Aucun changement détecté – utilisation du cache.",
        "it": "Nessuna modifica rilevata – utilizzo dei dati cache.",
        "pt": "Nenhuma mudança detectada – usando dados em cache.",
        "ru": "Изменungen nicht обнаружено – используются Daten aus dem Cache.",
        "ja": "変更は検出されませんでした – キャッシュされたデータを使用します。",
        "ko": "변경 사항이 감지되지 않음 – 캐시된 데이터를 사용합니다.",
        "zh": "未检测到更改 – 使用缓存数据。"
    },
    "changes_detected": {
        "en": "Changes detected or no cache available – recalculating.",
        "de": "Änderungen erkannt oder Cache nicht vorhanden – starte Berechnung.",
        "es": "Se detectaron cambios o no hay caché verfügbar – recalculando.",
        "fr": "Changements détectés ou cache non disponible – recalcul en cours.",
        "it": "Modifiche rilevate o cache non disponibile – ricalcolo in corso.",
        "pt": "Alterações detectadas ou cache indisponível – recalculando.",
        "ru": "Изменungen erkannt oder кэш недоступен – пересчет.",
        "ja": "変更が検出されたか、キャッシュが利用できません – 再計算中。",
        "ko": "변경 사항이 감지되었거나 캐시가 없음 – 재계산 중.",
        "zh": "检测到更改或无缓存可用 – 正在重新计算。"
    },
    "common_seq_length": {
        "en": "Common sequence has {0} lines.",
        "de": "Gemeinsame Sequenz hat {0} Zeilen.",
        "es": "La secuencia común tiene {0} líneas.",
        "fr": "La séquence commune comporte {0} lignes.",
        "it": "La sequenza comune ha {0} righe.",
        "pt": "A sequência comum tem {0} linhas.",
        "ru": "Общая последовательность enthält {0} строк.",
        "ja": "共通のシーケンスは{0}行です。",
        "ko": "공통 시퀀스에 {0} 줄이 있습니다.",
        "zh": "公共序列有 {0} 行。"
    },
    "template_written": {
        "en": "BS4 template written to '{0}'.",
        "de": "BS4-Code-Template wurde in '{0}' geschrieben.",
        "es": "Plantilla BS4 escrita en '{0}'.",
        "fr": "Template BS4 écrit dans '{0}'.",
        "it": "Template BS4 scritto in '{0}'.",
        "pt": "Template BS4 escrito em '{0}'.",
        "ru": "Шаблон BS4 записан в '{0}'.",
        "ja": "BS4テンプレートが'{0}'に書き込まれました。",
        "ko": "BS4 템플릿이 '{0}'에 작성되었습니다.",
        "zh": "BS4 模板已写入 '{0}'。"
    },
    "error_writing": {
        "en": "Error writing to '{0}': {1}",
        "de": "Fehler beim Schreiben in '{0}': {1}",
        "es": "Error al escribir en '{0}': {1}",
        "fr": "Erreur lors de l'écriture dans '{0}' : {1}",
        "it": "Errore nella scrittura in '{0}': {1}",
        "pt": "Erro ao escrever em '{0}': {1}",
        "ru": "Ошибка записи in '{0}': {1}",
        "ja": "'{0}'への書き込みエラー: {1}",
        "ko": "'{0}'에 쓰기 오류: {1}",
        "zh": "写入 '{0}' 时出错：{1}"
    },
    "elapsed_time": {
        "en": "Total time: {0:.2f} seconds",
        "de": "Gesamtzeit: {0:.2f} Sekunden",
        "es": "Tiempo total: {0:.2f} segundos",
        "fr": "Temps total : {0:.2f} secondes",
        "it": "Tempo totale: {0:.2f} secondi",
        "pt": "Tempo total: {0:.2f} segundos",
        "ru": "Общее время: {0:.2f} секунд",
        "ja": "総時間: {0:.2f}秒",
        "ko": "총 시간: {0:.2f}초",
        "zh": "总时间: {0:.2f} 秒"
    },
    "process_aborted": {
        "en": "Process aborted by user. Exiting cleanly...",
        "de": "Prozess vom Benutzer abgebrochen. Beende sauber...",
        "es": "Proceso abortado por el usuario. Saliendo limpiamente...",
        "fr": "Processus interrompu par l'utilisateur. Fermeture propre...",
        "it": "Processo interrotto dall'utente. Uscita pulita...",
        "pt": "Processo abortado pelo usuário. Saindo com segurança...",
        "ru": "Процесс прерван пользователем. Завершение...",
        "ja": "ユーザーによりプロzessが中断されました。正常に終了しています...",
        "ko": "사용자에 의해 프로세스가 중단되었습니다. 깔끔하게 종료합니다...",
        "zh": "进程被用户中止。正在正常退出..."
    }
}

# Ermittelt die Systemsprache; kann per CLI überschrieben werden
def get_language():
    lang = None
    try:
        lang_tuple = locale.getdefaultlocale()
        if lang_tuple and lang_tuple[0]:
            lang = lang_tuple[0].split('_')[0]
    except Exception as e:
        logging.error(f"[LANG] Error in getdefaultlocale(): {e}")
    if not lang or lang not in translations["header"]:
        lang_env = os.environ.get("LANG", "en")
        lang = lang_env.split('_')[0]
    return lang if lang in translations["header"] else "en"

LANG = get_language()

# Globaler Lock für einen gemeinsamen Selenium-Driver
selenium_lock = threading.Lock()

def animate_rainbow_header(ascii_art, duration=5, frame_interval=0.15):
    rainbow_colors = [Fore.RED, Fore.YELLOW, Fore.GREEN, Fore.CYAN, Fore.BLUE, Fore.MAGENTA]
    total_frames = int(duration / frame_interval)
    ascii_lines = ascii_art.splitlines()
    for frame in range(total_frames):
        os.system("cls" if os.name == "nt" else "clear")
        current_frame = []
        for idx, line in enumerate(ascii_lines):
            colored_line = ""
            for ch in line:
                color_index = (idx + frame) % len(rainbow_colors)
                colored_line += rainbow_colors[color_index] + ch
            current_frame.append(colored_line + Style.RESET_ALL)
        print("\n".join(current_frame))
        time.sleep(frame_interval)
    return "\n".join(current_frame)

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
    final_ascii_art = animate_rainbow_header(ascii_art, duration=5, frame_interval=0.15)
    return final_ascii_art

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
    logging.debug(f"[PROJECT] Checking existence of project for domain '{domain}': {'found' if exists else 'not found'}.")
    return exists, project_path

def create_project_structure(project_path):
    os.makedirs(project_path, exist_ok=True)
    mhtml_path = os.path.join(project_path, "downloaded_mhtml")
    os.makedirs(mhtml_path, exist_ok=True)
    logging.debug(f"[PROJECT] Created project structure at {project_path}.")
    return mhtml_path

def prioritize_urls(url_list):
    """[CRAWLING] Prioritizes URLs based on depth (number of '/') to favor shallower pages."""
    return sorted(url_list, key=lambda url: (url.count("/"), url))

def is_cloudflare_error_page(content):
    """[HTTP] Checks if content indicates a Cloudflare error."""
    if not content:
        return True
    markers = ["cf-error-details", "Email Protection", "Cloudflare Ray ID:"]
    return any(marker in content for marker in markers)

# Normalisiert HTML und entfernt variable Inhalte
def prepare_for_comparison(html_content):
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

# Erweiterte get_page_content mit Timeouts und Retry
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
                logging.debug(f"[HTTP] Cloudflare protection detected for {url}. Switching to Selenium.")
                return get_content_with_selenium(url, headers, shared_driver, selenium_timeout)
            return content
        except Exception as e:
            logging.warning(f"[HTTP] Attempt {attempt+1} for {url} failed: {e}")
            if not no_delay:
                time.sleep(2)
    logging.debug(f"[HTTP] Falling back to Selenium for {url} after {retry_count} failed attempts.")
    return get_content_with_selenium(url, headers, shared_driver, selenium_timeout)

# Angepasste Selenium-Funktion, ggf. mit geteiltem Driver
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

# Paralleles Crawling mit Unterstützung von max_depth (-1 = infinite)
def crawl_website(url, download_dir, strategy="bfs", sort_links=True, max_pages=-1, max_depth=-1, no_delay=False,
                  selenium_only=False, max_workers=5, page_timeout=10, selenium_timeout=15, retry_count=3,
                  keywords=None, use_keywords=False):
    domain = extract_domain(url)
    logging.info(f"[CRAWLING] Starting crawl for domain '{domain}'.")
    visited = set()
    # to_visit enthält Tupel: (url, depth)
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
    for file in tqdm(files, desc=f"{Fore.GREEN}{translations['read_files'][LANG]}{Style.RESET_ALL}", ncols=80):
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
            logging.debug(f"[CACHE] {translations['cache_loaded'][LANG]}")
            return cache
        except Exception as e:
            logging.error(f"[CACHE] Error loading cache: {e}")
    return {}

def save_cache(cache):
    try:
        with open(CACHE_FILE, "wb") as f:
            pickle.dump(cache, f)
        logging.debug(f"[CACHE] {translations['cache_updated'][LANG]}")
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
    global LANG
    if args.lang:
        LANG = args.lang

    # Set console verbosity based on --verbose
    verbose_mapping = {
        "off": logging.CRITICAL + 10,  # virtually no output
        "v": logging.WARNING,
        "vv": logging.INFO,
        "vvv": logging.DEBUG,
        "infinite": logging.NOTSET
    }
    logging.getLogger().setLevel(verbose_mapping[args.verbose])
    
    final_header = print_matrix_header()
    logging.info(f"[MAIN] {translations['header'][LANG]}")
    
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
        logging.debug(f"[COMMON] {translations['common_seq_length'][LANG].format(len(common_seq))}")
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
        logging.info(f"[TEMPLATE] {translations['template_written'][LANG].format(OUTPUT_FILE)}")
    except Exception as e:
        logging.error(f"[TEMPLATE] {translations['error_writing'][LANG].format(OUTPUT_FILE, e)}")
    
    elapsed = time.time() - start_time
    logging.info(f"[MAIN] {translations['elapsed_time'][LANG].format(elapsed)}")
    print(translations["elapsed_time"][LANG].format(elapsed))

if __name__ == "__main__":
    # Initiales Logging für Konsolenausgaben (wird später anhand von --verbose angepasst)
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    parser = argparse.ArgumentParser(
        description="BS4 Template Generator with advanced crawling and extraction features"
    )
    parser.add_argument("--lang", choices=list(translations["header"].keys()), help="Language for output messages")
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
                        help="Use keywords from KEYWORDS_FILE to filter pages")
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
    
    try:
        main(args)
    except KeyboardInterrupt:
        logging.info(f"[MAIN] {translations['process_aborted'][LANG]}")
        sys.exit(0)
