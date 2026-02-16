import os
import time
import google.generativeai as genai
from dotenv import load_dotenv

# Load env from parent dir
env_path = os.path.join(os.getcwd(), "..", ".env")
load_dotenv(env_path)

api_key = os.getenv("GEMINI_API_KEY")

print(f"Checking Key: {api_key[:5]}...{api_key[-5:] if api_key else 'None'}")

if not api_key:
    print("❌ No API Key found in .env")
    exit(1)

genai.configure(api_key=api_key)

try:
    print("1. Listing Models...")
    models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
    print(f"✅ Access Granted. Available Models: {len(models)}")
    
    model_name = "gemini-2.0-flash"
    print(f"\n2. Testing Generation with {model_name}...")
    model = genai.GenerativeModel(model_name)
    
    start = time.time()
    response = model.generate_content("Hello, are you working?")
    elapsed = time.time() - start
    
    print(f"✅ Response Received in {elapsed:.2f}s:")
    print(f"   > {response.text}")
    print("\n🎉 Your API Key is ACTIVE and working correctly.")
    
except Exception as e:
    print(f"\n❌ API Error: {e}")
    if "429" in str(e):
        print("   ⚠️ This indicates a RATE LIMIT or QUOTA Exceeded.")
