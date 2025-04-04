#!/usr/bin/env python
import sys
from nlm.auth import handle_auth

if __name__ == "__main__":
    debug = "--debug" in sys.argv
    auth_token, cookies, error = handle_auth(debug=debug)
    
    if error:
        print(f"Error: {error}")
        sys.exit(1)
        
    print(f"Auth Token: {auth_token[:10]}...")
    print(f"Cookies: {cookies[:30]}...")
    print(f"Auth info written to ~/.nlm/env")
