from tess_cli.core.coding_engine import CodingEngine
from tess_cli.core.brain import Brain

print("Initializing Brain & Engine...")
brain = Brain()
engine = CodingEngine(brain, workspace_dir=".")

print("--- Testing Review ---")
print(engine.review_code("test_debug.py"))

print("\n--- Testing Debugger ---")
print(engine.debug_code("test_debug.py"))
