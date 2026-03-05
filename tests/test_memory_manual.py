
import sys
import os
import shutil

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tess_cli.core.knowledge_base import KnowledgeBase

def test_memory():
    print("Testing KnowledgeBase (Memory)...")
    
    # Init
    kb = KnowledgeBase()
    print(f"KB Available: {kb.available}")
    print(f"Fallback Engine: {kb.fallback_engine is not None}")
    
    # Store
    fact = "My favorite color is Neon Blue."
    print(f"Storing fact: '{fact}'")
    kb.store_memory(fact, metadata={"type": "test_fact"})
    
    # Recall
    print("Recalling 'favorite color'...")
    results = kb.search_memory("favorite color", n_results=1)
    print(f"Results:\n{results}")
    
    if "Neon Blue" in results:
        print("✅ Memory Store/Recall Verified.")
    else:
        print("❌ Memory Recall Failed.")

if __name__ == "__main__":
    test_memory()
