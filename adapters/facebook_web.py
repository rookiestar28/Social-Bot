from .base import BaseAdapter
import logging
import asyncio
import random
from typing import List, Dict
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

    async def _human_delay(self, min_s=1.0, max_s=3.0):
        await asyncio.sleep(random.uniform(min_s, max_s))

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

    async def get_feed(self) -> List[Dict]:
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
                            'element': article,
                            '_locator': article
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

    async def get_notifications(self) -> List[Dict]:
        """
        獲取 Facebook 官方帳號/粉專的通知
        """
        page = self.browser.page
        logger.info(" [Facebook] Navigating to Notifications...")

        try:
            # Click on notifications icon or navigate directly
            notif_nav = page.locator(selectors.FB_NOTIFICATION_NAV).first
            if await notif_nav.count() > 0:
                await notif_nav.click()
                await self._human_delay(2, 3)
            else:
                # Direct navigation fallback
                await page.goto("https://www.facebook.com/notifications", timeout=30000)
                await self._human_delay(2, 3)

            notifications = []
            
            # Wait for notification items
            try:
                await page.wait_for_selector(selectors.FB_NOTIFICATION_ITEM, timeout=10000)
            except:
                logger.warning(" [Facebook] No notifications found or page structure changed.")
                return []

            items = await page.locator(selectors.FB_NOTIFICATION_ITEM).all()
            logger.info(f" [Facebook] Found {len(items)} notification items.")

            for i, item in enumerate(items[:10]):
                try:
                    if not await item.is_visible():
                        continue

                    full_text = await item.inner_text()
                    
                    # Determine notification type
                    notif_type = "unknown"
                    if "commented" in full_text.lower() or "留言" in full_text or "回應" in full_text:
                        notif_type = "comment"
                    elif "mentioned" in full_text.lower() or "提及" in full_text or "標記" in full_text:
                        notif_type = "mention"
                    elif "replied" in full_text.lower() or "回覆" in full_text:
                        notif_type = "reply"
                    elif "reacted" in full_text.lower() or "心情" in full_text or "對你的" in full_text:
                        notif_type = "reaction"
                        continue  # Skip reactions

                    notif_id = f"fb_notif_{i}_{hash(full_text[:50])}"

                    notifications.append({
                        'id': notif_id,
                        'type': notif_type,
                        'content': full_text[:200],
                        'author': 'unknown',
                        'post_id': None,
                        'element': item,
                        '_locator': item
                    })

                except Exception as e:
                    logger.warning(f" [Facebook] Failed to parse notification {i}: {e}")
                    continue

            logger.info(f" [Facebook] Parsed {len(notifications)} actionable notifications.")
            return notifications

        except Exception as e:
            logger.error(f" [Facebook] Error fetching notifications: {e}")
            return []

    async def reply_to_comment(self, notification: Dict, comment: str):
        """
        回覆 Facebook 上的特定留言通知
        """
        page = self.browser.page
        notif_id = notification.get('id')
        logger.info(f" [Facebook] Replying to notification {notif_id}...")

        item = notification.get('_locator') or notification.get('element')
        
        if not item:
            logger.error(" [Facebook] No locator found. Cannot reply.")
            return False

        try:
            # Click on the notification to open context
            await item.scroll_into_view_if_needed()
            await item.click()
            await self._human_delay(2, 3)

            # Look for comment input box
            input_box = page.locator(selectors.FB_COMMENT_INPUT).first

            if await input_box.count() == 0:
                # Alternative selectors
                input_box = page.locator('div[role="textbox"][contenteditable="true"]').first

            if await input_box.count() == 0:
                logger.error(" [Facebook] Comment input not found.")
                return False

            await input_box.click()
            await self._human_delay(0.5, 1)

            # Type comment
            await input_box.fill(comment)
            await self._human_delay(1, 2)

            # Try Enter key first
            await input_box.press("Enter")
            await self._human_delay(1, 2)

            # Check if we need to click submit button
            submit_btn = page.locator(selectors.FB_COMMENT_SUBMIT).first
            if await submit_btn.count() > 0 and await submit_btn.is_visible():
                await submit_btn.click()

            logger.info(" [Facebook] Reply sent successfully!")
            await self._human_delay(2, 3)
            return True

        except Exception as e:
            logger.error(f" [Facebook] Error replying to notification: {e}")
            return False

    async def reply(self, post: Dict, comment: str):
        """
        Replies to a Facebook post.
        """
        logger.info(f"Replying to {post['id']}...")
        try:
            article = post.get('element') or post.get('_locator')
            
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
