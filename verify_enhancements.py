
import os
import sys
from tess_cli.core.coding_engine import CodingEngine
from tess_cli.core.terminal_ui import print_info, print_success, print_error

def test_coding_tools():
    # Setup mock brain
    class MockBrain:
        def update_history(self, role, content): pass
        def request_completion(self, messages, json_mode=False): return "{}"
    
    brain = MockBrain()
    engine = CodingEngine(brain, workspace_dir="test_workspace")
    
    # 1. Test Scaffold
    print_info("Testing Scaffold...")
    res = engine.scaffold_project("python", "test_project")
    print_success(res)
    
    # 2. Test ls_recursive
    print_info("Testing ls_recursive...")
    res = engine.ls_recursive("test_project")
    print_success("Tree:\n" + res)
    
    # 3. Test grep_search
    print_info("Testing grep_search...")
    engine.write_file("test_project/src/main.py", "def hello():\n    print('test search pattern')\n")
    res = engine.grep_search("search pattern", "test_project")
    print_success("Grep result: " + res)
    
    # 4. Test outline
    print_info("Testing outline...")
    res = engine.get_file_outline("test_project/src/main.py")
    print_success("Outline result: " + res)
    
    # 5. Test replace_block (Refined)
    print_info("Testing replace_block (Refined)...")
    original_code = "def foo():\n    print('hello')  \n" # extra space
    engine.write_file("test_project/src/refine.py", original_code)
    
    # Try replacing with slightly different whitespace in search block
    search = "def foo():\n    print('hello')" 
    replace = "def foo():\n    print('refined')"
    res = engine.replace_block("test_project/src/refine.py", search, replace)
    print_success(res)
    
    with open(os.path.join(engine.workspace_root, "test_project/src/refine.py"), "r") as f:
        content = f.read()
        if "refined" in content:
            print_success("Refined replacement verification passed.")
        else:
            print_error("Refined replacement verification failed.")
            print(f"Content was: {repr(content)}")

if __name__ == "__main__":
    # Add project root to path
    sys.path.append(os.getcwd())
    try:
        test_coding_tools()
    except Exception as e:
        print_error(f"Verification failed: {e}")
        import traceback
        traceback.print_exc()
