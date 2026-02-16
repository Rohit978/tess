import logging
from tess_cli.core.youtube_client import YouTubeClient
from tess_cli.core.terminal_ui import C

# Setup logging
logging.basicConfig(level=logging.INFO)

print(f"{C.BRIGHT_CYAN}🧪 Starting YouTube Client Debugger...{C.R}")

try:
    client = YouTubeClient(headless=False)
    
    query = "him and i"
    print(f"\n{C.YELLOW}▶️ Attempting to play: {query}{C.R}")
    
    result = client.play_video(query)
    
    print(f"\n{C.BRIGHT_GREEN}✅ Result: {result}{C.R}")
    
    # Keep open for a moment to see
    import time
    time.sleep(10)
    
    client.stop()

except Exception as e:
    print(f"\n{C.RED}❌ CRASH: {e}{C.R}")
    import traceback
    traceback.print_exc()
