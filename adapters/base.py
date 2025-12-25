from abc import ABC, abstractmethod
from typing import List, Dict

class BaseAdapter(ABC):
    @abstractmethod
    async def login(self):
        """Handle platform login flow."""
        pass

    @abstractmethod
    async def get_feed(self) -> List[Dict]:
        """Fetch feed posts and return a list of post dictionaries."""
        pass
    
    @abstractmethod
    async def reply(self, post: Dict, comment: str):
        """Reply to a specific post."""
        pass

    @abstractmethod
    async def get_notifications(self) -> List[Dict]:
        """
        Fetch notifications/comments on the official account's posts.
        Returns a list of notification dictionaries with:
        - id: Unique identifier
        - type: 'comment', 'reply', 'mention', etc.
        - content: Comment/reply text
        - author: Commenter username
        - post_id: ID of the related post
        - element: Playwright locator
        """
        pass

    @abstractmethod
    async def reply_to_comment(self, notification: Dict, comment: str):
        """
        Reply to a specific comment notification.
        Args:
            notification: Notification dict from get_notifications()
            comment: Reply text to send
        """
        pass

    async def refresh_feed(self):
        """
        Global refresh mechanism.
        Default implementation: Reloads the page.
        """
        if hasattr(self, 'browser') and self.browser.page:
            await self.browser.page.reload()
