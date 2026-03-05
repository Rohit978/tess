import logging
import os
import sys

def setup_logger(name="TESS", level=logging.WARNING):
    """Configures console & file logging."""
    logger = logging.getLogger(name)
    logger.setLevel(level)
    
    if logger.handlers: return logger
        
    fmt = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    # Console
    ch = logging.StreamHandler(sys.stdout)
    ch.setFormatter(fmt)
    logger.addHandler(ch)
    
    # File
    log_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "logs")
    os.makedirs(log_dir, exist_ok=True)
    fh = logging.FileHandler(os.path.join(log_dir, "tess.log"), encoding='utf-8')
    fh.setFormatter(fmt)
    logger.addHandler(fh)
    
    return logger
