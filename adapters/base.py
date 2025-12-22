from abc import ABC, abstractmethod

class BaseAdapter(ABC):
    @abstractmethod
    async def login(self):
        pass

    @abstractmethod
    async def get_feed(self):
        pass
    
    @abstractmethod
    async def reply(self, post, comment):
        pass

    async def refresh_feed(self):
        """
        Global refresh mechanism.
        Default implementation: Reloads the page.
        """
        if hasattr(self, 'browser') and self.browser.page:
            await self.browser.page.reload()

