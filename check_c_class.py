import sys
import os

# Ensure the local tess_cli is prioritised
sys.path.insert(0, os.getcwd())

try:
    from tess_cli.core.terminal_ui import C
    import tess_cli.core.terminal_ui as tui
    
    print(f"File Path: {tui.__file__}")
    
    attrs = ['RED', 'GREEN', 'YELLOW', 'BLUE', 'BRIGHT_BLUE', 'BRIGHT_RED', 'CYAN', 'R', 'MISSING_COLOR_X']
    for attr in attrs:
        val = getattr(C, attr, 'FAIL')
        print(f"C.{attr}: {'EXISTS (or handled by meta)' if val != 'FAIL' else 'FAIL'}")
        if attr == 'MISSING_COLOR_X':
            print(f"  Value for MISSING_COLOR_X: {repr(val)}")

        
except Exception as e:
    print(f"Error: {e}")
