
import os
import sys
import google.generativeai as genai
from dotenv import load_dotenv

# Add project root
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tess_cli.core.config import Config

def list_models():
    print("--- Checking Gemini Models ---")
    
    # Load Config (which loads .env)
    Config.load()
    
    key = Config.get_api_key("gemini")
    if not key:
        print("❌ No Gemini API Key found in Config/Env.")
        return

    print(f"🔑 Key found (ends with {key[-4:]})")
    
    try:
        genai.configure(api_key=key)
        print("✅ Configured genai. Listing models...")
        
        models = list(genai.list_models())
        found_any = False
        for m in models:
            if 'generateContent' in m.supported_generation_methods:
                print(f"  - {m.name} ({m.display_name})")
                found_any = True
                
        if not found_any:
            print("⚠️ No models found with 'generateContent' capability.")
            
    except Exception as e:
        print(f"❌ Error listing models: {e}")

if __name__ == "__main__":
    # Redirect stdout to file (UTF-8)
    with open("gemini_models.txt", "w", encoding="utf-8") as f:
        sys.stdout = f
        list_models()
    # Also print to console for backup
    sys.stdout = sys.__stdout__
    print(" written to gemini_models.txt")
