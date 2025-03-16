#!/usr/bin/env python3
import os
import sys
import time
import locale
import pickle
import logging
import difflib
import random
import requests
from tqdm import tqdm
from bs4 import BeautifulSoup
from urllib.parse import urlparse, urljoin
from colorama import init, Fore, Style
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# Für Headless-Browser (Lösung 1)
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

# Colorama initialisieren (für farbige Konsolenausgaben)
init(autoreset=True)

# Logging-Konfiguration: Alle DEBUG-Meldungen werden in "log.txt" geschrieben.
logging.basicConfig(
    filename='log.txt',
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s',
    filemode='w'
)

# Konfigurationen und Pfade
PROJECTS_DIR = 'projects'
MHTML_DIR = 'downloaded_mhtml'
OUTPUT_FILE = 'bs4code.txt'
CACHE_FILE = 'cache.pkl'
KEYWORDS_FILE = 'bs4-search-items.txt'

# Übersetzungsdictionary für Ausgaben (10 häufigste Sprachen)
translations = {
    'header': {
        'en': "Starting BS4 Template Generator...",
        'de': "Starte BS4-Template-Generator...",
        'es': "Iniciando el Generador de Plantillas BS4...",
        'fr': "Démarrage du Générateur de Template BS4...",
        'it': "Avvio del Generatore di Template BS4...",
        'pt': "Iniciando o Gerador de Template BS4...",
        'ru': "Запуск генератора шаблонов BS4...",
        'ja': "BS4テンプレートジェネレーターを起動しています...",
        'ko': "BS4 템플릿 생성기를 시작합니다...",
        'zh': "启动 BS4 模板生成器..."
    },
    'read_files': {
        'en': "Reading all downloaded and supported file formats suitable for analysis and parsing them with BeautifulSoup...",
        'de': "Liest alle heruntergeladenen und zur Auswertung geeigneten und unterstützten Dateiformate ein und parst sie mit BeautifulSoup...",
        'es': "Leyendo todos los formatos de archivo descargados y compatibles, adecuados para el análisis, y parseándolos con BeautifulSoup...",
        'fr': "Lecture de tous les formats de fichiers téléchargés et supportés, adaptés à l'analyse, et leur analyse avec BeautifulSoup...",
        'it': "Lettura di tutti i formati di file scaricati e supportati, adatti all'analisi, e loro parsing con BeautifulSoup...",
        'pt': "Lendo todos os formatos de arquivo baixados e suportados, adequados para análise, e parseando-os com BeautifulSoup...",
        'ru': "Чтение всех загруженных и поддерживаемых форматов файлов, подходящих для анализа, с последующим парсингом с помощью BeautifulSoup...",
        'ja': "ダウンロードされた、評価に適した、サポートされているすべてのファイル形式を読み込み、BeautifulSoupで解析します...",
        'ko': "다운로드 된 분석에 적합하고 지원되는 모든 파일 형식을 읽어 BeautifulSoup으로 파싱합니다...",
        'zh': "读取所有下载的、适用于分析和受支持的文件格式，并使用BeautifulSoup解析它们..."
    },
    'cache_loaded': {
        'en': "Cache successfully loaded.",
        'de': "Cache erfolgreich geladen.",
        'es': "Cache cargado con éxito.",
        'fr': "Cache chargé avec succès.",
        'it': "Cache caricato con successo.",
        'pt': "Cache carregado com sucesso.",
        'ru': "Кэш успешно загружен.",
        'ja': "キャッシュが正常に読み込まれました。",
        'ko': "캐시가 성공적으로 로드되었습니다.",
        'zh': "缓存加载成功。"
    },
    'cache_updated': {
        'en': "Cache successfully saved.",
        'de': "Cache erfolgreich gespeichert.",
        'es': "Cache guardado con éxito.",
        'fr': "Cache enregistré avec succès.",
        'it': "Cache salvato con successo.",
        'pt': "Cache salvo com sucesso.",
        'ru': "Кэш успешно сохранён.",
        'ja': "キャッシュが正常に保存されました。",
        'ko': "캐시가 성공적으로 저장되었습니다.",
        'zh': "缓存保存成功。"
    },
    'no_changes': {
        'en': "No changes detected – using cached data.",
        'de': "Keine Änderungen festgestellt – benutze den Cache.",
        'es': "No se detectaron cambios – usando datos en caché.",
        'fr': "Aucun changement détecté – utilisation du cache.",
        'it': "Nessuna modifica rilevata – utilizzo dei dati cache.",
        'pt': "Nenhuma mudança detectada – usando dados em cache.",
        'ru': "Изменений не обнаружено – используются данные из кэша.",
        'ja': "変更は検出されませんでした – キャッシュされたデータを使用します。",
        'ko': "변경 사항이 감지되지 않음 – 캐시된 데이터를 사용합니다.",
        'zh': "未检测到更改 – 使用缓存数据。"
    },
    'changes_detected': {
        'en': "Changes detected or no cache available – recalculating.",
        'de': "Änderungen erkannt oder Cache nicht vorhanden – starte Berechnung.",
        'es': "Se detectaron cambios o no hay caché disponible – recalculando.",
        'fr': "Changements détectés ou cache non disponible – recalcul en cours.",
        'it': "Modifiche rilevate o cache non disponibile – ricalcolo in corso.",
        'pt': "Alterações detectadas ou cache indisponível – recalculando.",
        'ru': "Обнаружены изменения или кэш недоступен – пересчет.",
        'ja': "変更が検出されたか、キャッシュが利用できません – 再計算中。",
        'ko': "변경 사항이 감지되었거나 캐시가 없음 – 재계산 중.",
        'zh': "检测到更改或无缓存可用 – 正在重新计算。"
    },
    'common_seq_length': {
        'en': "Common sequence has {0} lines.",
        'de': "Gemeinsame Sequenz hat {0} Zeilen.",
        'es': "La secuencia común tiene {0} líneas.",
        'fr': "La séquence commune comporte {0} lignes.",
        'it': "La sequenza comune ha {0} righe.",
        'pt': "A sequência comum tem {0} linhas.",
        'ru': "Общая последовательность содержит {0} строк.",
        'ja': "共通のシーケンスは{0}行です。",
        'ko': "공통 시퀀스에 {0} 줄이 있습니다.",
        'zh': "公共序列有 {0} 行。"
    },
    'template_written': {
        'en': "BS4 template written to '{0}'.",
        'de': "BS4-Code-Template wurde in '{0}' geschrieben.",
        'es': "Plantilla BS4 escrita en '{0}'.",
        'fr': "Template BS4 écrit dans '{0}'.",
        'it': "Template BS4 scritto in '{0}'.",
        'pt': "Template BS4 escrito em '{0}'.",
        'ru': "Шаблон BS4 записан в '{0}'.",
        'ja': "BS4テンプレートが'{0}'に書き込まれました。",
        'ko': "BS4 템플릿이 '{0}'에 작성되었습니다.",
        'zh': "BS4 模板已写入 '{0}'。"
    },
    'error_writing': {
        'en': "Error writing to '{0}': {1}",
        'de': "Fehler beim Schreiben in '{0}': {1}",
        'es': "Error al escribir en '{0}': {1}",
        'fr': "Erreur lors de l'écriture dans '{0}' : {1}",
        'it': "Errore nella scrittura in '{0}': {1}",
        'pt': "Erro ao escrever em '{0}': {1}",
        'ru': "Ошибка записи в '{0}': {1}",
        'ja': "'{0}'への書き込みエラー: {1}",
        'ko': "'{0}'에 쓰기 오류: {1}",
        'zh': "写入 '{0}' 时出错：{1}"
    },
    'elapsed_time': {
        'en': "Total time: {0:.2f} seconds",
        'de': "Gesamtzeit: {0:.2f} Sekunden",
        'es': "Tiempo total: {0:.2f} segundos",
        'fr': "Temps total : {0:.2f} secondes",
        'it': "Tempo totale: {0:.2f} secondi",
        'pt': "Tempo total: {0:.2f} segundos",
        'ru': "Общее время: {0:.2f} секунд",
        'ja': "総時間: {0:.2f}秒",
        'ko': "총 시간: {0:.2f}초",
        'zh': "总时间: {0:.2f} 秒"
    },
    'process_aborted': {
        'en': "Process aborted by user. Exiting cleanly...",
        'de': "Prozess vom Benutzer abgebrochen. Beende sauber...",
        'es': "Proceso abortado por el usuario. Saliendo limpiamente...",
        'fr': "Processus interrompu par l'utilisateur. Fermeture propre...",
        'it': "Processo interrotto dall'utente. Uscita pulita...",
        'pt': "Processo abortado pelo usuário. Saindo com segurança...",
        'ru': "Процесс прерван пользователем. Завершение...",
        'ja': "ユーザーによりプロzessが中断されました。正常に終了しています...",
        'ko': "사용자에 의해 프로세스가 중단되었습니다. 깔끔하게 종료합니다...",
        'zh': "进程被用户中止。正在正常退出..."
    }
}

def get_language():
    lang_tuple = locale.getdefaultlocale()
    if lang_tuple[0]:
        lang = lang_tuple[0].split('_')[0]
    else:
        lang = 'en'
    return lang if lang in translations['header'] else 'en'

LANG = get_language()

def animate_rainbow_header(ascii_art, duration=5, frame_interval=0.15):
    rainbow_colors = [Fore.RED, Fore.YELLOW, Fore.GREEN, Fore.CYAN, Fore.BLUE, Fore.MAGENTA]
    total_frames = int(duration / frame_interval)
    ascii_lines = ascii_art.splitlines()
    last_frame_lines = []
    for frame in range(total_frames):
        os.system('cls' if os.name == 'nt' else 'clear')
        current_frame = []
        for line in ascii_lines:
            colored_line = ""
            for idx, ch in enumerate(line):
                color_index = (idx + frame) % len(rainbow_colors)
                colored_line += rainbow_colors[color_index] + ch
            current_frame.append(colored_line + Style.RESET_ALL)
        print("\n".join(current_frame))
        time.sleep(frame_interval)
        last_frame_lines = current_frame
    return "\n".join(last_frame_lines)

def print_matrix_header():
    ascii_art = f"""
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
    print(Fore.CYAN + Style.BRIGHT + translations['header'][LANG] + Style.RESET_ALL)
    return final_ascii_art

def load_keywords(filename):
    if os.path.exists(filename):
        with open(filename, 'r', encoding='utf-8') as f:
            keywords = [line.strip() for line in f if line.strip()]
        logging.debug(f"Loaded {len(keywords)} search keywords from {filename}.")
        return keywords
    else:
        logging.error(f"Keywords file {filename} not found.")
        return []

def extract_domain(url):
    parsed = urlparse(url)
    domain = parsed.netloc
    if domain.startswith('www.'):
        domain = domain[4:]
    return domain

def check_project_existence(url):
    domain = extract_domain(url)
    project_path = os.path.join(PROJECTS_DIR, domain)
    exists = os.path.exists(project_path)
    return exists, project_path

def create_project_structure(project_path):
    os.makedirs(project_path, exist_ok=True)
    mhtml_path = os.path.join(project_path, MHTML_DIR)
    os.makedirs(mhtml_path, exist_ok=True)
    logging.debug(f"Created project structure at {project_path}.")
    return mhtml_path

def prioritize_urls(url_list):
    """
    Priorisiert URLs nach der Tiefe (Anzahl der '/'), sodass Seiten mit geringerer Tiefe bevorzugt werden.
    """
    return sorted(url_list, key=lambda url: (url.count('/'), url))

def is_cloudflare_error_page(content):
    """
    Prüft, ob der Seiteninhalt typische Marker einer Cloudflare-Fehlerseite enthält.
    """
    if not content:
        return True
    markers = ["cf-error-details", "Email Protection", "Cloudflare Ray ID:"]
    return any(marker in content for marker in markers)

def get_page_content(url, session, headers):
    """
    Versucht zuerst, den Inhalt per Requests zu laden.
    Falls Cloudflare-Schutz erkannt wird, wird auf Selenium umgeschaltet.
    Es werden zudem zufällige Verzögerungen eingefügt.
    """
    try:
        response = session.get(url, headers=headers, timeout=10)
        content = response.text
        if is_cloudflare_error_page(content):
            logging.debug(f"Cloudflare-Schutz erkannt bei {url} (via Requests), wechsle zu Selenium.")
            content = get_content_with_selenium(url, headers)
        return content
    except Exception as e:
        logging.error(f"Error fetching {url} with requests: {e}")
        return get_content_with_selenium(url, headers)

def get_content_with_selenium(url, headers):
    """
    Lädt die Seite mit Selenium im Headless-Modus.
    Setzt den User-Agent entsprechend.
    """
    try:
        options = Options()
        options.add_argument("--headless")
        options.add_argument("--disable-gpu")
        options.add_argument(f'user-agent={headers["User-Agent"]}')
        driver = webdriver.Chrome(options=options)
        driver.get(url)
        time.sleep(random.uniform(2, 4))
        content = driver.page_source
        driver.quit()
        return content
    except Exception as e:
        logging.error(f"Error fetching {url} with Selenium: {e}")
        return ""

def crawl_website(url, download_dir, strategy='bfs', sort_links=True):
    """
    Crawlt alle Seiten innerhalb der Domain und speichert sie im MHTML-Format.
    Unterstützt BFS/DFS, verwendet einen Retry-Mechanismus, wechselt bei Bedarf zu Selenium,
    fügt zufällige Verzögerungen ein und ignoriert Cloudflare-Fehlerseiten.
    """
    domain = extract_domain(url)
    visited = set()
    to_visit = [url]
    downloaded_files = []
    pbar = tqdm(desc=f"{Fore.GREEN}Downloading pages{Style.RESET_ALL}", ncols=80)
    
    session = requests.Session()
    retry_strategy = Retry(
        total=3,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["HEAD", "GET", "OPTIONS"],
        backoff_factor=1
    )
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    
    headers = {'User-Agent': 'Mozilla/5.0 (compatible; BS4TemplateGenerator/1.0)'}
    
    while to_visit:
        if strategy == 'bfs':
            current_url = to_visit.pop(0)
        elif strategy == 'dfs':
            current_url = to_visit.pop()
        else:
            current_url = to_visit.pop(0)
        
        if current_url in visited:
            continue
        visited.add(current_url)
        
        content = get_page_content(current_url, session, headers)
        time.sleep(random.uniform(1, 3))
        
        # Wenn der Inhalt eine Cloudflare-Fehlerseite ist, wird dieser Link ignoriert.
        if content and not is_cloudflare_error_page(content):
            file_index = len(downloaded_files) + 1
            filename = os.path.join(download_dir, f"page_{file_index}.mhtml")
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(content)
            downloaded_files.append(filename)
            pbar.update(1)
            logging.debug(f"Downloaded {current_url} to {filename}.")
            soup = BeautifulSoup(content, 'lxml')
            new_links = []
            for link in soup.find_all('a', href=True):
                href = link['href']
                absolute_url = urljoin(current_url, href)
                if extract_domain(absolute_url) == domain and absolute_url not in visited:
                    new_links.append(absolute_url)
            if sort_links:
                new_links = prioritize_urls(new_links)
            to_visit.extend(new_links)
        else:
            logging.info(f"Ignored Cloudflare error page or empty content from {current_url}.")
    
    pbar.close()
    return downloaded_files

def read_supported_files(directory):
    logging.debug(f"Starte das Einlesen von unterstützten Dateien aus dem Ordner '{directory}'.")
    supported_exts = ('.mhtml', '.html', '.htm')
    files = [os.path.join(directory, f) for f in os.listdir(directory) if f.lower().endswith(supported_exts)]
    documents = {}
    for file in tqdm(files, desc=f"{Fore.GREEN}{translations['read_files'][LANG]}{Style.RESET_ALL}", ncols=80):
        try:
            with open(file, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
                soup = BeautifulSoup(content, 'lxml')
                html_lines = soup.prettify().splitlines()
                documents[file] = html_lines
            logging.debug(f"Datei '{file}' erfolgreich eingelesen ({len(html_lines)} Zeilen).")
        except Exception as e:
            logging.error(f"Fehler beim Einlesen von '{file}': {e}")
    return documents

def normalize_html_lines(lines):
    """
    Normalisiert die HTML-Zeilen, indem führende und nachfolgende Leerzeichen entfernt werden und leere Zeilen ausgesondert werden.
    """
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
    common_seq = None
    for filename, lines in documents.items():
        normalized = normalize_html_lines(lines)
        if common_seq is None:
            common_seq = normalized
            logging.debug(f"Starte mit der Datei '{filename}' als Basis.")
        else:
            common_seq = lcs(common_seq, normalized)
            logging.debug(f"Nach Verarbeitung von '{filename}' Länge der gemeinsamen Sequenz: {len(common_seq)} Zeilen.")
    return common_seq

def compute_variable_lines(doc_lines, common_seq):
    diff = difflib.ndiff(common_seq, doc_lines)
    variable_lines = [line[2:] for line in diff if line.startswith('+ ')]
    return variable_lines

def aggregate_variable_lines(documents, common_seq):
    variable_all = []
    for filename, lines in documents.items():
        var_lines = compute_variable_lines(lines, common_seq)
        logging.debug(f"{filename}: {len(var_lines)} variable Zeilen gefunden.")
        variable_all.extend(var_lines)
    seen = set()
    variable_ordered = []
    for line in variable_all:
        if line not in seen and line.strip():
            seen.add(line)
            variable_ordered.append(line)
    logging.debug(f"Insgesamt {len(variable_ordered)} einzigartige variable Zeilen aggregiert.")
    return variable_ordered

def generate_bs4_template(common_seq, variable_lines):
    template = '''"""
Automatisch generiertes BS4-Template

=== Gemeinsame (statische) HTML-Struktur aller unterstützten Dateien ===
'''
    for line in common_seq:
        template += line + "\n"
    template += '''
=== Variablen Bereiche (potenziell relevante Daten, die sich unterscheiden) ===
'''
    for line in variable_lines:
        safe_line = line.strip().replace('"""', '\"\"\"')
        if safe_line:
            template += "# " + safe_line + "\n"
    template += '''
=== Endgültiges Template zur Extraktion ===

Die Funktion "extract_relevant_data" ist ein Ausgangspunkt, um mit BeautifulSoup
die relevanten Daten aus dem HTML zu extrahieren. Passe diese Funktion nach Bedarf an.
"""

from bs4 import BeautifulSoup

def extract_relevant_data(html_content):
    soup = BeautifulSoup(html_content, 'lxml')
    # Beispiel: Extrahiere ein Element anhand seiner Klasse oder seines Tags
    # title = soup.find("h1", class_="product-title").get_text(strip=True)
    # price = soup.find("span", class_="price").get_text(strip=True)
    # Füge hier weitere Extraktionen hinzu
    return soup.get_text(separator=" ", strip=True)

if __name__ == '__main__':
    with open('example.mhtml', 'r', encoding='utf-8', errors='ignore') as f:
        html = f.read()
    data = extract_relevant_data(html)
    print(data)
'''
    return template

def load_cache():
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, 'rb') as f:
                cache = pickle.load(f)
            logging.debug(translations['cache_loaded'][LANG])
            return cache
        except Exception as e:
            logging.error(f"Fehler beim Laden des Caches: {e}")
    return {}

def save_cache(cache):
    try:
        with open(CACHE_FILE, 'wb') as f:
            pickle.dump(cache, f)
        logging.debug(translations['cache_updated'][LANG])
    except Exception as e:
        logging.error(f"Fehler beim Speichern des Caches: {e}")

def files_have_changed(documents, cached_info):
    for filepath in documents.keys():
        mtime = os.path.getmtime(filepath)
        if filepath not in cached_info or cached_info[filepath] != mtime:
            return True
    return False

def update_cache_info(documents):
    cache_info = {}
    for filepath in documents.keys():
        cache_info[filepath] = os.path.getmtime(filepath)
    return cache_info

def main():
    start_time = time.time()
    final_header = print_matrix_header()
    
    project_url = input("Please enter the project URL: ").strip()
    logging.debug(f"User entered project URL: {project_url}")
    exists, project_path = check_project_existence(project_url)
    if exists:
        print(f"{Fore.GREEN}Project exists.{Style.RESET_ALL}")
        logging.debug("Projekt existiert.")
    else:
        print(f"{Fore.YELLOW}Project not found. Creating new project structure...{Style.RESET_ALL}")
        logging.debug("Projekt nicht gefunden. Erstelle neue Projektstruktur...")
        project_path = os.path.join(PROJECTS_DIR, extract_domain(project_url))
        mhtml_path = create_project_structure(project_path)
        print(f"{Fore.GREEN}Downloading project pages...{Style.RESET_ALL}")
        downloaded_files = crawl_website(project_url, mhtml_path, strategy='bfs', sort_links=True)
        if not downloaded_files:
            print(f"{Fore.RED}No pages downloaded. Exiting.{Style.RESET_ALL}")
            logging.error("No pages downloaded. Exiting.")
            sys.exit(1)
    
    mhtml_dir = os.path.join(project_path, MHTML_DIR)
    if not os.path.exists(mhtml_dir):
        print(f"{Fore.RED}Directory not found in project. Exiting.{Style.RESET_ALL}")
        logging.error("Directory not found in project. Exiting.")
        sys.exit(1)
    
    documents = read_supported_files(mhtml_dir)
    if not documents:
        print(f"{Fore.RED}No supported files found. Exiting.{Style.RESET_ALL}")
        logging.error("No supported files found. Exiting.")
        sys.exit(1)
    
    cache = load_cache()
    cached_info = cache.get("file_info", {})
    cached_common = cache.get("common_seq", None)
    cached_variables = cache.get("variable_lines", None)
    
    if cached_common is not None and not files_have_changed(documents, cached_info):
        logging.debug(translations['no_changes'][LANG])
        common_seq = cached_common
        variable_lines = cached_variables
    else:
        logging.debug(translations['changes_detected'][LANG])
        common_seq = compute_common_sequence(documents)
        if common_seq is None:
            print(f"{Fore.RED}Error: Common sequence could not be computed. Exiting.{Style.RESET_ALL}")
            logging.error("Common sequence is None.")
            sys.exit(1)
        logging.debug(translations['common_seq_length'][LANG].format(len(common_seq)))
        variable_lines = aggregate_variable_lines(documents, common_seq)
        cache["file_info"] = update_cache_info(documents)
        cache["common_seq"] = common_seq
        cache["variable_lines"] = variable_lines
        save_cache(cache)
    
    logging.debug("Generating BS4 code template.")
    bs4_template = generate_bs4_template(common_seq, variable_lines)
    try:
        with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
            f.write(bs4_template)
        logging.debug(translations['template_written'][LANG].format(OUTPUT_FILE))
        print(f"{Fore.CYAN}{Style.BRIGHT}{translations['template_written'][LANG].format(OUTPUT_FILE)}{Style.RESET_ALL}")
    except Exception as e:
        logging.error(translations['error_writing'][LANG].format(OUTPUT_FILE, e))
        print(f"{Fore.RED}{Style.BRIGHT}{translations['error_writing'][LANG].format(OUTPUT_FILE, e)}{Style.RESET_ALL}")
    
    elapsed = time.time() - start_time
    print(f"{Fore.MAGENTA}{translations['elapsed_time'][LANG].format(elapsed)}{Style.RESET_ALL}")

if __name__ == '__main__':
    try:
        keywords = load_keywords(KEYWORDS_FILE)
        logging.debug(f"Keywords: {keywords[:5]} ...")
        main()
    except KeyboardInterrupt:
        print(f"\n{Fore.RED}{Style.BRIGHT}{translations['process_aborted'][LANG]}{Style.RESET_ALL}")
        logging.info("Process aborted by KeyboardInterrupt.")
        sys.exit(0)
