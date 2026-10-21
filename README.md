![Aegis Outreach Banner](https://images.pexels.com/photos/3183150/pexels-photo-3183150.jpeg?auto=compress&cs=tinysrgb&w=1260&h=750&dpr=2)

# Aegis Outreach
### High-Performance Asynchronous Intelligence Scraping, Vectorized Scoring, & Automated Dispatch Orchestrator

---

## 📜 The Myth, The Legend, The Backronym

At first glance, **Aegis Outreach** sounds like a high-budget, enterprise-grade cybersecurity initiative engineered by defense contractors to shield a global Fortune 500 brand's outbound communication reputation. 

In reality, it is a deeply engineered, meticulously crafted backronym for:

> **A**utonomous **E**ngine for **G**athering **I**ntelligence & **S**ending **S**ignals

Let’s be entirely transparent: the lead architect spent considerably more time wrestling with ancient Greek mythology dictionaries to transform "Aegis" (the legendary shield of Zeus and Athena) into an engineering backronym than it took to fight Selenium's anti-bot evasions and headless Chrome driver flags. While Zeus used his Aegis to inspire awe and strike fear, this **Aegis** ensures your event loop never blocks while harvesting high-value corporate leads and orchestrating transactional dispatches.

---

## 🏗️ Core Architecture & The Non-Blocking Concurrency Flow

Aegis Outreach is built on top of **FastAPI** (`main.py`) to serve as an ultra-fast, asynchronous API gateway. However, real-world outreach engines must handle heavy, blocking, CPU- and I/O-intensive operations: running headless browser instances via Selenium, parsing massive HTML trees with BeautifulSoup4, and processing multi-column array transformations across Pandas DataFrames and NumPy arrays.

If executed naively inside an async request handler, these synchronous tasks freeze Python's single-threaded event loop, dropping incoming concurrent HTTP connections and stalling outbound network requests.

To mitigate this, Aegis Outreach decouples thread-bound synchronous operations from the primary asynchronous loop using Python’s native `asyncio.to_thread()` execution pool.

![Server Infrastructure](https://images.pexels.com/photos/2881232/pexels-photo-2881232.jpeg?auto=compress&cs=tinysrgb&w=1260&h=750&dpr=2)

### Async Execution Flowchart

```
┌──────────────────────────────────────────────────────────────────────────────────┐
│                                 INCOMING HTTP REQUEST                            │
│                      (POST /api/v1/orchestrate-outreach)                         │
└────────────────────────────────────────┬─────────────────────────────────────────┘
                                         │
                                         ▼
┌──────────────────────────────────────────────────────────────────────────────────┐
│                            FastAPI Async Event Loop                              │
│                                   (main.py)                                      │
└───────────────────┬──────────────────────────────────────────────┬───────────────┘
                    │                                              │
        [Non-Blocking Dispatch]                               [Async Network IO]
                    │                                              │
                    ▼                                              ▼
┌─────────────────────────────────────────┐      ┌─────────────────────────────────┐
│        ThreadPoolWorker Pool            │      │       Gmail API Client          │
│       (via asyncio.to_thread)           │      │   (httpx / Google OAuth2)       │
├─────────────────────────────────────────┤      ├─────────────────────────────────┤
│ 1. Selenium-Stealth DOM Scraping        │      │ 1. Await OAuth Token Refresh    │
│ 2. BeautifulSoup4 (lxml) Tree Extract   │      │ 2. Transmit Base64-URL Payload  │
│ 3. Pandas / NumPy Vectorized Scoring    │      │ 3. Exponential Backoff Retry    │
└───────────────────┬─────────────────────┘      └────────────────┬────────────────┘
                    │                                             │
                    └──────────────────────┬──────────────────────┘
                                           │
                                           ▼
┌──────────────────────────────────────────────────────────────────────────────────┐
│                             HTTP 200 OK RESPONSE                                 │
│                   { status: "success", leads_processed: N }                      │
└──────────────────────────────────────────────────────────────────────────────────┘
```

---

## 🛠️ Deep-Dive Technical Mechanics

![Cyber Security Interface](https://images.pexels.com/photos/5380664/pexels-photo-5380664.jpeg?auto=compress&cs=tinysrgb&w=1260&h=750&dpr=2)

<details>
<summary><b>1. Data Harvesting Engine (Selenium-Stealth + BeautifulSoup4)</b></summary>

<br>

The scraping pipeline operates under a strict **rapid-exit browser model** designed to minimize memory footprint and eliminate headless detection vectors.

- **Anti-Bot Evasion**: Utilizes `selenium-stealth` to override `navigator.webdriver` flags, mask user-agent profiles, patch WebGL vendor strings, and randomize window dimensions.
- **Immediate Resource Freeing**: Rather than navigating through multi-step browser DOM selections (which keeps heavy Chromedriver processes alive in memory), Aegis retrieves the raw `driver.page_source` string in a single synchronous cycle.
- **lxml Ingestion**: The raw HTML string is passed directly to `BeautifulSoup(page_source, 'lxml')`. The browser instance is immediately torn down (`driver.quit()`), delegating tree traversing and CSS/XPath parsing to C-optimized CPython modules.

```python
# Conceptual snippet from orchestrator worker
import asyncio
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium_stealth import stealth

def harvest_raw_dom(target_url: str) -> str:
    chrome_options = Options()
    chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")
    
    driver = webdriver.Chrome(options=chrome_options)
    stealth(
        driver,
        languages=["en-US", "en"],
        vendor="Google Inc.",
        platform="Win32",
        webgl_vendor="Intel Inc.",
        renderer="Intel Iris OpenGL Engine",
        fix_hairline=True,
    )
    
    try:
        driver.get(target_url)
        return driver.page_source
    finally:
        driver.quit()

async def get_parsed_html(target_url: str) -> BeautifulSoup:
    raw_html = await asyncio.to_thread(harvest_raw_dom, target_url)
    return BeautifulSoup(raw_html, "lxml")
```
</details>

<details>
<summary><b>2. Vectorized Intelligence Pipelines (Pandas + NumPy Matrix Priorities)</b></summary>

<br>

Raw scraped leads are converted into structured Pandas DataFrames to perform vectorized cleanups and calculate lead scores without looping over Python dictionaries.

- **Vectorized Cleaning**: Replaces null structures, standardizes email text formatting, strips trailing domains, and normalizes corporate names using string vector operations (`df['company'].str.strip()`).
- **NumPy Matrix Prioritization**: Rather than executing conditional `if/else` logic per record, Aegis uses `np.select` and matrix dot-products (`np.dot`) to generate scaling priority tiers (e.g., matching keywords, domain authority signals, and employee size thresholds).

```python
import numpy as np
import pandas as pd

def compute_lead_scores(df: pd.DataFrame) -> pd.DataFrame:
    # Standardize string fields
    df['email'] = df['email'].str.lower().str.strip()
    df['company'] = df['company'].str.title().str.strip()

    # Rule-based conditions for prioritization matrix
    conditions = [
        (df['employee_count'] > 500) & (df['verified_domain'] == True),
        (df['employee_count'] > 100) & (df['verified_domain'] == True),
        (df['verified_domain'] == True)
    ]
    
    choices = [100, 75, 50]
    
    # Assign baseline scoring via vectorized selection
    df['base_score'] = np.select(conditions, choices, default=10)
    
    # Vectorized multi-factor weighting using np.dot
    weights = np.array([0.6, 0.4])
    feature_matrix = df[['base_score', 'engagement_index']].values
    df['final_priority_score'] = np.dot(feature_matrix, weights)
    
    return df.sort_values(by='final_priority_score', ascending=False)
```
</details>

<details>
<summary><b>3. Secure Delivery Engine (Google API Client + OAuth2)</b></summary>

<br>

Once intelligence payloads are compiled, the delivery subsystem interfaces directly with the Gmail API via official OAuth2 client libraries.

- **Base64-URL MIME Encoding**: Constructs RFC 2822 compliant MIME messages using Python's `email.mime` modules and translates them into URL-safe Base64 encoded strings (`base64.urlsafe_b64encode`).
- **Resilient Delivery Cycles**: Outbound REST calls are wrapped with automated exponential backoff retries using `httpx` or Google API's built-in execution handlers to gracefully bypass HTTP 429 (Rate Limit Exceeded) and transient 5xx server responses.

```python
import base64
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from googleapiclient.discovery import build

def create_encoded_message(sender: str, to: str, subject: str, body_html: str) -> dict:
    message = MIMEMultipart("alternative")
    message["to"] = to
    message["from"] = sender
    message["subject"] = subject
    
    part = MIMEText(body_html, "html")
    message.attach(part)
    
    raw_bytes = message.as_bytes()
    encoded_message = base64.urlsafe_b64encode(raw_bytes).decode("utf-8")
    return {"raw": encoded_message}

async def send_outbound_email(service_credentials, sender: str, to: str, subject: str, body: str):
    service = build("gmail", "v1", credentials=service_credentials)
    payload = create_encoded_message(sender, to, subject, body)
    
    # Non-blocking thread execution for API call
    response = await asyncio.to_thread(
        service.users().messages().send(userId="me", body=payload).execute
    )
    return response
```
</details>

---

## 🚀 Local Deployment & Production Run

Follow these precise steps to deploy and run **Aegis Outreach** in your local environment.

### 1. Clone the Repository

```bash
git clone https://github.com/rayaantasnim/Aegis-Outreach.git
cd Aegis-Outreach
```

### 2. Create and Activate a Virtual Environment

On macOS/Linux:
```bash
python3 -m venv venv
source venv/bin/activate
```

On Windows (PowerShell):
```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

### 3. Install Core Production Dependencies

Execute the following command to install all required libraries:

```bash
pip install fastapi uvicorn selenium selenium-stealth beautifulsoup4 lxml pandas numpy google-api-python-client google-auth-oauthlib pydantic-settings httpx
```

### 4. Launch the ASGI Production Server

Start the application with standard auto-reload flags for development:

```bash
uvicorn main:app --reload
```

The service will spin up on `http://127.0.0.1:8000`. You can inspect the automatically generated Swagger API documentation by navigating to `http://127.0.0.1:8000/docs`.

---

<hr> <center>
<em>Authorized by Rayaan Tasnim </em><br>
© All rights Reserved
</center>
