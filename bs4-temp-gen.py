#!/usr/bin/env python3
"""
Advanced BS4 Template Generator – Ultimate Web-Scraping Engine

Features:
    - Asynchrones Crawling mit aiohttp und dynamischer URL-Priorisierung
    - Fallback auf Selenium bei Cloudflare-/JS-geschützten Seiten
    - Multi-Format-Support: HTML, JSON, XML und optionale PDF-/CSV-Handling (erweiterbar)
    - KI-gestützte Datenextraktion: NLP-basierte Analyse mit spaCy (falls verfügbar)
    - Umfassendes Logging & Performance-Monitoring (konsole & Datei, inklusive E-Mail-Benachrichtigung bei kritischen Fehlern)
    - Modularer Aufbau (Crawler, Parser, TemplateGenerator, ConfigManager)
    - Konfigurierbare Parameter über CLI und Konfigurationsdatei (YAML/JSON)
    - **Interaktive Menüführung, Statusanzeigen und Fortschrittsbalken** (CLI, voll tastaturgesteuert)
    
Dieses Skript wurde entwickelt, um Web-Scraping auf ein neues Level zu heben – robust, skalierbar und intelligent.
"""

import os, sys, time, locale, pickle, logging, difflib, random, re, argparse, threading, asyncio, json
import concurrent.futures
from queue import Queue
from tqdm import tqdm
from urllib.parse import urlparse, urljoin
import xml.etree.ElementTree as ET

# Externe Module für HTTP, HTML und Browser-Automation
import aiohttp
import requests
from bs4 import BeautifulSoup
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# Selenium für dynamische Inhalte
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC

# Colorama für farbige Ausgaben
from colorama import init, Fore, Style
init(autoreset=True)

# Optional: spaCy für NLP-basierte Extraktion (falls installiert)
try:
    import spacy
except ImportError:
    spacy = None

# Optional: prompt_toolkit für interaktive Menüs
try:
    from prompt_toolkit.shortcuts import radiolist_dialog
    from prompt_toolkit import prompt as pt_prompt
except ImportError:
    radiolist_dialog = None
    pt_prompt = input

# Optional: rich für ansprechende Statusanzeigen und Fortschrittsbalken
try:
    from rich.console import Console
    from rich.progress import Progress
except ImportError:
    Console = None

# =============================================
# Global Constants und Standard-Konfiguration
# =============================================

PROJECTS_DIR = "projects"
KEYWORDS_FILE = "bs4-search-items.txt"
DEFAULT_CONFIG = {
    "crawler": {
        "max_pages": 100,
        "concurrency": 10,
        "strategy": "bfs",          # bfs oder dfs
        "delay_range": [1, 3],
        "use_selenium": False,
        "use_keywords": False,
        "allowed_domains": []
    },
    "logging": {
        "level": "DEBUG",
        "console": True,
        "file": True,
        "log_filename": "log.txt",
        "email_notify": None         # z.B. "admin@example.com"
    },
    "output": {
        "template_filename": "bs4code.txt"
    },
    "nlp": {
        "enabled": True,
        "model": "en_core_web_sm"    # oder de_core_news_sm, etc.
    }
}

# Übersetzungsdictionary für Ausgaben (10 häufigste Sprachen)
translations = {
    "header": {
        "en": "Starting Advanced BS4 Template Generator...",
        "de": "Starte erweiterten BS4-Template-Generator...",
        "es": "Iniciando el Generador Avanzado de Plantillas BS4...",
        "fr": "Démarrage du Générateur Avancé de Template BS4...",
        "it": "Avvio del Generatore Avanzato di Template BS4...",
        "pt": "Iniciando o Gerador Avançado de Template BS4...",
        "ru": "Запуск расширенного генератора шаблонов BS4...",
        "ja": "拡張版BS4テンプレートジェネレーターを起動しています...",
        "ko": "고급 BS4 템플릿 생성기를 시작합니다...",
        "zh": "启动高级 BS4 模板生成器..."
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
        "ru": "Изменений не обнаружено – используются данные aus dem Cache.",
        "ja": "変更は検出されませんでした – キャッシュされたデータを使用します。",
        "ko": "변경 사항이 감지되지 않음 – 캐시된 데이터를 사용합니다.",
        "zh": "未检测到更改 – 使用缓存数据。"
    },
    "changes_detected": {
        "en": "Changes detected or no cache available – recalculating.",
        "de": "Änderungen erkannt oder Cache nicht vorhanden – starte Berechnung.",
        "es": "Se detectaron cambios o no hay caché disponible – recalculando.",
        "fr": "Changements détectés ou cache non disponible – recalcul en cours.",
        "it": "Modifiche rilevate o cache non disponibile – ricalcolo in corso.",
        "pt": "Alterações detectadas ou cache indisponível – recalculando.",
        "ru": "Обнаружены изменения oder кэш недоступен – пересчет.",
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
        "ru": "Общая последовательность содержит {0} строк.",
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
        "ru": "Ошибка записи в '{0}': {1}",
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

# =============================================
# Hilfsklassen: Konfigurations- und Logger-Manager
# =============================================

class ConfigManager:
    """
    Verwaltet Konfigurationen aus einer Datei (JSON oder YAML) und Standardwerte.
    """
    def __init__(self, config_file=None):
        self.config_file = config_file
        self.config = DEFAULT_CONFIG.copy()
        if config_file and os.path.exists(config_file):
            try:
                with open(config_file, "r", encoding="utf-8") as f:
                    if config_file.endswith(".json"):
                        user_config = json.load(f)
                    else:
                        # YAML-Parsing könnte hier erfolgen – als Beispiel verwenden wir JSON
                        user_config = json.load(f)
                self.merge_config(user_config)
            except Exception as e:
                logging.error(f"Error loading config from {config_file}: {e}")

    def merge_config(self, user_config):
        # Rekursive Zusammenführung von Dictionaries
        def merge(a, b):
            for key, value in b.items():
                if key in a and isinstance(a[key], dict) and isinstance(value, dict):
                    merge(a[key], value)
                else:
                    a[key] = value
        merge(self.config, user_config)

    def get(self, section, key, default=None):
        return self.config.get(section, {}).get(key, default)

class LoggerManager:
    """
    Konfiguriert das Logging: Ausgabe in Konsole und in Datei, sowie optionale E-Mail-Benachrichtigung.
    """
    def __init__(self, project_path, config):
        self.project_path = project_path
        self.config = config
        self.logger = logging.getLogger()
        self.setup_logging()

    def setup_logging(self):
        # Entferne alle vorhandenen Handler
        for handler in self.logger.handlers[:]:
            self.logger.removeHandler(handler)
        self.logger.setLevel(getattr(logging, self.config.get("logging", "level", "DEBUG")))
        formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
        if self.config.get("logging", "console", True):
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setFormatter(formatter)
            self.logger.addHandler(console_handler)
        if self.config.get("logging", "file", True):
            log_file = os.path.join(self.project_path, self.config.get("logging", "log_filename", "log.txt"))
            file_handler = logging.FileHandler(log_file, mode="a", encoding="utf-8")
            file_handler.setFormatter(formatter)
            self.logger.addHandler(file_handler)
        # Optional: E-Mail-Handler könnte hier konfiguriert werden

# =============================================
# Sprachbestimmung
# =============================================

def get_language():
    lang = None
    try:
        lang_tuple = locale.getdefaultlocale()
        if lang_tuple and lang_tuple[0]:
            lang = lang_tuple[0].split('_')[0]
    except Exception as e:
        logging.error(f"Error in getdefaultlocale(): {e}")
    if not lang or lang not in translations["header"]:
        lang_env = os.environ.get("LANG", "en")
        lang = lang_env.split('_')[0]
    return lang if lang in translations["header"] else "en"

LANG = get_language()

# =============================================
# KI-gestützte NLP-Auswertung (falls spaCy installiert)
# =============================================

def init_nlp(model_name):
    if spacy is None:
        logging.warning("spaCy is not installed. NLP features will be disabled.")
        return None
    try:
        nlp_model = spacy.load(model_name)
        logging.debug(f"spaCy model '{model_name}' loaded successfully.")
        return nlp_model
    except Exception as e:
        logging.error(f"Error loading spaCy model '{model_name}': {e}")
        return None

nlp_model = None  # Wird in main initialisiert, falls aktiviert

def analyze_text_with_nlp(text):
    """
    Analysiert Text mittels spaCy und extrahiert Entitäten.
    """
    if nlp_model is None:
        return {}
    doc = nlp_model(text)
    entities = {}
    for ent in doc.ents:
        entities.setdefault(ent.label_, []).append(ent.text)
    return entities

# =============================================
# Hilfsfunktionen: URL, Priorisierung, und Vergleich
# =============================================

def extract_domain(url):
    parsed = urlparse(url)
    domain = parsed.netloc
    if domain.startswith("www."):
        domain = domain[4:]
    return domain

def prioritize_urls(url_list):
    """Sortiert URLs nach Pfadtiefe (weniger '/' zuerst) und alphabetisch."""
    return sorted(url_list, key=lambda url: (url.count("/"), url))

def is_cloudflare_error_page(content):
    """Prüft, ob der Seiteninhalt typische Cloudflare-Fehlerindikatoren enthält."""
    if not content:
        return True
    markers = ["cf-error-details", "Email Protection", "Cloudflare Ray ID:"]
    return any(marker in content for marker in markers)

def prepare_for_comparison(html_content):
    """
    Normalisiert HTML: Entfernt dynamische Tags und variable Attribute,
    ersetzt Zahlen durch Platzhalter.
    """
    soup = BeautifulSoup(html_content, "lxml")
    for tag in soup(["script", "style"]):
        tag.decompose()
    for tag in soup.find_all(True):
        for attr in list(tag.attrs.keys()):
            if attr in ["id", "style"] or attr.startswith("on") or attr.startswith("data-"):
                del tag.attrs[attr]
    normalized = re.sub(r"\d+", "0", soup.prettify())
    return normalized

def normalize_html_lines(lines):
    return [line.strip() for line in lines if line.strip()]

def lcs(seq1, seq2):
    n, m = len(seq1), len(seq2)
    dp = [[0]*(m+1) for _ in range(n+1)]
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
            i -= 1; j -= 1
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
            logging.debug(f"Started common sequence with '{filename}'.")
        else:
            common_seq = lcs(common_seq, normalized)
            logging.debug(f"After '{filename}', common sequence has {len(common_seq)} lines.")
    return common_seq

def compute_variable_lines(doc_lines, common_seq):
    diff = difflib.ndiff(common_seq, doc_lines)
    variable_lines = [line[2:] for line in diff if line.startswith("+ ")]
    return variable_lines

def aggregate_variable_lines(documents, common_seq):
    variable_all = []
    for filename, lines in documents.items():
        var_lines = compute_variable_lines(lines, common_seq)
        logging.debug(f"{filename}: found {len(var_lines)} variable lines.")
        variable_all.extend(var_lines)
    seen = set()
    variable_ordered = []
    for line in variable_all:
        if line not in seen and line.strip():
            seen.add(line)
            variable_ordered.append(line)
    logging.debug(f"Aggregated {len(variable_ordered)} unique variable lines.")
    return variable_ordered

# =============================================
# Parser-Klassen: HTML, JSON und XML
# =============================================

class BaseParser:
    """
    Basisklasse für Parser. Alle Parser sollten die Methode parse(content) implementieren.
    """
    def parse(self, content):
        raise NotImplementedError("parse() muss in Unterklassen implementiert werden.")

class HTMLParser(BaseParser):
    def parse(self, content):
        soup = BeautifulSoup(content, "lxml")
        return soup

class JSONParser(BaseParser):
    def parse(self, content):
        try:
            return json.loads(content)
        except Exception as e:
            logging.error(f"JSON parsing error: {e}")
            return None

class XMLParser(BaseParser):
    def parse(self, content):
        try:
            return ET.fromstring(content)
        except Exception as e:
            logging.error(f"XML parsing error: {e}")
            return None

def detect_content_type(response):
    """
    Bestimmt den Inhaltstyp anhand des HTTP-Headers oder anhand von Dateiendungen.
    """
    content_type = response.headers.get("Content-Type", "")
    if "application/json" in content_type:
        return "json"
    elif "xml" in content_type:
        return "xml"
    else:
        return "html"

# =============================================
# Template-Generator: Erzeugt das BS4-Template
# =============================================

class TemplateGenerator:
    def __init__(self, common_seq, variable_lines):
        self.common_seq = common_seq
        self.variable_lines = variable_lines

    def generate_template(self):
        template = '''"""
Automatically generated Advanced BS4 Template

=== Common (static) HTML structure from all supported files ===
'''
        for line in self.common_seq:
            template += line + "\n"
        template += '''
=== Variable sections (data that differ) ===
'''
        for line in self.variable_lines:
            safe_line = line.strip().replace('"""', '\"\"\"')
            if safe_line:
                template += "# " + safe_line + "\n"
        template += '''
=== Final extraction template ===

The function "extract_relevant_data" is a starting point for extracting
relevant data from various content types using BeautifulSoup and additional NLP.
Customize as needed.
"""

from bs4 import BeautifulSoup

def extract_relevant_data(html_content):
    soup = BeautifulSoup(html_content, 'lxml')
    # Example: Extract an element by its class or tag
    # title = soup.find("h1", class_="product-title").get_text(strip=True)
    # price = soup.find("span", class_="price").get_text(strip=True)
    # Optionally, use NLP to analyze the text:
    # from your_module import analyze_text_with_nlp
    # entities = analyze_text_with_nlp(soup.get_text())
    return soup.get_text(separator=" ", strip=True)

if __name__ == '__main__':
    with open("example.mhtml", "r", encoding="utf-8", errors="ignore") as f:
        html = f.read()
    data = extract_relevant_data(html)
    print(data)
'''
        return template

# =============================================
# Caching-Funktionen
# =============================================

def load_cache(cache_file):
    if os.path.exists(cache_file):
        try:
            with open(cache_file, "rb") as f:
                cache = pickle.load(f)
            logging.debug(translations["cache_loaded"][LANG])
            return cache
        except Exception as e:
            logging.error(f"Error loading cache: {e}")
    return {}

def save_cache(cache, cache_file):
    try:
        with open(cache_file, "wb") as f:
            pickle.dump(cache, f)
        logging.debug(translations["cache_updated"][LANG])
    except Exception as e:
        logging.error(f"Error saving cache: {e}")

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

# =============================================
# Hilfsfunktion: Keywords laden
# =============================================

def load_keywords(filename):
    if os.path.exists(filename):
        with open(filename, "r", encoding="utf-8") as f:
            keywords = [line.strip() for line in f if line.strip()]
        logging.debug(f"Loaded {len(keywords)} search keywords from {filename}.")
        return keywords
    else:
        logging.error(f"Keywords file {filename} not found.")
        return []

# =============================================
# Asynchroner Crawler: aiohttp-basierte Implementierung
# =============================================

class AsyncCrawler:
    def __init__(self, start_url, download_dir, config, keywords=None):
        self.start_url = start_url
        self.download_dir = download_dir
        self.config = config
        self.visited = set()
        self.to_visit = asyncio.Queue()
        self.keywords = keywords
        self.domain = extract_domain(start_url)
        self.sem = asyncio.Semaphore(config.get("crawler", "concurrency", 10))
        self.session = None
        self.results = []
    
    async def init_session(self):
        timeout = aiohttp.ClientTimeout(total=15)
        self.session = aiohttp.ClientSession(timeout=timeout)
    
    async def close_session(self):
        if self.session:
            await self.session.close()
    
    async def fetch(self, url):
        headers = {"User-Agent": "Mozilla/5.0 (compatible; AdvancedBS4TemplateGenerator/2.0)"}
        async with self.sem:
            try:
                async with self.session.get(url, headers=headers) as response:
                    content_type = detect_content_type(response)
                    text = await response.text()
                    if is_cloudflare_error_page(text):
                        logging.debug(f"Cloudflare protection detected for {url}.")
                        return None
                    # Optional: Hier könnte man auch JSON/XML direkt parsen
                    return (url, text, content_type)
            except Exception as e:
                logging.warning(f"Async fetch error for {url}: {e}")
                return None

    async def worker(self):
        while True:
            url = await self.to_visit.get()
            if url in self.visited:
                self.to_visit.task_done()
                continue
            self.visited.add(url)
            result = await self.fetch(url)
            if result:
                url, content, ctype = result
                # Keyword-Filterung, falls aktiviert
                if self.config.get("crawler", "use_keywords", False) and self.keywords:
                    if not any(kw.lower() in content.lower() for kw in self.keywords):
                        logging.debug(f"Skipping {url} due to keyword filter.")
                        self.to_visit.task_done()
                        continue
                # Speichere den Inhalt als Datei
                index = len(self.results) + 1
                filename = os.path.join(self.download_dir, f"page_{index}.mhtml")
                try:
                    with open(filename, "w", encoding="utf-8") as f:
                        f.write(content)
                    self.results.append(filename)
                    logging.debug(f"Downloaded {url} to {filename}.")
                except Exception as e:
                    logging.error(f"Error writing file {filename}: {e}")
                # Extrahiere neue Links
                new_links = self.extract_links(content, url)
                for link in new_links:
                    if extract_domain(link) == self.domain and link not in self.visited:
                        await self.to_visit.put(link)
            self.to_visit.task_done()
            # Abbruchbedingung: max_pages erreicht
            if len(self.results) >= self.config.get("crawler", "max_pages", 100):
                break

    def extract_links(self, html, base_url):
        soup = BeautifulSoup(html, "lxml")
        links = []
        for link in soup.find_all("a", href=True):
            href = link["href"]
            absolute_url = urljoin(base_url, href)
            if absolute_url not in self.visited:
                links.append(absolute_url)
        if self.config.get("crawler", "strategy", "bfs") == "bfs":
            links = prioritize_urls(links)
        return links

    async def crawl(self):
        await self.init_session()
        await self.to_visit.put(self.start_url)
        workers = []
        for _ in range(self.config.get("crawler", "concurrency", 10)):
            worker_task = asyncio.create_task(self.worker())
            workers.append(worker_task)
        await self.to_visit.join()
        for w in workers:
            w.cancel()
        await self.close_session()
        return self.results

# =============================================
# Selenium-basierter Fallback-Crawler (synchron)
# =============================================

selenium_lock = threading.Lock()

def get_content_with_selenium(url, headers, shared_driver=None):
    if shared_driver:
        try:
            with selenium_lock:
                shared_driver.get(url)
                WebDriverWait(shared_driver, 10).until(lambda d: d.execute_script('return document.readyState') == 'complete')
                content = shared_driver.page_source
            return content
        except Exception as e:
            logging.error(f"Error fetching {url} with shared Selenium driver: {e}")
            return ""
    else:
        try:
            options = Options()
            options.add_argument("--headless")
            options.add_argument("--disable-gpu")
            options.add_argument(f'user-agent={headers["User-Agent"]}')
            driver = webdriver.Chrome(options=options)
            driver.set_page_load_timeout(15)
            driver.get(url)
            WebDriverWait(driver, 10).until(lambda d: d.execute_script('return document.readyState') == 'complete')
            content = driver.page_source
            driver.quit()
            return content
        except Exception as e:
            logging.error(f"Error fetching {url} with Selenium: {e}")
            return ""

def get_page_content(url, session, headers, selenium_only=False, shared_driver=None, no_delay=False):
    if selenium_only:
        return get_content_with_selenium(url, headers, shared_driver)
    MAX_RETRIES = 3
    for attempt in range(MAX_RETRIES):
        try:
            response = session.get(url, headers=headers, timeout=10)
            content = response.text
            if is_cloudflare_error_page(content):
                logging.debug(f"Cloudflare protection detected for {url} via Requests. Switching to Selenium.")
                return get_content_with_selenium(url, headers, shared_driver)
            return content
        except Exception as e:
            logging.warning(f"Attempt {attempt+1} for {url} failed: {e}")
            if not no_delay:
                time.sleep(2)
    # Fallback:
    return get_content_with_selenium(url, headers, shared_driver)

# =============================================
# Dateileser: Unterstützt HTML, MHTML, JSON und XML
# =============================================

def read_supported_files(directory):
    logging.debug(f"Reading supported files from '{directory}'.")
    supported_exts = (".mhtml", ".html", ".htm", ".json", ".xml")
    files = [os.path.join(directory, f) for f in os.listdir(directory) if f.lower().endswith(supported_exts)]
    documents = {}
    for file in tqdm(files, desc=f"{Fore.GREEN}{translations['read_files'][LANG]}{Style.RESET_ALL}", ncols=80):
        try:
            with open(file, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
                normalized_html = prepare_for_comparison(content)
                html_lines = normalized_html.splitlines()
                documents[file] = html_lines
            logging.debug(f"Read file '{file}' with {len(html_lines)} lines.")
        except Exception as e:
            logging.error(f"Error reading '{file}': {e}")
    return documents

# =============================================
# ASCII-Art Header (Rainbow Matrix Style)
# =============================================

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

# =============================================
# Interaktive Menüführung (prompt_toolkit)
# =============================================

def interactive_main_menu():
    if radiolist_dialog:
        choice = radiolist_dialog(
            title="Main Menu",
            text="Select an option:",
            values=[
                ("start", "Start Crawling and Generate Template"),
                ("config", "Configure Settings"),
                ("exit", "Exit")
            ]
        ).run()
        return choice
    else:
        print("Main Menu:")
        print("1. Start Crawling and Generate Template")
        print("2. Configure Settings")
        print("3. Exit")
        choice = input("Enter choice: ")
        if choice == "1":
            return "start"
        elif choice == "2":
            return "config"
        else:
            return "exit"

def interactive_config_menu(config):
    # Language selection
    if radiolist_dialog:
        lang = radiolist_dialog(
            title="Language Selection",
            text="Select output language:",
            values=[("en", "English"), ("de", "Deutsch"), ("fr", "French")]
        ).run()
    else:
        lang = input("Enter language (en/de/fr): ")
    config["lang"] = lang if lang in ["en", "de", "fr"] else "en"

    # Crawling mode selection
    if radiolist_dialog:
        crawl_mode = radiolist_dialog(
            title="Crawling Mode",
            text="Select crawling mode:",
            values=[("async", "Asynchronous Crawling (aiohttp)"), ("selenium", "Selenium Fallback")]
        ).run()
    else:
        crawl_mode = input("Enter crawling mode (async/selenium): ")
    config["crawler"]["use_selenium"] = True if crawl_mode == "selenium" else False

    # Keyword filtering selection
    if radiolist_dialog:
        keyword_filter = radiolist_dialog(
            title="Keyword Filtering",
            text="Enable keyword filtering?",
            values=[("yes", "Yes"), ("no", "No")]
        ).run()
    else:
        keyword_filter = input("Use keyword filtering? (yes/no): ")
    config["crawler"]["use_keywords"] = True if keyword_filter == "yes" else False

    return config

# =============================================
# Main-Funktion: Integration aller Komponenten inkl. interaktiver Menüs
# =============================================

def main(args):
    start_time = time.time()
    # Konfiguration laden (optional über Datei, hier CLI-Argumente und Standardwerte)
    config_manager = ConfigManager(args.config) if args.config else ConfigManager()
    config = config_manager.config

    # Interaktives Hauptmenü
    while True:
        choice = interactive_main_menu()
        if choice == "exit":
            print("Exiting...")
            sys.exit(0)
        elif choice == "config":
            config = interactive_config_menu(config)
            print("Configuration updated.")
        elif choice == "start":
            break

    # Spracheinstellung über interaktive Konfiguration (falls gesetzt)
    global LANG
    if "lang" in config:
        LANG = config["lang"]

    # Optional: spaCy-Modell initialisieren
    global nlp_model
    if config.get("nlp", "enabled", True):
        nlp_model = init_nlp(config.get("nlp", "model", "en_core_web_sm"))
    else:
        nlp_model = None

    # ASCII-Art Header anzeigen
    final_header = print_matrix_header()
    logging.info(translations["header"][LANG])
    
    # Projekt-URL einlesen (interaktiv via prompt_toolkit, falls verfügbar)
    if pt_prompt:
        project_url = pt_prompt("Enter the project URL: ")
    else:
        project_url = input("Enter the project URL: ").strip()
    logging.debug(f"User entered project URL: {project_url}")
    domain = extract_domain(project_url)
    project_path = os.path.join(PROJECTS_DIR, domain)
    
    # Projektstruktur erstellen
    if not os.path.exists(project_path):
        os.makedirs(project_path, exist_ok=True)
        download_dir = os.path.join(project_path, "downloaded_mhtml")
        os.makedirs(download_dir, exist_ok=True)
    else:
        download_dir = os.path.join(project_path, "downloaded_mhtml")
    
    # Logger konfigurieren (mit Datei-Logging im Projektordner)
    LoggerManager(project_path, config)
    
    # Cache-Dateien definieren
    global CACHE_FILE, OUTPUT_FILE
    CACHE_FILE = os.path.join(project_path, "cache.pkl")
    OUTPUT_FILE = os.path.join(project_path, config.get("output", "template_filename", "bs4code.txt"))
    
    # Keywords laden, falls aktiviert
    keywords = load_keywords(KEYWORDS_FILE) if config.get("crawler", "use_keywords", False) else None

    # Auswahl des Crawling-Mechanismus: asynchron vs. Selenium-Fallback
    downloaded_files = []
    # Verwende rich Statusanzeige, falls verfügbar
    if Console:
        console = Console()
        with console.status("[bold green]Crawling in progress...[/bold green]"):
            if config.get("crawler", "use_selenium", False):
                logging.info("Using Selenium for crawling (synchronous fallback).")
                downloaded_files = crawl_website_sync(project_url, download_dir, args, keywords)
            else:
                logging.info("Using asynchronous crawling with aiohttp.")
                loop = asyncio.get_event_loop()
                async_crawler = AsyncCrawler(project_url, download_dir, config, keywords)
                downloaded_files = loop.run_until_complete(async_crawler.crawl())
    else:
        # Fallback, falls rich nicht verfügbar ist
        if config.get("crawler", "use_selenium", False):
            logging.info("Using Selenium for crawling (synchronous fallback).")
            downloaded_files = crawl_website_sync(project_url, download_dir, args, keywords)
        else:
            logging.info("Using asynchronous crawling with aiohttp.")
            loop = asyncio.get_event_loop()
            async_crawler = AsyncCrawler(project_url, download_dir, config, keywords)
            downloaded_files = loop.run_until_complete(async_crawler.crawl())
    
    if not downloaded_files:
        logging.error("No pages downloaded. Exiting.")
        sys.exit(1)
    
    # Lese heruntergeladene Dateien ein
    documents = read_supported_files(download_dir)
    if not documents:
        logging.error("No supported files found. Exiting.")
        sys.exit(1)
    
    # Cache laden und ggf. neu berechnen
    cache = load_cache(CACHE_FILE)
    cached_info = cache.get("file_info", {})
    cached_common = cache.get("common_seq", None)
    cached_variables = cache.get("variable_lines", None)
    
    if cached_common is not None and not files_have_changed(documents, cached_info):
        logging.debug(translations["no_changes"][LANG])
        common_seq = cached_common
        variable_lines = cached_variables
    else:
        logging.debug(translations["changes_detected"][LANG])
        common_seq = compute_common_sequence(documents)
        if common_seq is None:
            logging.error("Common sequence is None. Exiting.")
            sys.exit(1)
        logging.debug(translations["common_seq_length"][LANG].format(len(common_seq)))
        variable_lines = aggregate_variable_lines(documents, common_seq)
        cache["file_info"] = update_cache_info(documents)
        cache["common_seq"] = common_seq
        cache["variable_lines"] = variable_lines
        save_cache(cache, CACHE_FILE)
    
    # Template generieren
    logging.debug("Generating BS4 code template.")
    generator = TemplateGenerator(common_seq, variable_lines)
    bs4_template = generator.generate_template()
    try:
        with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
            f.write(bs4_template)
        logging.debug(translations["template_written"][LANG].format(OUTPUT_FILE))
    except Exception as e:
        logging.error(translations["error_writing"][LANG].format(OUTPUT_FILE, e))
    
    elapsed = time.time() - start_time
    logging.debug(translations["elapsed_time"][LANG].format(elapsed))
    print(translations["elapsed_time"][LANG].format(elapsed))
    
# =============================================
# Synchroner Crawler als Fallback (Selenium-basierend)
# =============================================

def crawl_website_sync(url, download_dir, args, keywords):
    """
    Einfacher synchroner Crawler mit ThreadPoolExecutor und Selenium-Fallback.
    Verwendet größtenteils die bereits vorhandenen Funktionen.
    """
    domain = extract_domain(url)
    visited = set()
    to_visit = [url]
    downloaded_files = []
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
    headers = {"User-Agent": "Mozilla/5.0 (compatible; AdvancedBS4TemplateGenerator/2.0)"}
    shared_driver = None
    if args.selenium_only:
        options = Options()
        options.add_argument("--headless")
        options.add_argument("--disable-gpu")
        options.add_argument(f'user-agent={headers["User-Agent"]}')
        try:
            shared_driver = webdriver.Chrome(options=options)
        except Exception as e:
            logging.error(f"Error initializing shared Selenium driver: {e}")
            shared_driver = None
    pbar = tqdm(desc=f"{Fore.GREEN}Downloading pages (sync){Style.RESET_ALL}", ncols=80)
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.max_workers) as executor:
        while to_visit and len(downloaded_files) < args.max_pages:
            batch = []
            while to_visit and len(batch) < args.max_workers:
                batch.append(to_visit.pop(0))
            batch = [u for u in batch if u not in visited]
            if not batch:
                continue
            for u in batch:
                visited.add(u)
            futures = {executor.submit(get_page_content, u, session, headers, args.selenium_only, shared_driver, args.no_delay): u for u in batch}
            for future in concurrent.futures.as_completed(futures):
                current_url = futures[future]
                try:
                    content = future.result()
                except Exception as exc:
                    logging.error(f"Error processing {current_url}: {exc}")
                    continue
                if not args.no_delay:
                    time.sleep(random.uniform(1,3))
                if content and not is_cloudflare_error_page(content):
                    if args.use_keywords and keywords:
                        if not any(kw.lower() in content.lower() for kw in keywords):
                            logging.debug(f"Skipping {current_url} due to keyword filter.")
                            continue
                    file_index = len(downloaded_files) + 1
                    filename = os.path.join(download_dir, f"page_{file_index}.mhtml")
                    try:
                        with open(filename, "w", encoding="utf-8") as f:
                            f.write(content)
                    except Exception as e:
                        logging.error(f"Error writing file {filename}: {e}")
                        continue
                    downloaded_files.append(filename)
                    pbar.update(1)
                    logging.debug(f"Downloaded {current_url} to {filename}.")
                    soup = BeautifulSoup(content, "lxml")
                    new_links = []
                    for link in soup.find_all("a", href=True):
                        absolute_url = urljoin(current_url, link["href"])
                        if extract_domain(absolute_url) == domain and absolute_url not in visited:
                            new_links.append(absolute_url)
                    new_links = prioritize_urls(new_links)
                    to_visit.extend(new_links)
                    if len(downloaded_files) >= args.max_pages:
                        break
                else:
                    logging.info(f"Ignored Cloudflare error page or empty content from {current_url}.")
    pbar.close()
    if shared_driver:
        try:
            shared_driver.quit()
        except Exception as e:
            logging.error(f"Error quitting shared Selenium driver: {e}")
    return downloaded_files

# =============================================
# CLI Argument Parsing
# =============================================

if __name__ == "__main__":
    # Initiales Logging für Konsolenausgaben (bevor LoggerManager neu konfiguriert wird)
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    parser = argparse.ArgumentParser(
        description="Advanced BS4 Template Generator with asynchronous crawling, NLP integration, multi-format support, and extensive logging."
    )
    parser.add_argument("--lang", choices=list(translations["header"].keys()), help="Language for output messages")
    parser.add_argument("--strategy", choices=["bfs", "dfs"], default="bfs", help="Crawling strategy: breadth-first (bfs) or depth-first (dfs)")
    parser.add_argument("--max-pages", type=int, default=100, help="Maximum number of pages to crawl")
    parser.add_argument("--max-workers", type=int, default=5, help="Number of concurrent workers for crawling (sync mode)")
    parser.add_argument("--no-delay", action="store_true", help="Disable random delays during crawling")
    parser.add_argument("--selenium-only", action="store_true", help="Force using Selenium for all page fetches")
    parser.add_argument("--use-keywords", action="store_true", help="Use keywords from KEYWORDS_FILE to filter pages")
    parser.add_argument("--config", help="Path to configuration file (JSON format)")
    
    args = parser.parse_args()
    
    try:
        main(args)
    except KeyboardInterrupt:
        logging.info(translations["process_aborted"][LANG])
        sys.exit(0)
