import json
import os
import re
import time
import platform
import shutil
import tempfile
from pathlib import Path
from typing import Tuple, Optional, Dict, List
import requests
from bs4 import BeautifulSoup
from pycookiecheat import chrome_cookies


def extract_json_object(s: str) -> Optional[str]:
    """
    Extract a JSON object from a string, handling nested braces properly.
    
    Args:
        s: String containing a JSON object starting with '{'
        
    Returns:
        JSON object as string, or None if extraction failed
    """
    if not s.startswith('{'):
        return None
        
    brace_count = 0
    for i, char in enumerate(s):
        if char == '{':
            brace_count += 1
        elif char == '}':
            brace_count -= 1
            if brace_count == 0:
                # Found the matching closing brace
                return s[:i+1]
                
    # If we reach here, the JSON is not properly balanced
    return None


def get_auth(profile_name: str = "Default", debug: bool = False) -> Tuple[str, str]:
    """
    Extract authentication information from Chrome using pycookiecheat.
    
    Args:
        profile_name: Browser profile name to use
        debug: Whether to enable debug output
        
    Returns:
        Tuple of (auth_token, cookies)
    """
    try:
        # Get Chrome directory based on platform
        chrome_dir = get_chrome_dir(profile_name)
        if debug:
            print(f"Using Chrome profile directory: {chrome_dir}")
            print(f"Checking if directory exists: {os.path.exists(chrome_dir)}")
            print(f"Directory contents: {os.listdir(chrome_dir) if os.path.exists(chrome_dir) else 'directory not found'}")
        
        # Get cookies from Chrome using pycookiecheat
        cookies = get_google_cookies(chrome_dir, debug)
        
        if not cookies:
            if debug:
                print("Failed to retrieve any cookies from Chrome")
            return "", ""
            
        if debug:
            print(f"Retrieved {len(cookies)} cookies from Chrome")
            print(f"Cookie domains: {', '.join(set([k.split('.')[-2] + '.' + k.split('.')[-1] for k in cookies.keys() if '.' in k]))}")
        
        # Format cookies as string
        cookie_str = "; ".join([f"{name}={value}" for name, value in cookies.items()])
        
        if debug:
            print(f"Cookie string length: {len(cookie_str)}")
            print("Attempting to get auth token from NotebookLM...")
        
        # Get auth token by making a request to NotebookLM
        auth_token = get_auth_token_from_nlm(cookies, debug)
        
        if debug:
            token_preview = auth_token[:10] + "..." if auth_token else "None"
            print(f"Retrieved auth token: {token_preview}")
        
        return auth_token, cookie_str
    except Exception as e:
        if debug:
            print(f"Error in get_auth: {str(e)}")
            import traceback
            traceback.print_exc()
        return "", ""


def get_chrome_dir(profile_name: str = "Default") -> str:
    """Get Chrome profile directory path for the current platform."""
    system = platform.system()
    home = str(Path.home())
    
    if system == "Darwin":  # macOS
        base_dir = os.path.join(home, "Library", "Application Support", "Google", "Chrome")
    elif system == "Linux":
        base_dir = os.path.join(home, ".config", "google-chrome")
    elif system == "Windows":
        local_app_data = os.environ.get("LOCALAPPDATA", os.path.join(home, "AppData", "Local"))
        base_dir = os.path.join(local_app_data, "Google", "Chrome", "User Data")
    else:
        raise Exception(f"Unsupported platform: {system}")
    
    # Check for Chrome alternative browsers if standard Chrome not found
    if not os.path.exists(base_dir):
        alternatives = []
        
        if system == "Darwin":  # macOS
            alternatives = [
                os.path.join(home, "Library", "Application Support", "Google", "Chrome Canary"),
                os.path.join(home, "Library", "Application Support", "Chromium"),
                os.path.join(home, "Library", "Application Support", "Microsoft Edge"),
                os.path.join(home, "Library", "Application Support", "Brave Browser"),
            ]
        elif system == "Linux":
            alternatives = [
                os.path.join(home, ".config", "chromium"),
                os.path.join(home, ".config", "microsoft-edge"),
                os.path.join(home, ".config", "BraveSoftware", "Brave-Browser"),
            ]
        elif system == "Windows":
            local_app_data = os.environ.get("LOCALAPPDATA", os.path.join(home, "AppData", "Local"))
            alternatives = [
                os.path.join(local_app_data, "Google", "Chrome Canary", "User Data"),
                os.path.join(local_app_data, "Chromium", "User Data"),
                os.path.join(local_app_data, "Microsoft", "Edge", "User Data"),
                os.path.join(local_app_data, "BraveSoftware", "Brave-Browser", "User Data"),
            ]
            
        # Check each alternative
        for alt in alternatives:
            if os.path.exists(alt):
                base_dir = alt
                print(f"Using alternative browser profile directory: {base_dir}")
                break
    
    return os.path.join(base_dir, profile_name)


def get_google_cookies(chrome_dir: str, debug: bool = False) -> dict:
    """Get Google cookies from Chrome."""
    try:
        # Check if the cookies file exists
        cookie_file = os.path.join(chrome_dir, 'Cookies')
        if not os.path.exists(cookie_file):
            if debug:
                print(f"Cookie file not found at: {cookie_file}")
                # Check alternative locations (some browsers use Network/Cookies)
                alt_cookie_file = os.path.join(chrome_dir, 'Network', 'Cookies')
                if os.path.exists(alt_cookie_file):
                    print(f"Found alternative cookie file at: {alt_cookie_file}")
                    cookie_file = alt_cookie_file
                else:
                    print("No cookie file found in standard locations")
                    return {}
        
        if debug:
            print(f"Using cookie file: {cookie_file}")
            print(f"Cookie file exists: {os.path.exists(cookie_file)}")
            print(f"Cookie file size: {os.path.getsize(cookie_file) if os.path.exists(cookie_file) else 'N/A'} bytes")
        
        # Try to get cookies for multiple Google domains to ensure we get all required cookies
        domains = [
            'https://accounts.google.com',
            'https://google.com',
            'https://www.google.com',
            'https://notebooklm.google.com'
        ]
        
        all_cookies = {}
        success_count = 0
        
        for domain in domains:
            try:
                domain_cookies = chrome_cookies(domain, cookie_file=cookie_file)
                success_count += 1
                if debug:
                    print(f"Found {len(domain_cookies)} cookies for {domain}")
                    if domain_cookies:
                        print(f"Sample cookie names: {list(domain_cookies.keys())[:5]}")
                all_cookies.update(domain_cookies)
            except Exception as e:
                if debug:
                    print(f"Error getting cookies for {domain}: {str(e)}")
        
        if debug:
            print(f"Successfully retrieved cookies from {success_count}/{len(domains)} domains")
            print(f"Total cookies collected: {len(all_cookies)}")
        
        # Check for essential cookies
        if debug:
            essential_cookies = ['SID', 'HSID', 'SSID', 'APISID', 'SAPISID', '__Secure-1PSID']
            found = [c for c in essential_cookies if c in all_cookies]
            missing = [c for c in essential_cookies if c not in all_cookies]
            if missing:
                print(f"Warning: Missing essential cookies: {', '.join(missing)}")
                print(f"Found essential cookies: {', '.join(found)}")
            else:
                print("All essential Google cookies found!")
        
        return all_cookies
    except Exception as e:
        if debug:
            print(f"Error getting cookies: {str(e)}")
            import traceback
            traceback.print_exc()
        return {}


def get_auth_token_from_nlm(cookies: dict, debug: bool = False) -> str:
    """Get auth token from NotebookLM using cookies."""
    try:
        if debug:
            print(f"Making request to NotebookLM with {len(cookies)} cookies")
            
        # Make a request to NotebookLM
        response = requests.get('https://notebooklm.google.com', cookies=cookies)
        
        if debug:
            print(f"Response status code: {response.status_code}")
            print(f"Response headers: {response.headers}")
            
        if response.status_code != 200:
            if debug:
                print(f"Error accessing NotebookLM. Status code: {response.status_code}")
                print(f"Response body: {response.text[:500]}...")  # First 500 chars
            return ""
            
        # Check for redirects to login page
        if 'accounts.google.com' in response.url:
            if debug:
                print(f"Redirected to login page: {response.url}")
                print("This suggests the cookies aren't valid for authentication")
            return ""
        
        # Parse the HTML response
        soup = BeautifulSoup(response.text, 'html.parser')
        
        if debug:
            print(f"Response size: {len(response.text)} bytes")
            print(f"Title: {soup.title.string if soup.title else 'No title'}")
            print(f"Found {len(soup.find_all('script'))} script tags")
        
        # Look for script tags containing WIZ_global_data
        wiz_script = None
        for script in soup.find_all('script'):
            if script.string and 'WIZ_global_data' in script.string:
                wiz_script = script.string
                break
        
        if not wiz_script:
            if debug:
                print("No script tag with WIZ_global_data found")
                if len(response.text) > 1000:
                    print("Response is large. Saving first 1000 chars for debugging...")
                    print(response.text[:1000])
            return ""
        
        # Extract the auth token using regex - support both with and without window prefix
        match = re.search(r'(?:window\.)?WIZ_global_data\s*=\s*({.*?});', wiz_script, re.DOTALL)
        if not match:
            if debug:
                print("WIZ_global_data found but couldn't extract JSON")
                print(f"WIZ_global_data script content: {wiz_script[:200]}...")
            return ""
            
        # Try to get larger JSON block if first attempt fails
        if not match:
            # Fallback to more aggressive matching - find opening brace after WIZ_global_data
            start_idx = wiz_script.find('WIZ_global_data')
            if start_idx != -1:
                brace_idx = wiz_script.find('{', start_idx)
                if brace_idx != -1:
                    # Try to find matching closing brace
                    json_str = extract_json_object(wiz_script[brace_idx:])
                    if json_str:
                        # Try to parse this JSON
                        try:
                            wiz_data = json.loads(json_str)
                            if 'SNlM0e' in wiz_data:
                                return wiz_data['SNlM0e']
                        except json.JSONDecodeError:
                            if debug:
                                print("Failed to parse fallback JSON extraction")
                    else:
                        if debug:
                            print("Failed to extract JSON object with manual search")
            return ""
            
        # We found a match, try to parse it
        json_str = match.group(1)
        
        # Sometimes the JSON might have JavaScript-style comments or trailing commas
        # Try to clean it up a bit
        try:
            # First attempt with the raw match
            wiz_data = json.loads(json_str)
        except json.JSONDecodeError as e:
            if debug:
                print(f"Initial JSON parsing failed: {e}")
                print(f"Trying to clean up the JSON string...")
            
            try:
                # Try to clean up the JSON
                # Remove trailing commas in objects and arrays
                clean_json = re.sub(r',\s*([\]}])', r'\1', json_str)
                wiz_data = json.loads(clean_json)
            except json.JSONDecodeError as e:
                if debug:
                    print(f"Failed to parse cleaned JSON: {e}")
                    print(f"Extracted data: {json_str[:200]}...")
                
                # One last attempt - try to manually find the SNlM0e field
                snlm0e_match = re.search(r'"SNlM0e"\s*:\s*"([^"]+)"', json_str)
                if snlm0e_match:
                    if debug:
                        print(f"Found SNlM0e with direct regex: {snlm0e_match.group(1)[:10]}...")
                    return snlm0e_match.group(1)
                    
                return ""
        
        # Successfully parsed the JSON
        if debug:
            print(f"Successfully parsed WIZ_global_data JSON")
            print(f"WIZ_global_data keys: {', '.join(list(wiz_data.keys())[:10])}...")
            
        if 'SNlM0e' in wiz_data:
            if debug:
                print(f"Found auth token SNlM0e: {wiz_data['SNlM0e'][:10]}...")
            return wiz_data['SNlM0e']
        else:
            if debug:
                print("SNlM0e not found in WIZ_global_data keys")
                # Try to look for it in a nested structure
                for key, value in wiz_data.items():
                    if isinstance(value, dict) and 'SNlM0e' in value:
                        if debug:
                            print(f"Found SNlM0e in nested structure under key {key}")
                        return value['SNlM0e']
            return ""
        
        return ""
    except Exception as e:
        if debug:
            print(f"Error getting auth token: {str(e)}")
            import traceback
            traceback.print_exc()
        return ""


def load_stored_env() -> Tuple[Optional[str], Optional[str]]:
    """
    Load stored authentication information.
    
    Returns:
        Tuple of (auth_token, cookies)
    """
    home_dir = Path.home()
    env_file = home_dir / ".nlm" / "env"
    
    if not env_file.exists():
        return None, None
        
    auth_token = None
    cookies = None
    
    with open(env_file, "r") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
                
            key, value = line.split("=", 1)
            key = key.strip()
            value = value.strip()
            
            # Handle quoted values
            if value.startswith('"') and value.endswith('"'):
                value = value[1:-1]
                
            if key == "NLM_AUTH_TOKEN":
                auth_token = value
            elif key == "NLM_COOKIES":
                cookies = value
                
    return auth_token, cookies


def detect_auth_info(cmd: str) -> Tuple[str, str]:
    """
    Extract authentication information from HAR/curl command.
    
    Args:
        cmd: HAR/curl command string
        
    Returns:
        Tuple of (auth_token, cookies)
    """
    # Extract cookies
    cookie_match = re.search(r"-H ['\"]cookie: ([^'\"]+)['\"]", cmd)
    if not cookie_match:
        raise ValueError("No cookies found")
    cookies = cookie_match.group(1)
    
    # Extract auth token
    at_match = re.search(r"at=([^&\s]+)", cmd)
    if not at_match:
        raise ValueError("No auth token found")
    auth_token = at_match.group(1)
    
    persist_auth_to_disk(cookies, auth_token, "")
    return auth_token, cookies


def handle_auth(args=None, debug=False) -> Tuple[str, str, Optional[Exception]]:
    """
    Handle authentication flow using Chrome cookies.
    
    Args:
        args: Optional arguments
        debug: Whether to enable debug output
        
    Returns:
        Tuple of (auth_token, cookies, error)
    """
    import sys
    
    # Check if we're reading from stdin
    if not sys.stdin.isatty():
        # Parse HAR/curl from stdin
        input_data = sys.stdin.read()
        try:
            return detect_auth_info(input_data) + (None,)
        except Exception as e:
            return "", "", e
    
    # Use Chrome profile
    profile_name = os.environ.get("NLM_BROWSER_PROFILE", "Default")
    if args and len(args) > 0:
        profile_name = args[0]
        
    print(f"nlm: extracting authentication from Chrome profile: {profile_name}", file=sys.stderr)
    print(f"nlm: this requires you to be already logged into Google in Chrome", file=sys.stderr)
    print(f"nlm: (to use a different profile, set with NLM_BROWSER_PROFILE or pass as argument)", file=sys.stderr)
    
    chrome_dir = get_chrome_dir(profile_name)
    if debug:
        print(f"nlm: Chrome profile directory: {chrome_dir}", file=sys.stderr)
    
    if not os.path.exists(chrome_dir):
        print(f"nlm: Chrome profile directory not found: {chrome_dir}", file=sys.stderr)
        print(f"nlm: Check if Chrome is installed and the profile exists", file=sys.stderr)
        return "", "", Exception(f"Chrome profile not found: {chrome_dir}")
    
    cookie_file = os.path.join(chrome_dir, "Cookies")
    if not os.path.exists(cookie_file):
        print(f"nlm: Chrome cookies file not found: {cookie_file}", file=sys.stderr)
        print(f"nlm: Try using a different profile", file=sys.stderr)
        return "", "", Exception(f"Chrome cookies file not found: {cookie_file}")
    
    try:
        if debug:
            print(f"nlm: Attempting to extract cookies and auth token...", file=sys.stderr)
        auth_token, cookies = get_auth(profile_name=profile_name, debug=debug)
        
        if not cookies:
            print(f"nlm: Failed to extract cookies from Chrome", file=sys.stderr)
            print(f"nlm: Make sure you're logged into Google in Chrome", file=sys.stderr)
            return "", "", Exception("Failed to extract cookies")
            
        if not auth_token:
            print(f"nlm: Extracted cookies but failed to get auth token", file=sys.stderr)
            print(f"nlm: Try visiting NotebookLM in Chrome and ensure you're logged in", file=sys.stderr)
            return "", "", Exception("Failed to extract auth token")
        
        print(f"nlm: successfully extracted authentication data from Chrome", file=sys.stderr)
        if debug:
            print(f"nlm: cookies length: {len(cookies)}", file=sys.stderr)
            print(f"nlm: auth token length: {len(auth_token)}", file=sys.stderr)
        return persist_auth_to_disk(cookies, auth_token, profile_name) + (None,)
    except Exception as e:
        print(f"nlm: authentication failed: {str(e)}", file=sys.stderr)
        print(f"nlm: this might be due to Chrome profile access issues or security settings", file=sys.stderr)
        print(f"nlm: you can try again with a different profile using 'nlm auth <profile-name>'", file=sys.stderr)
        return "", "", e


def persist_auth_to_disk(cookies: str, auth_token: str, profile_name: str) -> Tuple[str, str]:
    """
    Save auth token and cookies to disk.
    
    Args:
        cookies: Browser cookies
        auth_token: Authentication token
        profile_name: Browser profile name
        
    Returns:
        Tuple of (auth_token, cookies)
    """
    import sys
    
    home_dir = Path.home()
    nlm_dir = home_dir / ".nlm"
    nlm_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
    
    env_file = nlm_dir / "env"
    content = f'NLM_COOKIES="{cookies}"\nNLM_AUTH_TOKEN="{auth_token}"\nNLM_BROWSER_PROFILE="{profile_name}"\n'
    
    env_file.write_text(content)
    env_file.chmod(0o600)
    
    print(f"nlm: auth info written to {env_file}", file=sys.stderr)
    return auth_token, cookies
