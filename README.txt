# BS4-Temp-Gen 🚀

> **"Ever dreamed of effortlessly extracting templates from websites? Now you can!"** 🎭

[![Python](https://img.shields.io/badge/Python-3.x-blue.svg)](https://www.python.org/)  
[![BeautifulSoup](https://img.shields.io/badge/BeautifulSoup-🌿-green.svg)](https://www.crummy.com/software/BeautifulSoup/)  
[![Selenium](https://img.shields.io/badge/Selenium-🕷-blue.svg)](https://www.selenium.dev/)

### What Does This Do? 🤔
✅ **Scrapes and Downloads** websites 🕵️  
✅ **Handles Cloudflare Protection** 🛡  
✅ **Finds Common HTML Structure** 🔬  
✅ **Generates a Reusable BeautifulSoup Template** 🏗  
✅ **Uses AI-powered LCS Matching** 🤖  
✅ **Supports Multiple Languages** 🌍  
✅ **Caches Results for Speed** ⚡  

---

## 🛠 Setup & Installation

1️⃣ Clone the repository  
```sh
git clone https://github.com/yourusername/bs4-temp-gen.git
cd bs4-temp-gen
```
2️⃣ Install dependencies  
```sh
pip install -r requirements.txt
```
3️⃣ Run the script  
```sh
python bs4-temp-gen.py
```

---

## 🚀 How It Works
1️⃣ **User enters a URL**  
2️⃣ **It downloads pages & detects Cloudflare protections**  
3️⃣ **Extracts static vs. variable content**  
4️⃣ **Generates a reusable `BeautifulSoup` template**  

🎥 **It's like magic!** 🎩✨

---

## ⚙️ Example Output
```python
from bs4 import BeautifulSoup

def extract_relevant_data(html_content):
    soup = BeautifulSoup(html_content, 'lxml')
    return soup.get_text(separator=" ", strip=True)

if __name__ == '__main__':
    with open("example.mhtml", "r", encoding="utf-8", errors="ignore") as f:
        html = f.read()
    data = extract_relevant_data(html)
    print(data)
```

---

## 📜 License
MIT License - Free for everyone! 🎉

---

# 🎨 Deutsch 🇩🇪

## `BS4-Temp-Gen` 🚀

> **"Du wolltest schon immer kinderleicht Website-Templates extrahieren? Jetzt geht’s!"** 🎭

[![Python](https://img.shields.io/badge/Python-3.x-blue.svg)](https://www.python.org/)  
[![BeautifulSoup](https://img.shields.io/badge/BeautifulSoup-🌿-green.svg)](https://www.crummy.com/software/BeautifulSoup/)  
[![Selenium](https://img.shields.io/badge/Selenium-🕷-blue.svg)](https://www.selenium.dev/)

### Was kann das? 🤔
✅ **Lädt Webseiten herunter** 🕵️  
✅ **Umgeht Cloudflare-Schutz** 🛡  
✅ **Findet wiederkehrende HTML-Elemente** 🔬  
✅ **Erstellt `BeautifulSoup`-Vorlagen** 🏗  
✅ **Nutzen KI-basierte LCS-Analyse** 🤖  
✅ **Mehrsprachige Unterstützung** 🌍  
✅ **Cache für Turbo-Geschwindigkeit** ⚡  

---

## 🛠 Einrichtung & Installation

1️⃣ Repository klonen  
```sh
git clone https://github.com/deinusername/bs4-temp-gen.git
cd bs4-temp-gen
```
2️⃣ Abhängigkeiten installieren  
```sh
pip install -r requirements.txt
```
3️⃣ Skript ausführen  
```sh
python bs4-temp-gen.py
```

---

## 🚀 Wie funktioniert’s?
1️⃣ **Gib eine URL ein**  
2️⃣ **Seiten werden geladen & Cloudflare erkannt**  
3️⃣ **Extraktion von statischem & variablem Content**  
4️⃣ **Erzeugung einer `BeautifulSoup`-Vorlage**  

🎥 **Wie Zauberei!** 🎩✨

---

## ⚙️ Beispielcode
```python
from bs4 import BeautifulSoup

def extract_relevant_data(html_content):
    soup = BeautifulSoup(html_content, 'lxml')
    return soup.get_text(separator=" ", strip=True)

if __name__ == '__main__':
    with open("example.mhtml", "r", encoding="utf-8", errors="ignore") as f:
        html = f.read()
    data = extract_relevant_data(html)
    print(data)
```

---

## 📜 Lizenz
MIT Lizenz - Frei für alle! 🎉
