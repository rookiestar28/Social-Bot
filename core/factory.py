from core.browser import BrowserEngine
from adapters.base import BaseAdapter
# Import adapters lazily or directly if no circular deps
from adapters.threads_web import ThreadsAdapter
from adapters.instagram_web import InstagramAdapter

# Placeholder imports for new adapters (to be created)
# from adapters.facebook_web import FacebookAdapter
# from adapters.x_web import XAdapter

class PlatformAdapterFactory:
    @staticmethod
    def get_adapter(platform_name: str, browser: BrowserEngine) -> BaseAdapter:
        platform = platform_name.lower().strip()
        
        if platform == "threads":
            return ThreadsAdapter(browser)
        elif platform == "instagram":
            return InstagramAdapter(browser)
        elif platform == "facebook":
            from adapters.facebook_web import FacebookAdapter
            return FacebookAdapter(browser)
        elif platform == "x":
            from adapters.x_web import XAdapter
            return XAdapter(browser)
        elif platform == "line":
            from adapters.line_web import LineAdapter
            return LineAdapter(browser)
        elif platform == "whatsapp":
            from adapters.whatsapp_web import WhatsAppAdapter
            return WhatsAppAdapter(browser)
        else:
            raise ValueError(f"Unknown platform: {platform}")
