import json
import os
import re
import platform
import subprocess
import sys
from pathlib import Path
from typing import Tuple, Optional, Dict, List


def get_auth(profile_name: str = "Default", debug: bool = False) -> Tuple[str, str]:
    """
    Extract authentication information from Chrome using the Go nlm-auth binary.
    
    Args:
        profile_name: Browser profile name to use
        debug: Whether to enable debug output
        
    Returns:
        Tuple of (auth_token, cookies)
    """
    try:
        # Determine the path to the Go binary based on platform and architecture
        binary_path = get_go_binary_path()
        
        if debug:
            print(f"Using Go binary at: {binary_path}")
            print(f"Binary exists: {os.path.exists(binary_path)}")
        
        # Execute the Go binary for authentication
        cmd = [binary_path]
        if profile_name != "Default":
            cmd.append(profile_name)
            
        if debug:
            cmd.append("--debug")
            
        if debug:
            print(f"Executing command: {' '.join(cmd)}")
            
        # Run the command and get output
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode != 0:
            if debug:
                print(f"Go binary execution failed with return code {result.returncode}")
                print(f"Error output: {result.stderr}")
            return "", ""
            
        # 標準出力から最後のJSONオブジェクトを抽出
        stdout = result.stdout
        if debug:
            print(f"Stdout length: {len(stdout)}")
            print(f"First 100 chars: {stdout[:100]}")
            print(f"Last 100 chars: {stdout[-100:] if len(stdout) > 100 else stdout}")
            
        # 最後のJSONオブジェクトを探す ('{...}' パターン)
        json_pattern = r'({[^{]*})'
        json_matches = re.findall(json_pattern, stdout)
        
        if not json_matches:
            if debug:
                print("No JSON object found in output")
            # 環境変数ファイルから認証情報を読み込む
            return load_stored_env() or ("", "")
            
        # 最後のJSONオブジェクトを取得
        last_json = json_matches[-1]
        
        if debug:
            print(f"Found potential JSON: {last_json[:50]}...")
            
        # Parse the output which should be JSON with auth_token and cookies
        try:
            output_data = json.loads(last_json)
            auth_token = output_data.get("auth_token", "")
            cookies = output_data.get("cookies", "")
            
            if debug:
                print(f"Auth token length: {len(auth_token)}")
                print(f"Cookies length: {len(cookies)}")
                
            # 認証情報が取得できたらそれを返す
            if auth_token and cookies:
                return auth_token, cookies
                
            # 取得できなかった場合は環境変数ファイルから読み込む
            return load_stored_env() or ("", "")
            
        except json.JSONDecodeError:
            if debug:
                print(f"Failed to parse JSON output from Go binary")
                print(f"Output: {last_json[:100]}...")
            # 環境変数ファイルから認証情報を読み込む
            return load_stored_env() or ("", "")
            
    except Exception as e:
        if debug:
            print(f"Error in get_auth: {str(e)}")
            import traceback
            traceback.print_exc()
        # 環境変数ファイルから認証情報を読み込む
        return load_stored_env() or ("", "")


def get_go_binary_path() -> str:
    """
    Get the path to the Go nlm-auth binary for the current platform and architecture.
    
    Returns:
        Path to the Go binary
    """
    # Get the directory where this Python module is located
    module_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Determine platform-specific binary name
    system = platform.system().lower()
    machine = platform.machine().lower()
    
    # Map common architecture names
    if machine in ["x86_64", "amd64"]:
        arch = "amd64"
    elif machine in ["arm64", "aarch64"]:
        arch = "arm64"
    elif machine in ["i386", "i686", "x86"]:
        arch = "386"
    else:
        arch = machine
    
    # Construct binary name with platform suffix
    binary_name = f"nlm-auth-{system}-{arch}"
    if system == "windows":
        binary_name += ".exe"
    
    # Full path to the binary
    binary_path = os.path.join(module_dir, "bin", binary_name)
    
    return binary_path


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
        cmd: HAR or curl command
        
    Returns:
        Tuple of (auth_token, cookies)
    """
    # Extract cookies
    cookie_re = re.compile(r'-H [\'"]cookie: ([^\'"]+)[\'"]')
    cookie_match = cookie_re.search(cmd)
    if not cookie_match:
        return "", ""
    cookies = cookie_match.group(1)
    
    # Extract auth token
    at_re = re.compile(r'at=([^&\s]+)')
    at_match = at_re.search(cmd)
    if not at_match:
        return "", ""
    auth_token = at_match.group(1)
    
    # Save to env file if able
    try:
        save_auth_to_env(auth_token, cookies)
    except Exception:
        pass
        
    return auth_token, cookies


def save_auth_to_env(auth_token: str, cookies: str, profile_name: str = "Default") -> None:
    """
    Save authentication information to env file.
    
    Args:
        auth_token: Authentication token
        cookies: Cookies
        profile_name: Browser profile name
    """
    home_dir = Path.home()
    nlm_dir = home_dir / ".nlm"
    nlm_dir.mkdir(parents=True, exist_ok=True)
    
    env_file = nlm_dir / "env"
    
    content = f'NLM_COOKIES="{cookies}"\n'
    content += f'NLM_AUTH_TOKEN="{auth_token}"\n'
    content += f'NLM_BROWSER_PROFILE="{profile_name}"\n'
    
    env_file.write_text(content)
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
    
    try:
        auth_token, cookies = get_auth(profile_name, debug)
        if not auth_token or not cookies:
            return "", "", Exception("Failed to extract cookies")
            
        # 認証情報をenvファイルに保存
        save_auth_to_env(auth_token, cookies, profile_name)
            
        return auth_token, cookies, None
    except Exception as e:
        return "", "", e
