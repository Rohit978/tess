import sys
import os

# Add current directory to path
sys.path.append(os.getcwd())

class Mock:
    def __getattr__(self, name):
        return Mock()
    def __init__(self):
        self.collection = Mock() # for CommandIndexer

def check_component(name, module_path, class_name, methods):
    try:
        # Import module
        mod = __import__(module_path, fromlist=[class_name])
        cls = getattr(mod, class_name)
        
        # Instantiate (mocking args if needed)
        try:
            if class_name in ["Organizer", "DesigningEngine"]:
                obj = cls(brain=Mock())
            elif class_name in ["CommandIndexer", "Librarian"]:
                obj = cls(knowledge_base=Mock()) 
            else:
                obj = cls()
        except:
             # If instantiation fails heavily due to missing params, just check class attr
             obj = cls
             
        print(f"✅ Class '{class_name}' found in {module_path}")
        
        for method in methods:
            if hasattr(obj, method):
                print(f"  ✅ Method '{method}' verified.")
            else:
                print(f"  ❌ Method '{method}' MISSING!")
                return False
        return True
    except ImportError as e:
        print(f"❌ Failed to import {module_path}: {e}")
        return False
    except AttributeError as e:
        print(f"❌ Failed to find class {class_name}: {e}")
        return False
    except Exception as e:
        print(f"❌ Error checking {name}: {e}")
        return False

print("--- TESS PRE-LAUNCH CHECK ---\n")

checks = [
    ("SystemController", "tess_cli.core.system_controller", "SystemController", ["press_key", "type_text", "media_control"]),
    ("AppLauncher", "tess_cli.core.app_launcher", "AppLauncher", ["launch_app", "scan_apps"]),
    ("Executor", "tess_cli.core.executor", "Executor", ["execute_command"]),
    ("WebBrowser", "tess_cli.core.web_browser", "WebBrowser", ["search_google", "scrape_page"]),
    ("Organizer", "tess_cli.core.organizer", "Organizer", ["organize_directory"]),
    ("CodingEngine", "tess_cli.core.coding_engine", "CodingEngine", ["scaffold_project", "grep_search", "ls_recursive"]),
    ("VoiceClient", "tess_cli.core.voice_client", "VoiceClient", ["listen", "transcribe"]),
    ("YouTubeClient", "tess_cli.core.youtube_client", "YouTubeClient", ["play_video"]),
    ("CommandIndexer", "tess_cli.core.command_indexer", "CommandIndexer", ["index_system_commands"]),
]

all_passed = True
for name, mod, cls, meths in checks:
    if not check_component(name, mod, cls, meths):
        all_passed = False
    print("-" * 30)

if all_passed:
    print("\n✅✅ ALL SYSTEMS GO! READY FOR LAUNCH! ✅✅")
else:
    print("\n❌❌ LAUNCH SCRUBBED! ERRORS FOUND. ❌❌")
