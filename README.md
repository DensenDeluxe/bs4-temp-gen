# BS4 Template Generator (bs4-temp-gen)

![Python](https://img.shields.io/badge/Python-3.x-blue.svg) ![BeautifulSoup](https://img.shields.io/badge/BeautifulSoup-4-green.svg) ![Selenium](https://img.shields.io/badge/Selenium-WebScraping-yellow.svg)

## Overview
**bs4-temp-gen** is an advanced web scraping and template generation tool that automates crawling, extracting, and analyzing HTML structures from web pages. It utilizes **BeautifulSoup**, **Selenium**, and **Requests** to handle both static and dynamic content, generating reusable BS4 parsing templates based on recurring patterns found across multiple pages.

## Features
- **Automated Web Crawling:** Supports breadth-first (BFS) and depth-first (DFS) crawling strategies.
- **Parallel Processing:** Multithreading with configurable workers for faster data collection.
- **Cloudflare Bypass:** Detects and circumvents Cloudflare-protected pages using Selenium.
- **Content Extraction:** Identifies and normalizes common and variable HTML patterns.
- **Configurable Keyword Filtering:** Filters relevant pages using a customizable keyword list.
- **Caching Mechanism:** Saves and reuses previous results to optimize performance.
- **Customizable Output:** Generates structured BS4 templates for easy data extraction.
- **Verbose Logging:** Adjustable console verbosity levels (`off`, `v`, `vv`, `vvv`, `infinite`).

## Installation
### Prerequisites
Ensure you have the following installed:
- Python 3.x
- Google Chrome & ChromeDriver (for Selenium)
- Required Python packages (install with `pip`)

### Setup
Clone the repository:
```bash
git clone https://github.com/DensenDeluxe/bs4-temp-gen.git
cd bs4-temp-gen
```

Install dependencies:
```bash
pip install -r requirements.txt
```

## Usage
Run the script with customizable options:
```bash
python bs4-temp-gen.py --output template.py --strategy bfs --max-pages 100 --max-workers 5
```

### Command-Line Arguments
| Argument | Description | Default |
|----------|-------------|---------|
| `--strategy` | Crawling strategy (`bfs` or `dfs`) | `bfs` |
| `--max-pages` | Maximum pages to crawl (`-1` for infinite) | `100` |
| `--max-depth` | Maximum crawl depth (`-1` for infinite) | `-1` |
| `--max-workers` | Number of concurrent threads | `5` |
| `--no-delay` | Disable random request delays | `False` |
| `--selenium-only` | Force Selenium for all requests | `False` |
| `--use-keywords` | Filter pages based on `bs4-search-items.txt` | `False` |
| `--page-timeout` | HTTP request timeout in seconds | `10` |
| `--selenium-timeout` | Selenium page load timeout in seconds | `15` |
| `--retry-count` | Number of retry attempts for failed requests | `3` |
| `--no-cache` | Disable caching and force re-crawl | `False` |
| `--project-dir` | Directory for storing project data | `projects` |
| `--keyword-file` | Keyword list file | `bs4-search-items.txt` |
| `--output` | Output file for BS4 template | `bs4code.txt` |
| `--verbose` | Console output verbosity (`off`, `v`, `vv`, `vvv`, `infinite`) | `vvv` |

### Example Usage
#### Basic Crawling
```bash
python bs4-temp-gen.py --output template.py --strategy bfs
```

#### Crawling with Keywords Filtering
```bash
python bs4-temp-gen.py --use-keywords --keyword-file bs4-search-items.txt
```

#### Selenium-only Crawling
```bash
python bs4-temp-gen.py --selenium-only
```

#### High-Speed Parallel Crawling
```bash
python bs4-temp-gen.py --max-workers 10 --no-delay
```

## Output
Upon completion, the script generates a structured BS4 parsing template, similar to:
```python
"""
Automatically generated BS4 template

=== Common (static) HTML structure from all supported files ===
<div class="product">
    <h1 class="product-title">Product Name</h1>
    <span class="price">$XX.XX</span>
</div>

=== Variable sections (data that differ) ===
# <h1 class="product-title">Different Product Name</h1>
# <span class="price">$YY.YY</span>

=== Final extraction template ===
from bs4 import BeautifulSoup

def extract_relevant_data(html_content):
    soup = BeautifulSoup(html_content, 'lxml')
    title = soup.find("h1", class_="product-title").get_text(strip=True)
    price = soup.find("span", class_="price").get_text(strip=True)
    return title, price
"""
```

## Logging & Debugging
Enable detailed logs with:
```bash
python bs4-temp-gen.py --verbose vvv
```

Log levels:
- **off** – Minimal output
- **v** – Warnings and errors only
- **vv** – Informational messages
- **vvv** – Debug-level details
- **infinite** – All logs with no filtering

## File Structure
```
bs4-temp-gen/
│── bs4-temp-gen.py      # Main script
│── bs4-search-items.txt # List of keywords for filtering
│── requirements.txt     # Required Python packages
│── projects/            # Directory for storing crawled data
└── README.md            # Documentation
```

## Contributing
Pull requests and feature suggestions are welcome! Follow these steps to contribute:
1. Fork the repository
2. Create a new branch (`git checkout -b feature-branch`)
3. Commit your changes (`git commit -m "Add new feature"`)
4. Push to your fork (`git push origin feature-branch`)
5. Create a pull request

## License
This project is licensed under the MIT License. See `LICENSE` for details.

## Author
[DensenDeluxe](https://github.com/DensenDeluxe)

