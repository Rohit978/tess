import sys
import os
import warnings
import logging

# 1. SUPPRESS WARNINGS IMMEDIATELY
# Must be done before ANY other imports (especially google/torch)
os.environ["GRPC_VERBOSITY"] = "ERROR"
os.environ["GLOG_minloglevel"] = "2"

warnings.filterwarnings("ignore", category=FutureWarning)
warnings.filterwarnings("ignore", category=UserWarning)
warnings.filterwarnings("ignore", message=".*google.generativeai.*")
warnings.filterwarnings("ignore", message=".*google.api_core.*")
warnings.filterwarnings("ignore", module="google.generativeai")

# 2. RUN CLI
try:
    from .cli import main
    main()
except ImportError:
    # Fallback if running as script not package
    # Append parent dir
    sys.path.append(os.path.dirname(os.path.dirname(__file__)))
    from tess_cli.cli import main
    main()
