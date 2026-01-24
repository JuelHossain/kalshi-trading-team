
import os
from dotenv import load_dotenv
from cryptography.hazmat.primitives import serialization
from colorama import init, Fore, Style
import sys

# Initialize Colorama
init()

def debug_auth():
    print(f"{Fore.CYAN}[DEBUG] Starting Auth Debug...{Style.RESET_ALL}")

    # 1. Load .env
    # Try loading from engine/.env first, then root .env
    env_path = os.path.join(os.path.dirname(__file__), '.env')
    print(f"[DEBUG] Loading .env from: {env_path}")
    loaded = load_dotenv(env_path)
    if not loaded:
        print(f"{Fore.YELLOW}[WARNING] Failed to load from {env_path}. Trying root .env...{Style.RESET_ALL}")
        root_env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env')
        load_dotenv(root_env_path)
    
    # 2. Check Key ID
    key_id = os.getenv("KALSHI_DEMO_KEY_ID")
    print(f"[DEBUG] Key ID found: {key_id}")
    
    # 3. Check Private Key
    pk_pem = os.getenv("KALSHI_DEMO_PRIVATE_KEY")
    if not pk_pem:
        print(f"{Fore.RED}[ERROR] KALSHI_DEMO_PRIVATE_KEY not found in environment.{Style.RESET_ALL}")
        return

    print(f"[DEBUG] Raw Key Length: {len(pk_pem)}")
    print(f"[DEBUG] First 50 chars: {pk_pem[:50]}")

    # 4. Attempt Parsing
    try:
        # Simulate logic in network.py
        if "\\n" in pk_pem:
            print("[DEBUG] Replacing escaped newlines...")
            pk_pem = pk_pem.replace("\\n", "\n")
        
        if pk_pem.startswith('"') and pk_pem.endswith('"'):
             print("[DEBUG] Stripping surrounding quotes...")
             pk_pem = pk_pem[1:-1]

        # Verify headers
        if "-----BEGIN RSA PRIVATE KEY-----" not in pk_pem:
             print(f"{Fore.RED}[ERROR] Missing PEM header!{Style.RESET_ALL}")
        
        # Load Key
        private_key = serialization.load_pem_private_key(
            pk_pem.encode(), password=None
        )
        print(f"{Fore.GREEN}[SUCCESS] Private Key successfully parsed!{Style.RESET_ALL}")
        
    except Exception as e:
        print(f"{Fore.RED}[ERROR] Key Parsing Failed: {e}{Style.RESET_ALL}")
        # Print hexdump of first few chars to see if there are hidden chars
        print(f"[DEBUG] Hex of first 20 chars: {pk_pem[:20].encode().hex()}")

if __name__ == "__main__":
    debug_auth()
