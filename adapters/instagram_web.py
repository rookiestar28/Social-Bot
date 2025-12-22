from .base import BaseAdapter
from config import settings
from . import selectors
import logging
import asyncio
import random
import base64

logger = logging.getLogger(__name__)

class InstagramAdapter(BaseAdapter):
    def __init__(self, browser_engine):
        self.browser = browser_engine
        self.base_url = "https://www.instagram.com"

    async def _human_delay(self, min_s=1, max_s=3):
        delay = random.uniform(min_s, max_s)
        await asyncio.sleep(delay)

    async def login(self):
        page = self.browser.page
        logger.info(f"Navigating to {self.base_url}...")
        await page.goto(self.base_url)
        await self._human_delay(2, 4)

        # IG Login Detection
        try:
            # Check for Home icon
            await page.locator(selectors.IG_NAV_HOME).wait_for(state="visible", timeout=5000)
            logger.info("✅ (Instagram) Session valid. Logged in.")
        except:
            logger.warning("⚠️  (Instagram) Login required.")
            if settings.headless:
                raise Exception("Cannot login in Headless mode. Switch to HEADLESS=False.")
            
            logger.info("👉 Please log in manually in the browser window...")
            
            # Wait for user to complete login
            try:
                # 10 mins wait
                await page.locator(selectors.IG_NAV_HOME).wait_for(state="visible", timeout=600000)
                logger.info("✅ Login detected! Saving state...")
                await self.browser.context.storage_state(path=self.browser.auth_path)
                logger.info("   Cookie saved.")
            except Exception as e:
                logger.error("Login timeout.")
                raise e

    async def get_feed(self):
        page = self.browser.page
        posts_data = []

        logger.info("👀 Scanning Instagram feed...")
        # Scroll
        for _ in range(3):
            await page.mouse.wheel(0, 800)
            await self._human_delay(1, 2)
        
        # Select articles
        articles = page.locator(selectors.IG_POST_ARTICLE)
        count = await articles.count()
        logger.info(f"Found {count} posts in view.")
        
        # Debug: If 0 posts, try to dump what's on the page
        if count == 0:
            logger.warning("   DEBUG: Checking alternative selectors...")
            for alt_sel in ["article", "div[role='article']", "div[class*='Post']", "div[class*='Feed']"]:
                alt_count = await page.locator(alt_sel).count()
                logger.info(f"   - {alt_sel}: {alt_count} matches")
        
        for i in range(count):
            article = articles.nth(i)
            # IG posts structure is complex. We try to get caption text.
            # Usually inside a span or an h1/div depending on layout?
            # Keeping it simple for MVP: grab all text in article
            try:
                text_content = await article.inner_text()
                content = text_content[:200].replace('\n', ' ') 
                
                post_id = f"ig_{hash(content)}"

                # Capture Screenshot for Vision Analysis
                # We use low quality jpeg to save bandwidth/tokens
                screenshot_bytes = await article.screenshot(type='jpeg', quality=70)
                image_b64 = base64.b64encode(screenshot_bytes).decode('utf-8')
                
                posts_data.append({
                    "id": post_id,
                    "content": content,
                    "image": image_b64,
                    "author": "unknown",
                    "element": article
                })
            except Exception as e:
                logger.warning(f"Failed to parse post {i}: {e}")
                
        return posts_data

    async def reply(self, post, comment):
        logger.info(f"Preparing to reply to {post['id']}...")
        if settings.dry_run:
            logger.info(f"[DRY_RUN] Would click Reply on post and type: '{comment}'")
            return

        article = post['element']
        page = self.browser.page
        
        # 1. Scroll into view
        await article.scroll_into_view_if_needed()
        await self._human_delay(1, 2)
        
        # 2. Click Reply Bubble (Go to post view often safer, but feed reply exists)
        # On IG Feed, clicking 'comment' usually focuses the text area or goes to single post page
        reply_btn = article.locator(selectors.IG_REPLY_BUTTON).first
        
        # Check if textarea is already visible (sometimes it is at bottom of card)
        # For now, assume we click the bubble
        if await reply_btn.count() > 0:
            await reply_btn.click()
            await self._human_delay(1, 2)
        else:
             # Fallback: maybe we are already on a post page or it's different?
             logger.info("   Reply bubble not found, checking for textarea directly...")
        
        # 3. Type Comment - 2024-12-13: 改進邏輯，先定位正確的輸入欄位
        try:
            # 優先在 article 範圍內尋找 textarea
            textarea = article.locator(selectors.IG_REPLY_TEXTAREA).first
            
            if await textarea.count() == 0:
                # 備選：全域搜尋但限定為可見元素
                textarea = page.locator(selectors.IG_REPLY_TEXTAREA).locator("visible=true").first
            
            if await textarea.count() > 0:
                logger.info("   🎯 Found reply textarea, clicking to focus...")
                await textarea.click()
                await self._human_delay(0.5, 1)
                
                # 輸入評論
                await page.keyboard.type(comment, delay=random.randint(50, 150))
                await self._human_delay(1, 2)
                
                # 4. Click Post - Enhanced Robustness
                # Strategy: 
                # A. Try Article Scoped (Preferred)
                # B. Try Global Visible (Fallback)
                
                logger.info("   🔍 Searching Post button...")
                post_btn = article.locator(selectors.IG_REPLY_POST_BTN).last
                
                if await post_btn.count() == 0:
                     logger.warning("   ⚠️ Post button not found in particle scope. Trying global visible...")
                     # Fallback to any visible Post button on page (risky but needed if DOM is weird)
                     post_btn = page.locator(selectors.IG_REPLY_POST_BTN).locator("visible=true").last
                
                if await post_btn.count() > 0 and await post_btn.is_visible():
                    await post_btn.click()
                    logger.info("🚀 Reply posted!")
                else:
                    logger.warning("   ⚠️ Post button not found anywhere. Reply NOT sent.")
                    return

            else:
                logger.warning("   ⚠️ Reply textarea not found. Skipping.")
                return
                
            await self._human_delay(3, 5)
        except Exception as e:
            logger.error(f"Failed to reply: {e}")

