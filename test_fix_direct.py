from tess_cli.core.coding_engine import CodingEngine
from tess_cli.core.brain import Brain

brain = Brain()
engine = CodingEngine(brain, workspace_dir=".")

print("Calling fix_code directly...")
res = engine.fix_code("test_debug.py", "ZeroDivisionError: division by zero")
print(f"Result: {res}")
