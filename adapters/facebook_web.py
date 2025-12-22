from .base import BaseAdapter
import logging
import asyncio
from playwright.async_api import TimeoutError
from . import selectors

logger = logging.getLogger(__name__)

class FacebookAdapter(BaseAdapter):
    def __init__(self, browser):
        self.browser = browser

    async def _dismiss_overlays(self):
        """Attempts to clear standard Facebook/Browser overlays."""
        try:
            # Press Escape to close standard modals
            # await self.browser.page.keyboard.press("Escape")
            # Clicking 1,1 or Escape arbitrarily can cause black screen or unwanted interactions.
            # Only use if necessary.
            pass
        except:
            pass

    async def login(self):
        """
        Navigates to Facebook and waits for the user to manually log in.
        """
        logger.info("Navigating to Facebook...")
        if not self.browser.page:
            await self.browser.start()
        
        await self.browser.page.goto("https://www.facebook.com")
        
        logger.info("⏳ Waiting for login... Please log in in the browser window.")
        
        max_wait = 300 
        check_interval = 2
        
        for i in range(max_wait // check_interval):
            try:
                # 1. Overlay Handling
                if i % 2 == 0:
                    await self._dismiss_overlays()

                # 2. Check for success indicators
                if await self.browser.page.get_by_label("Home", exact=True).is_visible() or \
                   await self.browser.page.get_by_label("首頁", exact=True).is_visible() or \
                   await self.browser.page.get_by_role("feed").is_visible() or \
                   await self.browser.page.locator('div[role="navigation"]').is_visible():
                    logger.info("✅ Login detected! Proceeding...")
                    return
            except Exception:
                pass
            
            if i % 10 == 0:
                logger.info("   ... still waiting for login ...")
            await asyncio.sleep(check_interval)
            
        logger.warning("⚠️ Login timeout or not detected. Proceeding anyway (might fail).")

    async def get_feed(self):
        """
        Scrapes posts. Handles black screen loop by periodically dismissing overlays.
        """
        logger.info("Fetching Facebook feed...")
        
        # Aggressively clear overlays before scanning - REMOVED to prevent black screen
        # await self._dismiss_overlays()
        
        posts = []
        try:
            # Wait for any article
            try:
                await self.browser.page.wait_for_selector('[role="article"]', state="visible", timeout=10000)
            except TimeoutError:
                logger.warning("Timeout waiting for 'article' role. Trying to dismiss overlays and retry...")
                await self._dismiss_overlays()
            
            # Get all articles
            articles = await self.browser.page.locator('[role="article"]').all()
            
            for i, article in enumerate(articles[:5]):
                try:
                    if not await article.is_visible():
                        continue

                    # 1. Extract Text
                    # Use specific selector to avoid reading comments
                    content_el = article.locator(selectors.POST_CONTENT_TEXT).first
                    if await content_el.count() > 0:
                        content = await content_el.inner_text()
                    else:
                        content = await article.inner_text() # Fallback

                    lines = [line.strip() for line in content.split('\n') if line.strip()]
                    clean_content = " ".join(lines)
                    
                    # 2. Extract Images (Fix for "Text only" issue)
                    images = []
                    # Check standard img tags, but exclude profile pics (usually small)
                    # This is heuristic.
                    imgs = await article.locator('img').all()
                    for img in imgs:
                        src = await img.get_attribute('src')
                        # Filter out tiny icons or profile pics by checking URL or generic classes
                        # For MVP, we simply take non-empty src that's not clearly a badge
                        if src and 'emoji' not in src:
                             images.append(src)
                    
                    post_id = f"fb_{i}_{abs(hash(clean_content[:20]))}"
                    
                    if len(clean_content) > 30 or len(images) > 0:
                        post_data = {
                            'id': post_id,
                            'content': clean_content,
                            'platform': 'facebook',
                            'element': article
                        }
                        if images:
                            post_data['images'] = images[:2] # Limit to 2 images
                            logger.info(f"   📸 Found {len(images)} images in post {i}")
                            
                        posts.append(post_data)
                        
                except Exception as e:
                    logger.warning(f"Failed to parse post {i}: {e}")
                    
        except Exception as e:
            logger.error(f"Error fetching FB feed: {e}")
            
        logger.info(f"Found {len(posts)} posts.")
        return posts

    async def reply(self, post, comment):
        """
        Replies to a Facebook post.
        """
        logger.info(f"Replying to {post['id']}...")
        try:
            article = post['element']
            
            # Method 1: Click "Comment" button
            # Expanded selectors for Chinese/English
            comment_triggers = [
                "Comment", "Write a comment", "留言", "回應", "寫留言", "評論", "发表评论"
            ]
            
            found_trigger = False
            
            # Priority: Use selectors.REPLY_BUTTON first
            reply_btn = article.locator(selectors.REPLY_BUTTON).first
            if await reply_btn.count() > 0 and await reply_btn.is_visible():
                await reply_btn.click()
                found_trigger = True
            
            if not found_trigger:
                for trigger in comment_triggers:
                    # STRICT MATCH text-is instead of has-text to avoid "封鎖這個留言" (Block this comment)
                    btn = article.locator(f"div[role='button']:text-is('{trigger}')").first
                    if await btn.count() > 0 and await btn.is_visible():
                         await btn.click()
                         found_trigger = True
                         break
                    # Try specific span with text-is
                    span = article.locator(f"span:text-is('{trigger}')").first
                    if await span.count() > 0 and await span.is_visible():
                         await span.click()
                         found_trigger = True
                         break
            
            if found_trigger:
                await asyncio.sleep(1.5) # Wait for animation

            # Method 2: Find the textbox
            # Generic textbox query is often best
            input_box = article.locator('div[role="textbox"][contenteditable="true"]').first
            
            if not await input_box.is_visible():
                # Fallback: Search globally if article-scoped failed (threaded view)
                # But risky. Try simple locator.
                input_box = article.locator('div[aria-label*="留言"], div[aria-label*="Comment"], div[aria-label*="Write"]').first

            if await input_box.is_visible():
                logger.info("   🎯 Found reply textarea, clicking to focus...")
                await input_box.click()
                await asyncio.sleep(0.5)
                await input_box.fill(comment)
                await asyncio.sleep(0.8)
                await input_box.press("Enter")
                
                # Check if we need to click a "Send" icon (mobile view or specific UIs)
                # usually Enter works on Desktop, but sometimes need to click the airplane icon
                send_icon = article.locator('div[aria-label="Post"], div[aria-label="發佈"], div[aria-label="留言"]').last
                if await send_icon.is_visible():
                     logger.info("   🔍 Searching Post button...")
                     # If the textbox is cleared, it might have sent.
                     pass 

                logger.info("🚀 Reply posted!")
            else:
                logger.error("   ❌ Reply bubble not found even after clicking Comment.")
                
        except Exception as e:
            logger.error(f"Failed to reply to FB post: {e}")

