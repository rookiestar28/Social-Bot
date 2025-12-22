from .base import BaseAdapter
import logging

logger = logging.getLogger(__name__)

class XAdapter(BaseAdapter):
    def __init__(self, browser):
        self.browser = browser

from .base import BaseAdapter
import logging
import asyncio
from playwright.async_api import TimeoutError

logger = logging.getLogger(__name__)

class XAdapter(BaseAdapter):
    def __init__(self, browser):
        self.browser = browser

    async def login(self):
        """
        Navigates to X (Twitter) and waits for manual login.
        """
        logger.info("Navigating to X (Twitter)...")
        if not self.browser.page:
            await self.browser.start()

        # X.com is the new domain, but twitter.com redirects. Using x.com directly.
        await self.browser.page.goto("https://www.x.com")
        
        logger.info("⏳ Waiting for login... Please log in in the browser window.")
        
        max_wait = 300
        check_interval = 2
        
        for i in range(max_wait // check_interval):
            try:
                # X uses stable data-testids.
                # Home link or Account menu are good indicators.
                if await self.browser.page.locator('[data-testid="AppTabBar_Home_Link"]').is_visible() or \
                   await self.browser.page.get_by_label("Home", exact=True).is_visible() or \
                   await self.browser.page.get_by_label("首頁", exact=True).is_visible():
                    logger.info("✅ Login detected! Proceeding...")
                    return
            except Exception:
                pass
            
            if i % 5 == 0:
                logger.info("   ... still waiting for login ...")
            await asyncio.sleep(check_interval)
            
        logger.warning("⚠️ Login timeout. Continuing (may fail)...")

    async def get_feed(self):
        """
        Scrapes tweets from the home timeline.
        """
        logger.info("Fetching X feed...")
        posts = []
        try:
            # Wait for any tweet to appear
            await self.browser.page.wait_for_selector('article[role="article"]', timeout=10000)
            
            # Get all article elements (tweets)
            # We filter for those having data-testid="tweet" to avoid ads/promoted if possible, 
            # though usually all are articles.
            articles = await self.browser.page.locator('article[data-testid="tweet"]').all()
            
            for i, article in enumerate(articles[:5]):
                try:
                    # Get Tweet Text
                    text_el = article.locator('[data-testid="tweetText"]')
                    if await text_el.count() > 0:
                        content = await text_el.inner_text()
                        
                        # X links are often absolute.
                        # Post ID: usually in the link to the tweet.
                        # We can try to find the time element which links to the tweet status.
                        
                        # Creating a pseudo ID for now
                        clean_content = content.replace('\n', ' ').strip()
                        post_id = f"x_{i}_{abs(hash(clean_content[:20]))}"
                        
                        if len(clean_content) > 10:
                            posts.append({
                                'id': post_id,
                                'content': clean_content,
                                'platform': 'x',
                                'element': article
                            })
                except Exception as e:
                    logger.warning(f"Failed to parse tweet {i}: {e}")
                    
        except TimeoutError:
             logger.error("Timed out waiting for tweets.")
        except Exception as e:
             logger.error(f"Error fetching X feed: {e}")
             
        logger.info(f"Found {len(posts)} tweets.")
        return posts

    async def reply(self, post, comment):
        """
        Replies to a tweet.
        """
        logger.info(f"Replying to {post['id']}...")
        try:
            article = post['element']
            
            # 1. Click Reply Button
            reply_btn = article.locator('[data-testid="reply"]')
            if await reply_btn.count() > 0:
                await reply_btn.first.click()
                await asyncio.sleep(1.0)
                
                # 2. Editor should appear in a modal
                # Look for the editor text area
                editor = self.browser.page.locator('[data-testid="tweetTextarea_0"]')
                
                if await editor.is_visible():
                    await editor.click()
                    await editor.fill(comment)
                    await asyncio.sleep(0.5)
                    
                    # 3. Click Send
                    send_btn = self.browser.page.locator('[data-testid="tweetButton"]')
                    if await send_btn.is_visible():
                        await send_btn.click()
                        logger.info("✅ Reply sent!")
                        
                        # Wait for modal to close
                        await asyncio.sleep(1.5)
                    else:
                        logger.error("Send button not found.")
                else:
                    logger.error("Reply text area not found.")
            else:
                logger.error("Reply button not found on tweet.")
                
        except Exception as e:
            logger.error(f"Failed to reply to tweet: {e}")

