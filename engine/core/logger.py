
import logging
import os
import re
import sys

from colorama import Fore, Style, init

# Initialize Colorama
init(autoreset=True)

# Pre-compile regex for performance (Emoji stripping)
EMOJI_PATTERN = re.compile("["
    "\U0001F600-\U0001F64F"  # emoticons
    "\U0001F300-\U0001F5FF"  # symbols & pictographs
    "\U0001F680-\U0001F6FF"  # transport & map symbols
    "\U0001F1E0-\U0001F1FF"  # flags
    "\U00002702-\U000027B0"
    "\U000024C2-\U0001F251"
    "]+", flags=re.UNICODE)

class EmojiSafeFormatter(logging.Formatter):
    """Strips emojis for Windows compatibility and adds colors."""
    
    FORMATS = {
        logging.DEBUG: Fore.CYAN + "[%(levelname)s] %(message)s" + Style.RESET_ALL,
        logging.INFO: Fore.WHITE + "[%(levelname)s] %(message)s" + Style.RESET_ALL,
        logging.WARNING: Fore.YELLOW + "[%(levelname)s] %(message)s" + Style.RESET_ALL,
        logging.ERROR: Fore.RED + "[%(levelname)s] %(message)s" + Style.RESET_ALL,
        logging.CRITICAL: Fore.RED + Style.BRIGHT + "[%(levelname)s] 💀 %(message)s" + Style.RESET_ALL,
    }

    def format(self, record):
        # 1. Strip Emojis if on Windows (or forced)
        if os.name == "nt":
             if isinstance(record.msg, str):
                record.msg = EMOJI_PATTERN.sub("", record.msg)
        
        # 2. Add Color
        log_fmt = self.FORMATS.get(record.levelno, self.FORMATS[logging.INFO])
        formatter = logging.Formatter(log_fmt)
        return formatter.format(record)

def get_logger(name: str):
    """Factory to return a configured logger."""
    logger = logging.getLogger(name)
    
    if not logger.handlers:
        logger.setLevel(logging.DEBUG)  # Capture all, let handler filter
        
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(EmojiSafeFormatter())
        
        logger.addHandler(handler)
        
    return logger

# Global instance for easy access
logger = get_logger("GHOST")
