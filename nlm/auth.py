import asyncio # To be removed, but kept for now considering potential use elsewhere
import json
import logging
import os
import platform
import re
import shutil
import sys
import tempfile
import time
from pathlib import Path
from typing import Tuple, Optional, Dict, List

# Import Selenium and undetected-chromedriver
try:
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options as ChromeOptions
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.common.exceptions import TimeoutException, WebDriverException
    import undetected_chromedriver as uc
except ImportError:
    print("Error: selenium or undetected-chromedriver is not installed.", file=sys.stderr)
    print("Please install them using: uv pip install selenium undetected-chromedriver", file=sys.stderr)
    webdriver = None # For subsequent checks
    uc = None

# --- Helper Functions (Reusing profile path retrieval) ---

def _get_chrome_profile_path() -> Optional[Path]:
    """Get the default Chrome user data directory path based on the OS"""
    system = platform.system().lower()
    if system == "darwin":
        return Path.home() / "Library/Application Support/Google/Chrome"
    elif system == "linux":
        possible_paths = [
            Path.home() / ".config/google-chrome",
            Path.home() / ".config/chromium",
        ]
        for path in possible_paths:
            if path.is_dir():
                return path
        return None
    elif system == "windows":
        localappdata = os.getenv('LOCALAPPDATA')
        if localappdata:
            return Path(localappdata) / "Google/Chrome/User Data"
        return None
    else:
        return None

# Format according to the result of Selenium's get_cookies()
def _format_selenium_cookies(cookies: List[Dict]) -> str:
    """Format a list of Selenium cookies into an HTTP header string"""
    if not cookies:
        return ""
    # Selenium returns a list of dictionaries with 'name' and 'value' keys
    return "; ".join([f"{cookie['name']}={cookie['value']}" for cookie in cookies])

# --- Authentication process using Selenium ---

def _get_auth_with_selenium(profile_name: str = "Default", debug: bool = False) -> Tuple[str, str]:
    """Get authentication information from the target service using Selenium and undetected-chromedriver"""
    if not webdriver or not uc:
        raise ImportError("selenium or undetected-chromedriver is not installed or could not be imported.")

    source_profile_dir_base = _get_chrome_profile_path()
    if not source_profile_dir_base or not source_profile_dir_base.is_dir():
        raise FileNotFoundError(f"Chrome user data directory not found for this OS ({platform.system()}). Searched base: {source_profile_dir_base}")

    source_profile_dir = source_profile_dir_base / profile_name
    if not source_profile_dir.is_dir():
        raise FileNotFoundError(f"Chrome profile directory not found: {source_profile_dir}")

    if debug:
        print(f"Using source profile directory: {source_profile_dir}")

    driver = None # To be referenced in finally block
    with tempfile.TemporaryDirectory() as temp_dir_str:
        temp_dir = Path(temp_dir_str)
        target_profile_dir = temp_dir / "Default" # Is it okay to fix the profile name to Default?
        target_profile_dir.mkdir(parents=True, exist_ok=True)

        if debug:
            print(f"Using temporary directory: {temp_dir}")

        # --- Copy profile data (Same logic as Pyppeteer version) ---
        files_to_copy = ["Cookies", "Login Data", "Web Data"]
        for filename in files_to_copy:
            src = source_profile_dir / filename
            dst = target_profile_dir / filename
            if src.exists():
                try:
                    shutil.copy2(src, dst)
                    if debug:
                        print(f"Copied: {filename}")
                except Exception as e:
                    print(f"Warning: Failed to copy {filename}: {e}", file=sys.stderr)
            elif debug:
                print(f"Skipping non-existent file: {filename}")

        local_state_content = '{"os_crypt":{"encrypted_key":""}}'
        local_state_path = temp_dir / "Local State"
        try:
            local_state_path.write_text(local_state_content, encoding='utf-8')
            if debug:
                print("Created minimal Local State file.")
        except Exception as e:
            raise IOError(f"Failed to write Local State file: {e}")

        # --- Launch undetected-chromedriver ---
        options = uc.ChromeOptions()

        # Add flags set in Go implementation/Pyppeteer version
        options.add_argument(f'--user-data-dir={str(temp_dir)}') # Specify UserDataDir
        options.add_argument('--no-first-run')
        options.add_argument('--no-default-browser-check')
        options.add_argument('--disable-gpu') # Sometimes recommended for headless
        options.add_argument('--disable-extensions')
        options.add_argument('--disable-sync')
        options.add_argument('--disable-popup-blocking')
        options.add_argument('--window-size=1280,800')
        options.add_argument('--disable-hang-monitor')
        options.add_argument('--disable-ipc-flooding-protection')
        options.add_argument('--disable-prompt-on-repost')
        options.add_argument('--disable-renderer-backgrounding')
        options.add_argument('--force-color-profile=srgb')
        options.add_argument('--metrics-recording-only')
        options.add_argument('--safebrowsing-disable-auto-update')
        options.add_argument('--enable-automation') # May be unnecessary/harmful with undetected-chromedriver, but added for now
        options.add_argument('--password-store=basic')
        # options.add_argument('--no-sandbox') # Added previously, but commented out for now to observe

        # Temporarily changed to always launch in non-headless mode for debugging
        # if not debug:
        #     # options.add_argument('--headless') # Old headless mode
        #     options.add_argument('--headless=new') # Try the new headless mode

        # Spoof User Agent to normal Chrome (Headless detection countermeasure)
        user_agent = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117.0.0.0 Safari/537.36" # Example: Better to match the actual version
        options.add_argument(f'user-agent={user_agent}')


        if debug:
            print(f"Launching undetected-chromedriver with options...")
            # Skipping display as there are too many options

        try:
            # Launch WebDriver using undetected_chromedriver
            # Specify version_main to match the current Chrome version (found to be 134 from logs)
            # Temporarily remove use_subprocess=True to observe
            driver = uc.Chrome(options=options, version_main=134)

            if debug:
                print("Navigating to target service...")

            # --- Extract authentication information ---
            driver.get("https://notebooklm.google.com/") # Use the correct service URL

            if debug:
                print("Waiting for authentication data (WIZ_global_data)...")

            # Wait until WIZ_global_data is available (max 30 seconds)
            # Using WebDriverWait
            try:
                WebDriverWait(driver, 30).until(
                    lambda d: d.execute_script("return !!window.WIZ_global_data")
                )
            except TimeoutException:
                current_url = driver.current_url
                raise TimeoutError(f"Authentication data (WIZ_global_data) not found after 30 seconds. Current URL: {current_url}")

            if debug:
                print("Authentication data found. Extracting token and cookies...")

            # Get the token
            token = driver.execute_script("return window.WIZ_global_data.SNlM0e")

            # Get cookies
            cookies_list = driver.get_cookies() # Get cookies for the current domain and subdomains
            cookies_str = _format_selenium_cookies(cookies_list)

            if debug:
                print(f"Token extracted (length: {len(token) if token else 0})")
                print(f"Cookies extracted (length: {len(cookies_str)})")
                # Display retrieved cookies for debugging
                # print(f"Retrieved cookies: {cookies_list}")

            if not token or not cookies_str:
                 # Should it be okay if cookies are empty but token exists? Align with Go implementation.
                 # Go implementation checks both, so check both here as well.
                 raise ValueError("Failed to extract valid token or cookies.")

            return token, cookies_str

        except (WebDriverException, Exception) as e:
            print(f"Error during Selenium/uc operation: {e}", file=sys.stderr)
            import traceback
            traceback.print_exc()
            raise
        finally:
            if driver:
                driver.quit()
                if debug:
                    print("Browser closed.")
            # Temporary directory is automatically deleted when exiting the with block

# --- Synchronous wrapper function (Modified from Pyppeteer version) ---

def get_auth(profile_name: str = "Default", debug: bool = False) -> Tuple[str, str]:
    """
    Extract authentication information from Chrome using Selenium/undetected-chromedriver.
    """
    if debug:
        print(f"Starting authentication process for profile: {profile_name} using Selenium/uc")

    try:
        # Call the Selenium version function directly
        auth_token, cookies = _get_auth_with_selenium(profile_name, debug)
        return auth_token, cookies
    except ImportError as e:
        print(f"ImportError: {e}", file=sys.stderr)
        print("Falling back to loading stored credentials...", file=sys.stderr)
        return load_stored_env() or ("", "")
    except (FileNotFoundError, TimeoutError, ValueError, IOError, WebDriverException, Exception) as e:
        # Display error type and message even if not in debug mode
        print(f"Error during Selenium/uc authentication ({type(e).__name__}): {e}", file=sys.stderr)
        # if debug: # This if was unnecessary
        print("Selenium/uc authentication failed. Falling back to loading stored credentials...", file=sys.stderr)
        return load_stored_env() or ("", "")


# --- Existing helper functions (load_stored_env, detect_auth_info, save_auth_to_env, handle_auth can be reused) ---
# (Messages related to Pyppeteer within handle_auth need modification)

def load_stored_env() -> Optional[Tuple[str, str]]:
    """Load stored authentication information from ~/.nlm/env."""
    home_dir = Path.home()
    env_file = home_dir / ".nlm" / "env"

    if not env_file.exists():
        return None, None

    auth_token = None
    cookies = None

    try:
        with open(env_file, "r", encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue

                if "=" in line:
                    key, value = line.split("=", 1)
                    key = key.strip()
                    value = value.strip()

                    # Handle quoted values
                    if value.startswith('"') and value.endswith('"'):
                        value = value[1:-1]
                    elif value.startswith("'") and value.endswith("'"):
                         value = value[1:-1]

                    if key == "NLM_AUTH_TOKEN":
                        auth_token = value
                    elif key == "NLM_COOKIES":
                        cookies = value
    except Exception as e:
        print(f"Error reading env file {env_file}: {e}", file=sys.stderr)
        return None, None

    if auth_token and cookies:
        return auth_token, cookies
    else:
        return None, None


def detect_auth_info(cmd: str) -> Tuple[str, str]:
    """Extract authentication information from HAR/curl command."""
    cookie_re = re.compile(r'-H [\'"]cookie: ([^\'"]+)[\'"]')
    cookie_match = cookie_re.search(cmd)
    cookies = cookie_match.group(1) if cookie_match else ""

    at_re = re.compile(r'[?&;]at=([^&\s\'"]+)')
    at_match = at_re.search(cmd)
    auth_token = at_match.group(1) if at_match else ""

    if not auth_token:
        bearer_re = re.compile(r'-H [\'"]Authorization: Bearer ([^\'"]+)[\'"]')
        bearer_match = bearer_re.search(cmd)
        if bearer_match:
             auth_token = bearer_match.group(1)

    if not cookies or not auth_token:
        raise ValueError("Could not extract both cookies and auth token from the input.")

    try:
        save_auth_to_env(auth_token, cookies)
    except Exception as e:
        print(f"Warning: Failed to save extracted auth info to env file: {e}", file=sys.stderr)

    return auth_token, cookies


def save_auth_to_env(auth_token: str, cookies: str, profile_name: str = "Default") -> None:
    """Save authentication information to env file (~/.nlm/env)."""
    home_dir = Path.home()
    nlm_dir = home_dir / ".nlm"
    nlm_dir.mkdir(parents=True, exist_ok=True)
    env_file = nlm_dir / "env"

    existing_content = {}
    if env_file.exists():
        try:
            with open(env_file, "r", encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("#") or "=" not in line:
                        continue
                    key, value = line.split("=", 1)
                    existing_content[key.strip()] = value.strip()
        except Exception as e:
            print(f"Warning: Could not read existing env file {env_file}: {e}", file=sys.stderr)

    existing_content["NLM_COOKIES"] = f'"{cookies}"'
    existing_content["NLM_AUTH_TOKEN"] = f'"{auth_token}"'
    existing_content["NLM_BROWSER_PROFILE"] = f'"{profile_name}"'

    try:
        content_lines = [f"{key}={value}" for key, value in existing_content.items()]
        env_file.write_text("\n".join(content_lines) + "\n", encoding='utf-8')
    except Exception as e:
         print(f"Error writing to env file {env_file}: {e}", file=sys.stderr)
         raise


def handle_auth(args=None, debug=False) -> Tuple[Optional[str], Optional[str], Optional[Exception]]:
    """
    Handle authentication flow: try stdin, then Selenium/uc, then stored env.
    """
    # 1. Check stdin (unchanged)
    if not sys.stdin.isatty():
        if debug:
            print("Reading authentication info from stdin...")
        input_data = sys.stdin.read()
        try:
            auth_token, cookies = detect_auth_info(input_data)
            if debug:
                print("Successfully extracted auth info from stdin.")
            return auth_token, cookies, None
        except Exception as e:
            if debug:
                print(f"Failed to extract auth info from stdin: {e}")
            pass # Fall through

    # 2. Determine profile name and attempt browser auth via Selenium/uc
    profile_name = os.environ.get("NLM_BROWSER_PROFILE", "Default")
    if args and len(args) > 0:
        profile_name = args[0]

    # Modify message
    print(f"nlm: Attempting to extract authentication from Chrome profile: '{profile_name}' using Selenium/uc...", file=sys.stderr)
    print(f"nlm: This requires you to be logged into Google in that Chrome profile.", file=sys.stderr)
    print(f"nlm: (To use a different profile, set NLM_BROWSER_PROFILE or pass it as an argument)", file=sys.stderr)

    try:
        # get_auth now calls _get_auth_with_selenium internally
        auth_token, cookies = get_auth(profile_name, debug)

        if auth_token and cookies:
            try:
                save_auth_to_env(auth_token, cookies, profile_name)
                if debug:
                    print(f"Authentication info saved for profile '{profile_name}'.")
            except Exception as e:
                 print(f"Warning: Failed to save auth info to env file: {e}", file=sys.stderr)
            return auth_token, cookies, None
        else:
            # get_auth failed (Selenium/uc failed AND stored env was empty/failed)
            return None, None, Exception(f"Failed to extract authentication using Selenium/uc for profile '{profile_name}' and could not load stored credentials.")

    except Exception as e:
        if debug:
            print(f"Unexpected error during handle_auth: {e}")
            import traceback
            traceback.print_exc()
        return None, None, e
