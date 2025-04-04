import json
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Union

from .batchexecute import Client as BatchExecuteClient, Config, RPC, Response


# RPC endpoint IDs for NotebookLM services
# NotebookLM service - Project/Notebook operations
RPC_LIST_RECENTLY_VIEWED_PROJECTS = "wXbhsf"  # ListRecentlyViewedProjects
RPC_CREATE_PROJECT = "CCqFvf"  # CreateProject
RPC_GET_PROJECT = "rLM1Ne"  # GetProject
RPC_DELETE_PROJECTS = "WWINqb"  # DeleteProjects
RPC_MUTATE_PROJECT = "s0tc2d"  # MutateProject
RPC_REMOVE_RECENTLY_VIEWED = "fejl7e"  # RemoveRecentlyViewedProject

# NotebookLM service - Source operations
RPC_ADD_SOURCES = "izAoDd"  # AddSources
RPC_DELETE_SOURCES = "tGMBJ"  # DeleteSources
RPC_MUTATE_SOURCE = "b7Wfje"  # MutateSource
RPC_REFRESH_SOURCE = "FLmJqe"  # RefreshSource
RPC_LOAD_SOURCE = "hizoJc"  # LoadSource
RPC_CHECK_SOURCE_FRESHNESS = "yR9Yof"  # CheckSourceFreshness
RPC_ACT_ON_SOURCES = "yyryJe"  # ActOnSources

# NotebookLM service - Note operations
RPC_CREATE_NOTE = "CYK0Xb"  # CreateNote
RPC_MUTATE_NOTE = "cYAfTb"  # MutateNote
RPC_DELETE_NOTES = "AH0mwd"  # DeleteNotes
RPC_GET_NOTES = "cFji9"  # GetNotes

# NotebookLM service - Audio operations
RPC_CREATE_AUDIO_OVERVIEW = "AHyHrd"  # CreateAudioOverview
RPC_GET_AUDIO_OVERVIEW = "VUsiyb"  # GetAudioOverview
RPC_DELETE_AUDIO_OVERVIEW = "sJDbic"  # DeleteAudioOverview
RPC_SHARE_AUDIO = "RGP97b"  # ShareAudio

# NotebookLM service - Generation operations
RPC_GENERATE_DOCUMENT_GUIDES = "tr032e"  # GenerateDocumentGuides
RPC_GENERATE_NOTEBOOK_GUIDE = "VfAZjd"  # GenerateNotebookGuide
RPC_GENERATE_OUTLINE = "lCjAd"  # GenerateOutline
RPC_GENERATE_SECTION = "BeTrYd"  # GenerateSection
RPC_START_DRAFT = "exXvGf"  # StartDraft
RPC_START_SECTION = "pGC7gf"  # StartSection


@dataclass
class Call:
    """Represents a NotebookLM RPC call."""
    id: str  # RPC endpoint ID
    args: List[Any]  # Arguments for the call
    notebook_id: str = ""  # Optional notebook ID for context


class Client:
    """Client for NotebookLM RPC communication."""
    def __init__(self, auth_token: str, cookies: str, debug: bool = False):
        self.config = Config(
            host="notebooklm.google.com",
            app="LabsTailwindUi",
            auth_token=auth_token,
            cookies=cookies,
            debug=debug,
            headers={
                "content-type": "application/x-www-form-urlencoded;charset=UTF-8",
                "origin": "https://notebooklm.google.com",
                "referer": "https://notebooklm.google.com/",
                "x-same-domain": "1",
                "accept": "*/*",
                "accept-language": "en-US,en;q=0.9",
                "cache-control": "no-cache",
                "pragma": "no-cache",
            },
            url_params={
                "bl": "boq_labs-tailwind-frontend_20241114.01_p0",
                "f.sid": "-7121977511756781186",
                "hl": "en",
            }
        )
        self.client = BatchExecuteClient(self.config)
        self.debug = debug

    def do(self, call: Call) -> json.loads:
        """Execute a NotebookLM RPC call."""
        if self.debug:
            print("\n=== RPC Call ===")
            print(f"ID: {call.id}")
            print(f"NotebookID: {call.notebook_id}")
            print(f"Args: {call.args}")

        # Create request-specific URL parameters
        url_params = {}
        for k, v in self.config.url_params.items():
            url_params[k] = v

        if call.notebook_id:
            url_params["source-path"] = f"/notebook/{call.notebook_id}"
        else:
            url_params["source-path"] = "/"

        rpc = RPC(
            id=call.id,
            args=call.args,
            index="generic",
            url_params=url_params
        )

        if self.debug:
            print("\nRPC Request:")
            print(rpc)

        resp = self.client.do(rpc)
        
        if self.debug:
            print("\nRPC Response:")
            print(resp)

        # Parse the response data if it's a string
        if isinstance(resp.data, str):
            try:
                return json.loads(resp.data)
            except json.JSONDecodeError:
                return resp.data
        
        return resp.data
