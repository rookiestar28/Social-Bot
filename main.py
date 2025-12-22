import asyncio
import logging
import sys
import os
import httpx 
from config import settings
from core.db import Database
from core.brain import BotBrain
from core.browser import BrowserEngine
from core.factory import PlatformAdapterFactory

# --- Venv Enforcement ---
def ensure_venv():
    """
    If not running in a virtual environment, attempt to restart
    the script using the venv interpreter.
    """
    if sys.prefix == sys.base_prefix:
        venv_python = os.path.join(os.getcwd(), "venv", "Scripts", "python.exe")
        if os.path.exists(venv_python):
            print(f"🔄 Switching to virtual environment: {venv_python}")
            # Replace the current process with the venv python
            os.execv(venv_python, [venv_python] + sys.argv)
        else:
            print("⚠️  Warning: Not running in venv and 'venv' directory not found.")
            print("   Structure expected: ./venv/Scripts/python.exe")
            # We don't exit here to allow manual overrides if someone knows what they are doing,
            # but usually this is where we'd force it.
            # strict mode: sys.exit(1)

ensure_venv()

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("data/bot.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

async def main():
    logger.info(f"Starting Social Bot MVP (Dry Run: {settings.dry_run})")
    
    # --- Interactive Platform Selection ---
    print("\nSelect Platform:")
    print("1. Threads (Default)")
    print("2. Instagram (Beta)")
    print("3. Facebook (Alpha)")
    print("4. X / Twitter (Alpha)")
    print("5. Line (Planning)")
    print("6. WhatsApp (Planning)")
    p_choice = input("Enter choice (1-6) [1]: ").strip()
    
    if p_choice == "2":
        settings.platform = "instagram"
    elif p_choice == "3":
        settings.platform = "facebook"
    elif p_choice == "4":
        settings.platform = "x"
    elif p_choice == "5":
        settings.platform = "line"
    elif p_choice == "6":
        settings.platform = "whatsapp"
    else:
        settings.platform = "threads"
    print(f"✅ Selected Platform: {settings.platform.upper()}")

    # --- Interactive Provider Selection ---
    print("\nSelect LLM Provider:")
    print("1. OpenAI (Default)")
    print("2. Google Gemini")
    print("3. Ollama (Local)")
    choice = input("Enter choice (1-3) [1]: ").strip()
    
    if choice == "2":
        settings.llm_provider = "google"
        print("\n   Select Google Model:")
        print("   1. gemini-1.5-flash (Fast & Cheap)")
        print("   2. gemini-1.5-pro (High Quality)")
        g_choice = input("   Enter choice (1-2) [1]: ").strip()
        if g_choice == "2":
            settings.google_model = "gemini-1.5-pro"
        else:
            settings.google_model = "gemini-1.5-flash"
        print(f"   👉 Set Google Model to: {settings.google_model}")

    elif choice == "3":
        settings.llm_provider = "ollama"
        try:
            # Clean up base URL for standard API calls if needed
            api_base = settings.ollama_base_url.replace("/v1", "")
            print(f"   🔍 Fetching models from {api_base}...")
            
            async with httpx.AsyncClient() as client:
                resp = await client.get(f"{api_base}/api/tags", timeout=5.0)
                if resp.status_code == 200:
                    models = [m['name'] for m in resp.json().get('models', [])]
                    if models:
                        print("\n   Available Ollama Models:")
                        for idx, m in enumerate(models, 1):
                            print(f"   {idx}. {m}")
                        
                        m_choice = input(f"   Select model (1-{len(models)}) [1]: ").strip()
                        if m_choice.isdigit() and 1 <= int(m_choice) <= len(models):
                            settings.ollama_model = models[int(m_choice)-1]
                            print(f"   👉 Set Ollama Model to: {settings.ollama_model}")
                    else:
                        print("   ⚠️ No models found in Ollama response.")
                else:
                    print("   ⚠️ Could not fetch models from Ollama.")
        except Exception as e:
            print(f"   ⚠️ Error fetching Ollama models: {e}")
            print("   Using default model from config.")

    else:
        settings.llm_provider = "openai"
        print("\n   Select OpenAI Model:")
        print("   1. gpt-5-mini (Fast & Cost Efficient)")
        print("   2. gpt-5.2 (High Intelligence)")
        print("   3. gpt-4.1 (Reliable Legacy)")
        o_choice = input("   Enter choice (1-3) [1]: ").strip()
        if o_choice == "2":
            settings.openai_model = "gpt-5.2"
        elif o_choice == "3":
            settings.openai_model = "gpt-4.1"
        else:
            settings.openai_model = "gpt-5-mini"
        print(f"   👉 Set OpenAI Model to: {settings.openai_model}")

    print(f"✅ Selected Provider: {settings.llm_provider.upper()}\n")

    # Initialize Core Components
    db = Database()
    await db.init_db()

    
    brain = BotBrain()
    browser = BrowserEngine()
    
    # Initialize Adapter based on selection
    try:
        adapter = PlatformAdapterFactory.get_adapter(settings.platform, browser)
    except Exception as e:
        logger.error(f"Failed to initialize adapter for {settings.platform}: {e}")
        return
    
    try:
        await browser.start()
        await adapter.login()
        
        
        # Continuous Loop
        logger.info("Starting feed monitor loop... (Press Ctrl+C to stop)")
        
        consecutive_errors = 0
        max_consecutive_errors = 3

        while True:
            posts_replied = 0  # Track replies in this cycle
            posts = await adapter.get_feed()
            
            if not posts:
                logger.warning("   No posts found in this scan. Retrying in 10s...")
                await asyncio.sleep(10)
                continue

            for post in posts:
                if consecutive_errors >= max_consecutive_errors:
                    logger.error("❌ Too many consecutive errors (likely API quota or connection issue). Stopping session.")
                    break

                try:
                    post_id = post['id']
                    if await db.is_replied(post_id):
                        logger.info(f"Skipping already replied post: {post_id}")
                        continue
                        
                    logger.info(f"Analyzing post: {post_id}")
                    
                    # Check for image
                    image_data = post.get('image')
                    if image_data:
                        logger.info("   📸 Image detected! Sending visual data to brain...")
                    else:
                        logger.info("   📄 Text only.")

                    comment = await brain.generate_comment(post['content'], image_base64=image_data)
                    
                    await adapter.reply(post, comment)
                    await db.add_reply(post_id, comment)
                    posts_replied += 1
                    
                    # Success - reset counter
                    consecutive_errors = 0
                    
                    # Rate limiting
                    await asyncio.sleep(settings.min_delay_seconds)
                except Exception as e:
                    consecutive_errors += 1
                    logger.error(f"⚠️  Error processing post {post.get('id', 'unknown')}: {e}")
                    
                    # Check for critical quota errors
                    if "insufficient_quota" in str(e) or "429" in str(e):
                        logger.critical("🚨 API QUOTA EXCEEDED. Stopping to prevent billing issues.")
                        break
                    
                    logger.info(f"   Skipping to next post... (Consecutive Errors: {consecutive_errors})")
                    await asyncio.sleep(2) # Short penalty wait
                    await asyncio.sleep(2) # Short penalty wait
                    continue
            
            # --- Global Auto-Refresh Logic ---
            if posts_replied > 0:
                logger.info(f"✨ Cycle complete. Replied to {posts_replied} posts. Refreshing feed for new content...")
                await adapter.refresh_feed()
                await asyncio.sleep(5) # Wait for reload
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
    finally:
        await browser.stop()

if __name__ == "__main__":
    asyncio.run(main())
