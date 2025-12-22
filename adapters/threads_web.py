import logging
import asyncio
import random
from core.browser import BrowserEngine
from adapters import selectors

logger = logging.getLogger(__name__)

class ThreadsAdapter:
    """
    Threads 平台適配器 (物件鎖定版 - 解決找不到貼文問題)
    """
    def __init__(self, browser: BrowserEngine):
        self.browser = browser
        self.page = None 

    async def _ensure_page(self):
        if not self.page:
            self.page = self.browser.page

    async def _human_delay(self, min_s=1.0, max_s=3.0):
        await asyncio.sleep(random.uniform(min_s, max_s))

    async def login(self):
        await self._ensure_page()
        logger.info(" [Threads] Navigating to https://www.threads.net/ ...")
        
        try:
            await self.page.goto("https://www.threads.net/", timeout=60000)
            await self._human_delay(2, 4)

            if await self.page.locator(selectors.LOGIN_CHECK).count() > 0:
                logger.warning(" [Threads] Not logged in detected!")
                logger.warning(" ⚠️  Please log in MANUALLY in the browser window now.")
                logger.warning(" ⏳  Waiting 45 seconds for manual login...")
                for i in range(45):
                    if i % 5 == 0: logger.info(f"    ... waiting ({45-i}s left)")
                    await asyncio.sleep(1)
            else:
                logger.info(" [Threads] Login check passed.")

        except Exception as e:
            logger.error(f" [Threads] Login navigation error: {e}")

    async def _get_image_base64(self, img_locator):
        try:
            src = await img_locator.get_attribute("src")
            if not src: return None
            
            full_base64 = await self.page.evaluate(f"""
                async () => {{
                    const response = await fetch("{src}");
                    const blob = await response.blob();
                    return new Promise((resolve) => {{
                        const reader = new FileReader();
                        reader.onloadend = () => resolve(reader.result);
                        reader.readAsDataURL(blob);
                    }});
                }}
            """)
            if "," in full_base64:
                return full_base64.split(",")[1]
            return full_base64
        except Exception:
            return None

    async def get_feed(self):
        """
        抓取貼文並保存元素定位器 (_locator)
        """
        await self._ensure_page()
        logger.info(" [Threads] Scanning feed...")

        try:
            await self.page.evaluate(f"window.scrollBy(0, {random.randint(300, 600)})")
            await self._human_delay(2.0, 3.0)

            posts_data = []
            # 獲取所有貼文容器的定位器
            articles_locators = await self.page.locator(selectors.POST_ARTICLE).all()
            
            for article in articles_locators[:3]: 
                try:
                    if not await article.is_visible(): continue

                    # Check for Reply Button to confirm it's a post and not a header
                    if await article.locator(selectors.REPLY_BUTTON).count() == 0:
                        continue

                    raw_text = await article.inner_text()
                    if not raw_text or len(raw_text) < 5: continue

                    lines = [l.strip() for l in raw_text.split('\n') if l.strip()]
                    content_body = " ".join(lines)
                    post_id = str(hash(content_body))
                    
                    image_data = None
                    images = article.locator('img')
                    if await images.count() > 1:
                        target_img = images.nth(1)
                        if (await target_img.bounding_box())['width'] > 100:
                            image_data = await self._get_image_base64(target_img)
                    
                    posts_data.append({
                        'id': post_id,
                        'content': content_body,
                        'image': image_data,
                        '_locator': article 
                    })
                except Exception:
                    continue

            logger.info(f" [Threads] Found {len(posts_data)} posts.")
            return posts_data

        except Exception as e:
            logger.error(f" [Threads] Error scanning feed: {e}")
            return []

    async def _get_reply_context(self, post_locator):
        """
        Determine if we are in a Modal (dialog) context or Inline context.
        Returns (target_container_locator, context_type_string)
        """
        # Check if REPLY_MODAL (dialog) is visible
        modal = self.page.locator(selectors.REPLY_MODAL)

        if await modal.count() > 0 and await modal.first.is_visible():
            # Scope search to the Modal
            logger.info(" [Threads] Detected Reply Modal context.")
            return modal.last, "MODAL"
        else:
            # Scope search to the Post Locator (Inline)
            logger.info(" [Threads] Detected Inline Reply context.")
            return post_locator, "INLINE"

    async def reply(self, post: dict, comment: str):
        """
        使用保存的 Locator 直接回覆，不再重新搜尋
        """
        post_id = post.get('id')
        logger.info(f" [Threads] Replying to post ID {post_id}...")

        post_locator = post.get('_locator')
        
        if not post_locator:
            logger.error(" [Threads] No locator found in post object. Cannot reply.")
            return

        try:
            await post_locator.scroll_into_view_if_needed()
            # 3. 在該貼文容器內尋找回覆按鈕
            # 使用 selectors.py 中的通用定位器
            reply_btn = post_locator.locator(selectors.REPLY_BUTTON)
            

            
            if await reply_btn.count() == 0:
                logger.error(" [Threads] Reply button not found in this post.")
                return

            await reply_btn.click()
            logger.info(" [Threads] Clicked reply button.")
            
            await self._human_delay(1.5, 2.5)
            
            # --- Safety Net: Check if "New Thread" modal opened incorrectly ---
            # 這是為了防止機器人誤點擊到 "發布串文" 的標頭，或者因 Context 誤判而開啟了新串文視窗
            new_thread_modal = self.page.locator(selectors.NEW_THREAD_MODAL_TITLE)
            if await new_thread_modal.count() > 0 and await new_thread_modal.first.is_visible():
                logger.error(" [Threads] CRITICAL: 'New Thread' modal detected instead of Reply! Closing it...")
                
                # 嘗試關閉
                close_btn = self.page.locator(selectors.CLOSE_MODAL_BTN).last
                if await close_btn.count() > 0:
                    await close_btn.click()
                    logger.info(" [Threads] Closed 'New Thread' modal.")
                    
                    # 處理可能的 "Discard" 確認選單
                    await self._human_delay(0.5, 1.0)
                    discard_btn = self.page.locator(selectors.DISCARD_MENU_BTN).last
                    if await discard_btn.count() > 0 and await discard_btn.is_visible():
                        await discard_btn.click()
                        logger.info(" [Threads] Confirmed discard.")
                
                return False
            # ------------------------------------------------------------------

            # 4. Determine Context (Modal vs Inline) and Scoped Search
            target_container, context_type = await self._get_reply_context(post_locator)

            # 在鎖定的容器內尋找輸入框
            textbox = target_container.locator(selectors.REPLY_INPUT).first
            
            if await textbox.count() == 0:
                 logger.error(f" [Threads] Textbox not found in {context_type} context.")
                 return
            
            if await textbox.count() == 0:
                 logger.error(" [Threads] Textbox not found after clicking reply.")
                 return

            await textbox.click()
            logger.info(f" [Threads] Typing comment ({len(comment)} chars)...")
            
            await textbox.press_sequentially(comment, delay=random.randint(50, 150))
            await self._human_delay(1.5, 2.0)

            # 5. 點擊發送
            # 5. 點擊發送
            # 無論是 Modal 還是 Inline，我們都嘗試在 Target Container 內尋找按鈕
            # 這是因為我們現在有了更廣泛的選擇器 (REPLY_SEND_BTN 包含 SVG)，因此 Scoped 是安全的
            post_btn = target_container.locator(selectors.REPLY_SEND_BTN).last
            
            if await post_btn.count() == 0:
                 logger.error(" [Threads] Post/Reply button not found. (Count is 0)")
                 return
            
            if await post_btn.is_disabled():
                 logger.error(" [Threads] Post button is disabled. Text input might have failed.")
                 return

            await post_btn.click()
            logger.info(" [Threads] Clicked Post button!")
            
            await self._human_delay(3.0, 4.0)
            logger.info(" [Threads] Reply sequence completed.")
            return True

        except Exception as e:
            logger.error(f" [Threads] Error during reply execution: {e}")
            return False