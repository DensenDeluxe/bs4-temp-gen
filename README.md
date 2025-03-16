# BS4 Template Generator

![BS4 Template Generator](https://img.shields.io/badge/Python-3.x-blue.svg)
![BeautifulSoup](https://img.shields.io/badge/BeautifulSoup-4-green.svg)
![Selenium](https://img.shields.io/badge/Selenium-ChromeDriver-yellow.svg)
![License](https://img.shields.io/badge/License-MIT-lightgrey.svg)

## Overview
The **BS4 Template Generator** is an advanced web scraping utility that extracts common HTML structures from multiple webpages and generates reusable **BeautifulSoup 4** (BS4) templates. It integrates **Selenium** for bypassing Cloudflare protections and supports multiple scraping strategies.

## Features
- **Automated HTML structure extraction** using `BeautifulSoup4`.
- **Smart web crawling** with `requests` and `Selenium` fallback.
- **Cloudflare bypass support** via headless Chrome.
- **Multi-language support** (10+ languages).
- **Efficient caching** to prevent redundant downloads.
- **Logging and Debugging** with structured logs.
- **Customizable keyword-based scraping**.
- **Parallel downloading** with request retries.
- **BS4 template generation** for extracted data.

## Installation

### Requirements
Ensure you have **Python 3.7+** installed.

#### 1. Clone the repository
```bash
git clone https://github.com/DensenDeluxe/bs4-temp-gen.git
cd bs4-template-gen
```

#### 2. Install dependencies
```bash
pip install -r requirements.txt
```

#### 3. Install ChromeDriver (for Selenium support)
- Download ChromeDriver matching your **Chrome version** from [here](https://sites.google.com/chromium.org/driver/).
- Place it in a directory included in your `PATH` or specify its location.

## Usage

### Running the Script
To generate a BS4 template, simply run:
```bash
python bs4-temp-gen.py
```

### Interactive Mode
The script will prompt you for a **target URL**:
```plaintext
Please enter the project URL: https://example.com
```
The generator will automatically:
1. Crawl the provided URL.
2. Extract common HTML structures.
3. Generate a reusable `BeautifulSoup` parsing template.

### Output
Generated templates are saved in the **project directory**:
```plaintext
projects/<domain>/bs4code.txt
```

## Example
A generated **BS4 parsing template**:
```python
from bs4 import BeautifulSoup

def extract_relevant_data(html_content):
    soup = BeautifulSoup(html_content, 'lxml')
    title = soup.find("h1", class_="page-title").get_text(strip=True)
    price = soup.find("span", class_="price").get_text(strip=True)
    return {"title": title, "price": price}
```

## Configuration

### Changing Crawling Strategy
By default, the script uses **BFS (Breadth-First Search)**. You can switch to **DFS (Depth-First Search)** by modifying:
```python
downloaded_files = crawl_website(project_url, strategy="dfs")
```

### Customizing Headers
Modify headers inside `get_page_content()`:
```python
headers = {"User-Agent": "Mozilla/5.0 (compatible; BS4TemplateGenerator/1.0)"}
```

## Contributing
1. **Fork** the repository.
2. Create a **feature branch** (`git checkout -b feature-name`).
3. Commit your changes (`git commit -m 'Add new feature'`).
4. Push to your branch (`git push origin feature-name`).
5. Open a **Pull Request**.

## License
This project is licensed under the **MIT License**.


---
Made with ❤️ by *Daniel.

