import os
import json
import uuid
import base64
import logging
import asyncio
from typing import Dict, List, Any, Optional
from email.mime.text import MIMEText

import numpy as np
import pandas as pd
from bs4 import BeautifulSoup
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings
from fastapi import FastAPI, BackgroundTasks, HTTPException

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium_stealth import stealth

from openai import AsyncOpenAI
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# =====================================================================
# 1. CONFIGURATION SCHEMAS & SETTINGS
# =====================================================================

class Settings(BaseSettings):
    ENVIRONMENT: str = "production"
    OPENAI_API_KEY: str = Field(default="sk-placeholder")
    GOOGLE_CLIENT_ID: str = Field(default="google-client-id-placeholder")
    GOOGLE_CLIENT_SECRET: str = Field(default="google-client-secret-placeholder")
    GOOGLE_REFRESH_TOKEN: str = Field(default="google-refresh-token-placeholder")
    SENDER_EMAIL: str = Field(default="sender@example.com")
    SELENIUM_HEADLESS: bool = True
    LEAD_THRESHOLD: float = 0.65
    SCORING_WEIGHTS: Dict[str, float] = {
        "tech_stack_match": 0.4,
        "hiring_activity": 0.3,
        "press_presence": 0.3
    }

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

settings = Settings()

# =====================================================================
# 2. WEB SCRAPING MODULE
# =====================================================================

logger = logging.getLogger("AegisOutreach")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")

class WebScraper:
    def __init__(self, headless: bool = True) -> None:
        self.headless = headless

    def _init_driver(self) -> webdriver.Chrome:
        options = Options()
        if self.headless:
            options.add_argument("--headless=new")
        options.add_argument("--disable-gpu")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option("useAutomationExtension", False)
        
        driver = webdriver.Chrome(options=options)
        stealth(
            driver,
            languages=["en-US", "en"],
            vendor="Google Inc.",
            platform="Win32",
            webgl_vendor="Intel Inc.",
            renderer="Intel Iris OpenGL Engine",
            fix_hairline=True,
        )
        return driver

    def scrape_domain(self, domain: str) -> Dict[str, Any]:
        driver: Optional[webdriver.Chrome] = None
        url = f"https://{domain}" if not domain.startswith("http") else domain
        data: Dict[str, Any] = {
            "domain": domain,
            "tech_stack_match": 0.0,
            "hiring_activity": 0.0,
            "press_presence": 0.0,
            "raw_text": ""
        }
        try:
            driver = self._init_driver()
            driver.set_page_load_timeout(30)
            driver.get(url)
            
            page_source = driver.page_source
            soup = BeautifulSoup(page_source, "lxml")
            
            text_content = soup.get_text(separator=" ", strip=True)
            data["raw_text"] = text_content[:5000]
            
            tech_keywords = ["python", "fastapi", "react", "kubernetes", "aws", "docker", "typescript"]
            lower_text = text_content.lower()
            tech_hits = sum(1 for kw in tech_keywords if kw in lower_text)
            data["tech_stack_match"] = min(tech_hits / 3.0, 1.0)
            
            hiring_keywords = ["careers", "we're hiring", "open positions", "job openings", "join our team"]
            data["hiring_activity"] = 1.0 if any(hk in lower_text for hk in hiring_keywords) else 0.0
            
            press_keywords = ["press", "news", "announces", "media kit", "blog"]
            data["press_presence"] = 1.0 if any(pk in lower_text for pk in press_keywords) else 0.0

        except Exception as e:
            logger.error(f"Error scraping domain {domain}: {str(e)}")
        finally:
            if driver:
                try:
                    driver.quit()
                except Exception as qe:
                    logger.error(f"Error terminating WebDriver session for {domain}: {str(qe)}")
        return data

# =====================================================================
# 3. DATA PROCESSING & MATRIX SCORING MODULE
# =====================================================================

class LeadProcessor:
    def __init__(self, weights: Dict[str, float], threshold: float) -> None:
        self.weights = weights
        self.threshold = threshold

    def process_leads(self, raw_leads: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        if not raw_leads:
            return []

        try:
            df = pd.DataFrame(raw_leads)
            
            df["domain"] = df["domain"].astype(str).str.lower().str.strip()
            df.drop_duplicates(subset=["domain"], inplace=True)
            
            for col in ["tech_stack_match", "hiring_activity", "press_presence"]:
                if col not in df.columns:
                    df[col] = 0.0
                else:
                    df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0.0)

            w_tech = self.weights.get("tech_stack_match", 0.4)
            w_hire = self.weights.get("hiring_activity", 0.3)
            w_press = self.weights.get("press_presence", 0.3)

            scores = (
                df["tech_stack_match"] * w_tech +
                df["hiring_activity"] * w_hire +
                df["press_presence"] * w_press
            )
            
            df["priority_score"] = np.clip(scores, 0.0, 1.0)
            
            filtered_df = df[df["priority_score"] >= self.threshold]
            return filtered_df.to_dict(orient="records")
        except Exception as e:
            logger.error(f"Error processing lead vector pipeline: {str(e)}")
            return []

# =====================================================================
# 4. AI GENERATION AGENT
# =====================================================================

class OutreachAIAgent:
    def __init__(self, api_key: str) -> None:
        self.client = AsyncOpenAI(api_key=api_key)

    async def generate_outreach(self, lead_data: Dict[str, Any]) -> Dict[str, str]:
        domain = lead_data.get("domain", "target company")
        raw_text = lead_data.get("raw_text", "")

        prompt = f"""
        You are an elite B2B sales and engineering consultant. Analyze the following corporate intelligence extracted from domain: {domain}.
        Raw text snippet: {raw_text[:2000]}

        Draft a hyper-personalized, non-template cold outreach email.
        Return a strictly valid JSON object with keys "subject" and "body". No markdown wrappers, raw JSON only.
        """

        try:
            response = await self.client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": "You are a professional B2B outreach copywriter. Output only valid JSON."},
                    {"role": "user", "content": prompt}
                ],
                response_format={"type": "json_object"},
                temperature=0.7
            )
            content = response.choices[0].message.content
            parsed = json.loads(content)
            return {
                "subject": parsed.get("subject", "Engineering Collaboration"),
                "body": parsed.get("body", "Hello, I noticed your tech stack and wanted to connect.")
            }
        except Exception as e:
            logger.error(f"Error generating AI outreach for {domain}: {str(e)}")
            return {
                "subject": f"Engineering optimization for {domain}",
                "body": f"Hello team at {domain}, we build high-performance systems and would love to connect."
            }

# =====================================================================
# 5. GMAIL DELIVERY SERVICE
# =====================================================================

class GmailServiceManager:
    def __init__(self, client_id: str, client_secret: str, refresh_token: str, sender_email: str) -> None:
        self.creds = Credentials(
            token=None,
            refresh_token=refresh_token,
            client_id=client_id,
            client_secret=client_secret,
            token_uri="https://oauth2.googleapis.com/token"
        )
        self.sender_email = sender_email

    def _get_service(self) -> Any:
        return build("gmail", "v1", credentials=self.creds)

    def _create_message(self, to: str, subject: str, body: str) -> dict:
        message = MIMEText(body)
        message["to"] = to
        message["from"] = self.sender_email
        message["subject"] = subject
        raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode("utf-8")
        return {"raw": raw_message}

    async def send_email(self, to: str, subject: str, body: str) -> bool:
        loop = asyncio.get_running_loop()
        max_retries = 3
        backoff_factor = 2.0

        for attempt in range(max_retries):
            try:
                def _execute_send() -> None:
                    service = self._get_service()
                    msg = self._create_message(to, subject, body)
                    service.users().messages().send(userId="me", body=msg).execute()

                await loop.run_in_executor(None, _execute_send)
                logger.info(f"Email successfully sent to {to}")
                return True
            except HttpError as he:
                logger.warning(f"HTTP error sending email to {to} (attempt {attempt+1}/{max_retries}): {he}")
                if attempt == max_retries - 1:
                    logger.error(f"Failed to send email to {to} after {max_retries} attempts.")
                    return False
                await asyncio.sleep(backoff_factor ** attempt)
            except Exception as e:
                logger.error(f"Unexpected error sending email to {to}: {e}")
                return False
        return False

# =====================================================================
# 6. FASTAPI BOOTSTRAP & PIPELINE ORCHESTRATION
# =====================================================================

app = FastAPI(
    title="Aegis Outreach Engine",
    version="1.0.0",
    description="Autonomous AI-Driven Market Intelligence & Cold Outreach System"
)

class OutreachRequest(BaseModel):
    domains: List[str] = Field(..., description="List of target corporate domains to process.")
    recipient_emails: Dict[str, str] = Field(..., description="Mapping of domain to target contact email.")

class OutreachResponse(BaseModel):
    job_id: str
    status: str
    message: str

async def run_outreach_pipeline(job_id: str, domains: List[str], recipient_emails: Dict[str, str]) -> None:
    logger.info(f"Execution job [{job_id}] initialized for targets: {domains}")
    
    scraper = WebScraper(headless=settings.SELENIUM_HEADLESS)
    processor = LeadProcessor(weights=settings.SCORING_WEIGHTS, threshold=settings.LEAD_THRESHOLD)
    ai_agent = OutreachAIAgent(api_key=settings.OPENAI_API_KEY)
    gmail_service = GmailServiceManager(
        client_id=settings.GOOGLE_CLIENT_ID,
        client_secret=settings.GOOGLE_CLIENT_SECRET,
        refresh_token=settings.GOOGLE_REFRESH_TOKEN,
        sender_email=settings.SENDER_EMAIL
    )

    try:
        loop = asyncio.get_running_loop()
        raw_leads = []
        
        # Non-blocking parallel scraping via run_in_executor offloading
        for domain in domains:
            try:
                lead_data = await loop.run_in_executor(None, scraper.scrape_domain, domain)
                raw_leads.append(lead_data)
            except Exception as se:
                logger.error(f"Scraping stage exception for {domain}: {se}")

        if not raw_leads:
            logger.warning(f"Job [{job_id}] finished early: No raw leads harvested.")
            return

        # Vector processing execution offloaded to executor
        qualified_leads = await loop.run_in_executor(None, processor.process_leads, raw_leads)
        logger.info(f"Job [{job_id}] completed evaluation. Qualified leads: {len(qualified_leads)}/{len(domains)}")

        # Asynchronous generation and dispatch loop
        for lead in qualified_leads:
            dom = lead.get("domain")
            target_email = recipient_emails.get(dom)
            if not target_email:
                logger.warning(f"Recipient mapping missing for domain {dom}. Skipping delivery.")
                continue

            try:
                outreach_content = await ai_agent.generate_outreach(lead)
                subject = outreach_content["subject"]
                body = outreach_content["body"]

                await gmail_service.send_email(to=target_email, subject=subject, body=body)
                logger.info(f"Outreach workflow completed for domain: {dom}")
            except Exception as ie:
                logger.error(f"Outreach generation/dispatch exception for domain {dom}: {ie}")

    except Exception as e:
        logger.error(f"Uncaught failure in job execution [{job_id}]: {str(e)}")

@app.post("/api/v1/outreach/run", response_model=OutreachResponse)
async def trigger_outreach(payload: OutreachRequest, background_tasks: BackgroundTasks) -> OutreachResponse:
    if not payload.domains:
        raise HTTPException(status_code=400, detail="Domain list must not be empty.")
        
    job_id = str(uuid.uuid4())
    background_tasks.add_task(
        run_outreach_pipeline,
        job_id=job_id,
        domains=payload.domains,
        recipient_emails=payload.recipient_emails
    )
    return OutreachResponse(
        job_id=job_id,
        status="accepted",
        message="Aegis Outreach background execution pipeline started successfully."
    )

@app.get("/health")
async def health_check() -> Dict[str, str]:
    return {"status": "healthy", "service": "Aegis Outreach Unified Platform"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("aegis_outreach:app", host="0.0.0.0", port=8000, reload=True)
