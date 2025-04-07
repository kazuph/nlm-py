import json
import random
import re
import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple, Union, Callable
import requests
from ..api.models import *


class UnauthorizedError(Exception):
    """Raised when the client is not authorized to make the request."""
    pass


class BatchExecuteError(Exception):
    """Raised when a batch execute request fails."""
    def __init__(self, status_code: int, message: str, response: Optional[requests.Response] = None):
        self.status_code = status_code
        self.message = message
        self.response = response
        super().__init__(f"BatchExecute error: {message} (status: {status_code})")


@dataclass
class Config:
    """Configuration for batch execute requests."""
    host: str
    app: str
    auth_token: str
    cookies: str
    headers: Dict[str, str] = None
    url_params: Dict[str, str] = None
    debug: bool = False
    use_http: bool = False

    def __post_init__(self):
        if self.headers is None:
            self.headers = {}
        if self.url_params is None:
            self.url_params = {}


@dataclass
class RPC:
    """Represents an RPC request."""
    id: str
    args: List[Any]
    index: str = "generic"
    url_params: Dict[str, str] = None

    def __post_init__(self):
        if self.url_params is None:
            self.url_params = {}


@dataclass
class Response:
    """Represents an RPC response."""
    id: str
    data: Any
    index: int = 0
    error: str = ""


class ReqIDGenerator:
    """Generates sequential request IDs."""
    def __init__(self):
        self.base = random.randint(1000, 9999)
        self.sequence = 0

    def next(self) -> str:
        """Returns the next request ID in sequence."""
        reqid = self.base + (self.sequence * 100000)
        self.sequence += 1
        return str(reqid)

    def reset(self):
        """Resets the sequence counter but keeps the same base."""
        self.sequence = 0


class Client:
    """Client for executing batch requests."""
    def __init__(self, config: Config, http_client=None):
        self.config = config
        self.http_client = http_client or requests.Session()
        self.reqid = ReqIDGenerator()
        self.debug = self._debug if config.debug else lambda *args, **kwargs: None

    def _debug(self, *args, **kwargs):
        """Print debug information."""
        print("DEBUG:", *args, **kwargs)

    def do(self, rpc: RPC) -> Response:
        """Execute a single RPC call."""
        return self.execute([rpc])

    def build_rpc_data(self, rpc: RPC) -> List[Any]:
        """Convert RPC to batchexecute format."""
        # Always JSON encode the arguments list for the f.req payload
        args_json = json.dumps(rpc.args)
        return [rpc.id, args_json, None, "generic"]

    def execute(self, rpcs: List[RPC]) -> Response:
        """Execute a batch of RPC calls."""
        # Construct URL
        scheme = "http" if self.config.use_http else "https"
        url = f"{scheme}://{self.config.host}/_/{self.config.app}/data/batchexecute"

        # Add query parameters
        params = dict(self.config.url_params)
        params["rpcids"] = ",".join([rpc.id for rpc in rpcs])
        params["rt"] = "c"
        params["_reqid"] = self.reqid.next()

        # Add any request-specific params
        if rpcs and rpcs[0].url_params:
            params.update(rpcs[0].url_params)

        if self.config.debug:
            self.debug(f"URL: {url}")
            self.debug(f"Params: {params}")

        # Build request body
        envelope = []
        for rpc in rpcs:
            envelope.append(self.build_rpc_data(rpc))

        req_body = json.dumps([envelope])
        form_data = {
            "f.req": req_body,
            "at": self.config.auth_token
        }

        if self.config.debug:
            self.debug(f"Request Body: {form_data}")
            self.debug(f"Decoded Request Body: {req_body}")

        # Set headers
        headers = {
            "content-type": "application/x-www-form-urlencoded;charset=UTF-8"
        }
        headers.update(self.config.headers)
        headers["cookie"] = self.config.cookies

        if self.config.debug:
            self.debug(f"Request Headers: {headers}")

        # Execute request
        response = self.http_client.post(
            url, 
            params=params, 
            data=form_data, 
            headers=headers
        )

        if response.status_code != 200:
            if response.status_code == 401:
                raise UnauthorizedError("Unauthorized request")
            raise BatchExecuteError(
                response.status_code,
                f"Request failed: {response.status_code} {response.reason}",
                response
            )

        body = response.text
        if self.config.debug:
            self.debug(f"Response Status: {response.status_code}")
            self.debug(f"Response Body: {body[:200]}...")

        # Parse chunked response
        try:
            responses = self.decode_chunked_response(body)
        except Exception as e:
            self.debug(f"Failed to decode chunked response: {e}")
            # Fallback to regular response parsing
            responses = self.decode_response(body)

        if not responses:
            raise BatchExecuteError(
                response.status_code,
                "No valid responses found",
                response
            )

        return responses[0]

    def decode_response(self, raw: str) -> List[Response]:
        """Decode a non-chunked batchexecute response."""
        raw = raw.lstrip(")]}'")
        if not raw:
            raise BatchExecuteError(0, "Empty response after trimming prefix")

        try:
            data = json.loads(raw)
        except json.JSONDecodeError as e:
            raise BatchExecuteError(0, f"Invalid JSON: {e}")

        responses = []
        for rpc_data in data:
            if len(rpc_data) < 7:
                continue

            rpc_type = rpc_data[0]
            if not isinstance(rpc_type, str) or rpc_type != "wrb.fr":
                continue

            resp = Response(
                id=rpc_data[1],
                data=rpc_data[2] if rpc_data[2] is not None else None
            )

            if rpc_data[6] == "generic":
                resp.index = 0
            elif isinstance(rpc_data[6], str):
                try:
                    resp.index = int(rpc_data[6])
                except ValueError:
                    pass

            responses.append(resp)

        return responses

    def decode_chunked_response(self, raw: str) -> List[Response]:
        """Decode a chunked batchexecute response."""
        raw = raw.lstrip(")]}'").strip()
        if not raw:
            raise BatchExecuteError(0, "Empty response after trimming prefix")

        responses = []
        lines = raw.split('\n')
        i = 0

        while i < len(lines):
            # Read the length line
            length_str = lines[i].strip()
            i += 1

            # Skip empty lines
            if not length_str:
                continue

            try:
                total_length = int(length_str)
            except ValueError:
                self.debug(f"Invalid length string: {length_str}")
                raise BatchExecuteError(0, "Invalid chunk length: invalid syntax")

            # Get the chunk content
            if i >= len(lines):
                raise BatchExecuteError(0, "Incomplete chunk")

            chunk = lines[i]
            i += 1

            try:
                rpc_batch = json.loads(chunk)
            except json.JSONDecodeError:
                # Try unescaping the JSON string first
                try:
                    unescaped = json.loads(f'"{chunk}"')
                    rpc_batch = json.loads(unescaped)
                except (json.JSONDecodeError, ValueError):
                    self.debug(f"Failed to parse chunk: {chunk[:50]}...")
                    continue

            # Process each RPC response in the batch
            for rpc_data in rpc_batch:
                if len(rpc_data) < 7:
                    self.debug(f"Skipping short RPC data: {rpc_data}")
                    continue

                rpc_type = rpc_data[0]
                if not isinstance(rpc_type, str) or rpc_type != "wrb.fr":
                    self.debug(f"Skipping non-wrb.fr RPC: {rpc_data[0]}")
                    continue

                resp = Response(
                    id=rpc_data[1],
                    data=None
                )

                # Handle data
                if rpc_data[2] is not None:
                    if isinstance(rpc_data[2], str):
                        try:
                            data = json.loads(rpc_data[2])
                            resp.data = json.dumps(data)  # Re-encode for consistent format
                        except json.JSONDecodeError:
                            # Try unescaping first
                            try:
                                unescaped = json.loads(f'"{rpc_data[2]}"')
                                data = json.loads(unescaped)
                                resp.data = json.dumps(data)
                            except (json.JSONDecodeError, ValueError):
                                resp.data = rpc_data[2]

                # Handle index
                if rpc_data[6] == "generic":
                    resp.index = 0
                elif isinstance(rpc_data[6], str):
                    try:
                        resp.index = int(rpc_data[6])
                    except ValueError:
                        pass

                responses.append(resp)

        if not responses:
            raise BatchExecuteError(0, "No valid responses found")

        return responses
