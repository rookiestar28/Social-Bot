from playwright.async_api import async_playwright
from playwright_stealth import Stealth 
from config import settings
import os
import logging

logger = logging.getLogger(__name__)

class BrowserEngine:
    def __init__(self):
        self.playwright = None
        self.browser = None
        self.context = None
        self.page = None
        self.stealth = Stealth() # Instantiate Stealth
        
        # Ensure directory exists
        os.makedirs(settings.user_data_dir, exist_ok=True)
        self.auth_path = os.path.join(settings.user_data_dir, "auth.json")

    async def start(self):
        logger.info("Launching browser...")
        self.playwright = await async_playwright().start()
        
        # Load storage state if exists
        storage_state = self.auth_path if os.path.exists(self.auth_path) else None
        
        # Enhanced Launch Args for Anti-Detection
        self.browser = await self.playwright.chromium.launch(
            headless=settings.headless,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
                "--disable-infobars",
                "--disable-extensions",
                "--disable-dev-shm-usage",
            ]
        )
        
        self.context = await self.browser.new_context(
            storage_state=storage_state,
            viewport={"width": 1280, "height": 800},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            locale="zh-TW"
        )
        
        self.page = await self.context.new_page()
        
        # Apply Stealth Actions
        await self.stealth.apply_stealth_async(self.page)
        logger.info("🛡️  Stealth Mode Activated.")

    async def stop(self):
        if self.context:
            await self.context.storage_state(path=self.auth_path)
            await self.context.close()
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()
