import base64
import json
import os
import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple, Union, BinaryIO
import requests
from io import BytesIO
from urllib.parse import urlparse, parse_qs

from .rpc import Client as RPCClient, Call
from .models import *


class Client:
    """Client for NotebookLM API interactions."""
    def __init__(self, auth_token: str, cookies: str, debug: bool = False):
        self.rpc = RPCClient(auth_token, cookies, debug)
        self.debug = debug

    # Project/Notebook operations
    def list_recently_viewed_projects(self) -> List[Project]:
        """List all recently viewed notebooks."""
        from .rpc import RPC_LIST_RECENTLY_VIEWED_PROJECTS
        
        resp = self.rpc.do(Call(
            id=RPC_LIST_RECENTLY_VIEWED_PROJECTS,
            args=[None, 1]
        ))
        
        if not resp or not isinstance(resp, list) or len(resp) < 1:
            return []
        
        projects = []
        
        # The response structure from the API is complex, so let's handle that appropriately
        # This matches how the Go implementation processes it
        for project_data in resp[0]:
            if not project_data or len(project_data) < 4:
                continue
                
            title, sources_data, project_id, emoji = project_data[:4]
            metadata = None
            
            # Handle metadata if present
            if len(project_data) > 5 and project_data[5]:
                meta_data = project_data[5]
                if isinstance(meta_data, list) and len(meta_data) > 7:
                    metadata = ProjectMetadata(
                        user_role=meta_data[0] if len(meta_data) > 0 else 0,
                        session_active=meta_data[1] if len(meta_data) > 1 else False,
                        type=meta_data[6] if len(meta_data) > 6 else 0,
                        is_starred=meta_data[7] if len(meta_data) > 7 else False
                    )
                    
                    # Parse timestamps if present
                    # Modified time
                    if len(meta_data) > 5 and isinstance(meta_data[5], list) and len(meta_data[5]) > 1:
                        seconds, nanos = meta_data[5][0], meta_data[5][1]
                        from datetime import datetime
                        metadata.modified_time = datetime.fromtimestamp(seconds + (nanos / 1e9))
                    
                    # Create time
                    if len(meta_data) > 8 and isinstance(meta_data[8], list) and len(meta_data[8]) > 1:
                        seconds, nanos = meta_data[8][0], meta_data[8][1]
                        from datetime import datetime
                        metadata.create_time = datetime.fromtimestamp(seconds + (nanos / 1e9))
            
            # Parse sources - but don't add them to the notebook object for list command
            # This matches the Go implementation which doesn't load sources for the list command
            sources = []
            if self.debug and sources_data and isinstance(sources_data, list):
                print(f"Found {len(sources_data)} sources for notebook {project_id}")
            
            projects.append(Project(
                title=title,
                project_id=project_id,
                emoji=emoji,
                sources=sources,
                metadata=metadata
            ))
            
        return projects

    def create_project(self, title: str, emoji: str) -> Project:
        """Create a new notebook."""
        from .rpc import RPC_CREATE_PROJECT
        
        resp = self.rpc.do(Call(
            id=RPC_CREATE_PROJECT,
            args=[title, emoji]
        ))
        
        if not resp or not isinstance(resp, list) or len(resp) < 3:
            raise ValueError("Invalid response format")
            
        project_id = resp[2]
        
        return Project(
            title=title,
            project_id=project_id,
            emoji=emoji
        )

    def get_project(self, project_id: str) -> Project:
        """Get a notebook by ID."""
        from .rpc import RPC_GET_PROJECT
        
        resp = self.rpc.do(Call(
            id=RPC_GET_PROJECT,
            args=[project_id],
            notebook_id=project_id
        ))
        
        if self.debug:
            print(f"GET_PROJECT response: {resp}")
        
        if not resp or not isinstance(resp, list) or len(resp) < 1:
            raise ValueError(f"Invalid response format: {resp}")
            
        # The response structure is different than expected
        # The response is actually a list with one item, which is itself a list
        project_data = resp[0]
        
        if not project_data or not isinstance(project_data, list) or len(project_data) < 4:
            raise ValueError(f"Invalid project data: {project_data}")
            
        title, sources_data, project_id, emoji = project_data[:4]
        
        # Handle metadata if present
        metadata = None
        if len(project_data) > 4 and project_data[4] is not None:
            meta_list = project_data[4]
            if isinstance(meta_list, list) and len(meta_list) > 7:
                metadata = ProjectMetadata(
                    user_role=meta_list[0] if len(meta_list) > 0 else 0,
                    session_active=meta_list[1] if len(meta_list) > 1 else False,
                    type=meta_list[6] if len(meta_list) > 6 else 0,
                    is_starred=meta_list[7] if len(meta_list) > 7 else False
                )
                
                # Parse timestamps if present
                if len(meta_list) > 5 and isinstance(meta_list[5], list) and len(meta_list[5]) > 1:
                    seconds, nanos = meta_list[5][0], meta_list[5][1]
                    from datetime import datetime
                    metadata.modified_time = datetime.fromtimestamp(seconds + (nanos / 1e9))
                    
                if len(meta_list) > 8 and isinstance(meta_list[8], list) and len(meta_list[8]) > 1:
                    seconds, nanos = meta_list[8][0], meta_list[8][1]
                    from datetime import datetime
                    metadata.create_time = datetime.fromtimestamp(seconds + (nanos / 1e9))
        
        # Parse sources with additional debug and error handling
        sources = []
        if sources_data and isinstance(sources_data, list):
            if self.debug:
                print(f"Processing {len(sources_data)} sources")
                
            for source_data in sources_data:
                if not source_data:
                    if self.debug:
                        print("Skipping empty source data")
                    continue
                    
                if self.debug:
                    print(f"Source data: {source_data}")
                    
                if not isinstance(source_data, list) or len(source_data) < 2:
                    if self.debug:
                        print(f"Skipping invalid source data format: {source_data}")
                    continue
                    
                source_id_data = source_data[0]
                title = source_data[1]
                
                source_id = None
                if source_id_data and isinstance(source_id_data, list) and len(source_id_data) > 0:
                    source_id = SourceId(source_id=source_id_data[0])
                else:
                    if self.debug:
                        print(f"Invalid source ID format: {source_id_data}")
                    continue
                
                # Create basic source
                source = Source(
                    source_id=source_id,
                    title=title
                )
                
                # Add metadata if available (at index 2)
                if len(source_data) > 2 and source_data[2]:
                    metadata = source_data[2]
                    if isinstance(metadata, list) and len(metadata) > 2:
                        source_metadata = SourceMetadata()
                        
                        # Add more metadata processing as needed
                        if len(metadata) > 4 and metadata[4]:
                            try:
                                source_type_value = int(metadata[4])
                                source_metadata.source_type = SourceType(source_type_value)
                            except (ValueError, TypeError):
                                if self.debug:
                                    print(f"Invalid source type: {metadata[4]}")
                                
                        source.metadata = source_metadata
                        
                # Add settings if available (at index 3)
                if len(source_data) > 3 and source_data[3]:
                    settings_data = source_data[3]
                    if isinstance(settings_data, list) and len(settings_data) > 1:
                        settings = SourceSettings()
                        try:
                            status_value = int(settings_data[1])
                            settings.status = SourceStatus(status_value)
                        except (ValueError, TypeError):
                            if self.debug:
                                print(f"Invalid status value: {settings_data[1]}")
                        source.settings = settings
                
                sources.append(source)
        
        return Project(
            title=title,
            project_id=project_id,
            emoji=emoji,
            sources=sources
        )

    def delete_projects(self, project_ids: List[str]) -> None:
        """Delete notebooks by IDs."""
        from .rpc import RPC_DELETE_PROJECTS
        
        self.rpc.do(Call(
            id=RPC_DELETE_PROJECTS,
            args=[project_ids]
        ))

    # Source operations
    def delete_sources(self, project_id: str, source_ids: List[str]) -> None:
        """Delete sources from a notebook."""
        from .rpc import RPC_DELETE_SOURCES
        
        self.rpc.do(Call(
            id=RPC_DELETE_SOURCES,
            args=[
                [[[source_ids]]],
            ],
            notebook_id=project_id
        ))

    def mutate_source(self, source_id: str, updates: Dict[str, Any]) -> Source:
        """Update a source."""
        from .rpc import RPC_MUTATE_SOURCE
        
        resp = self.rpc.do(Call(
            id=RPC_MUTATE_SOURCE,
            args=[source_id, updates]
        ))
        
        # Parse response to Source object
        if not resp or not isinstance(resp, list) or len(resp) < 2:
            raise ValueError("Invalid response format")
            
        source_id_data = resp[0]
        title = resp[1]
        
        source_id_obj = None
        if source_id_data and isinstance(source_id_data, list) and len(source_id_data) > 0:
            source_id_obj = SourceId(source_id=source_id_data[0])
        
        return Source(
            source_id=source_id_obj,
            title=title
        )

    def refresh_source(self, source_id: str) -> Source:
        """Refresh a source."""
        from .rpc import RPC_REFRESH_SOURCE
        
        resp = self.rpc.do(Call(
            id=RPC_REFRESH_SOURCE,
            args=[source_id]
        ))
        
        # Parse response to Source object
        if not resp or not isinstance(resp, list) or len(resp) < 2:
            raise ValueError("Invalid response format")
            
        source_id_data = resp[0]
        title = resp[1]
        
        source_id_obj = None
        if source_id_data and isinstance(source_id_data, list) and len(source_id_data) > 0:
            source_id_obj = SourceId(source_id=source_id_data[0])
        
        return Source(
            source_id=source_id_obj,
            title=title
        )

    # Source upload utility methods
    def add_source_from_reader(self, project_id: str, reader: BinaryIO, filename: str) -> str:
        """Add a source from a file-like object."""
        content = reader.read()
        content_type = self._detect_content_type(content, filename)
        
        if content_type.startswith('text/'):
            return self.add_source_from_text(project_id, content.decode('utf-8'), filename)
        
        encoded = base64.b64encode(content).decode('utf-8')
        return self.add_source_from_base64(project_id, encoded, filename, content_type)
    
    def _detect_content_type(self, content: bytes, filename: str) -> str:
        """Detect content type from file content and name."""
        # Simple detection based on file extension
        if filename.lower().endswith(('.txt', '.md')):
            return 'text/plain'
        elif filename.lower().endswith(('.html', '.htm')):
            return 'text/html'
        elif filename.lower().endswith(('.pdf')):
            return 'application/pdf'
        elif filename.lower().endswith(('.doc', '.docx')):
            return 'application/msword'
        elif filename.lower().endswith(('.xls', '.xlsx')):
            return 'application/vnd.ms-excel'
        
        # Try to detect from content
        import mimetypes
        content_type = mimetypes.guess_type(filename)[0]
        if content_type:
            return content_type
            
        # Default to binary
        return 'application/octet-stream'

    def add_source_from_text(self, project_id: str, content: str, title: str) -> str:
        """Add a text source to a notebook."""
        from .rpc import RPC_ADD_SOURCES
        
        resp = self.rpc.do(Call(
            id=RPC_ADD_SOURCES,
            notebook_id=project_id,
            args=[
                [
                    [
                        None,
                        [title, content],
                        None,
                        2,  # text source type
                    ]
                ],
                project_id
            ]
        ))
        
        source_id = self._extract_source_id(resp)
        return source_id

    def add_source_from_base64(self, project_id: str, content: str, filename: str, content_type: str) -> str:
        """Add a binary source to a notebook."""
        from .rpc import RPC_ADD_SOURCES
        
        resp = self.rpc.do(Call(
            id=RPC_ADD_SOURCES,
            notebook_id=project_id,
            args=[
                [
                    [
                        content,
                        filename,
                        content_type,
                        "base64",
                    ]
                ],
                project_id
            ]
        ))
        
        source_id = self._extract_source_id(resp)
        return source_id

    def add_source_from_file(self, project_id: str, filepath: str) -> str:
        """Add a source from a file."""
        with open(filepath, 'rb') as f:
            return self.add_source_from_reader(project_id, f, os.path.basename(filepath))

    def add_source_from_url(self, project_id: str, url: str) -> str:
        """Add a source from a URL."""
        # Check if it's a YouTube URL first
        if self._is_youtube_url(url):
            video_id = self._extract_youtube_video_id(url)
            if not video_id:
                raise ValueError("Invalid YouTube URL")
                
            # Use dedicated YouTube method
            return self.add_youtube_source(project_id, video_id)
        
        # Regular URL handling
        from .rpc import RPC_ADD_SOURCES
        
        resp = self.rpc.do(Call(
            id=RPC_ADD_SOURCES,
            notebook_id=project_id,
            args=[
                [
                    [
                        None,
                        None,
                        [url],
                    ]
                ],
                project_id
            ]
        ))
        
        source_id = self._extract_source_id(resp)
        return source_id

    def add_youtube_source(self, project_id: str, video_id: str) -> str:
        """Add a YouTube source to a notebook."""
        from .rpc import RPC_ADD_SOURCES
        
        if self.debug:
            print("=== AddYouTubeSource ===")
            print(f"Project ID: {project_id}")
            print(f"Video ID: {video_id}")
        
        # Modified payload structure for YouTube
        payload = [
            [
                [
                    None,  # content
                    None,  # title
                    video_id,  # video ID (not in array)
                    None,  # unused
                    SourceType.SOURCE_TYPE_YOUTUBE_VIDEO.value,  # source type
                ]
            ],
            project_id
        ]
        
        if self.debug:
            print("\nPayload Structure:")
            print(payload)
        
        resp = self.rpc.do(Call(
            id=RPC_ADD_SOURCES,
            notebook_id=project_id,
            args=payload
        ))
        
        if self.debug:
            print(f"\nRaw Response: {resp}")
        
        if not resp:
            raise ValueError("Empty response from server (check debug output for request details)")
        
        source_id = self._extract_source_id(resp)
        return source_id

    def _extract_source_id(self, resp: Any) -> str:
        """Extract source ID from response with better error handling."""
        if not resp:
            raise ValueError("Empty response")
        
        if not isinstance(resp, list):
            raise ValueError(f"Expected list response, got {type(resp)}")
            
        # Try different response formats
        # Format 1: [[[["id",...]]]]
        # Format 2: [[["id",...]]]]
        # Format 3: [["id",...]]
        
        # Format 1
        if len(resp) > 0 and isinstance(resp[0], list) and len(resp[0]) > 0:
            if isinstance(resp[0][0], list) and len(resp[0][0]) > 0:
                if isinstance(resp[0][0][0], list) and len(resp[0][0][0]) > 0:
                    if isinstance(resp[0][0][0][0], str):
                        return resp[0][0][0][0]
        
        # Format 2
        if len(resp) > 0 and isinstance(resp[0], list) and len(resp[0]) > 0:
            if isinstance(resp[0][0], list) and len(resp[0][0]) > 0:
                if isinstance(resp[0][0][0], str):
                    return resp[0][0][0]
        
        # Format 3
        if len(resp) > 0 and isinstance(resp[0], list) and len(resp[0]) > 0:
            if isinstance(resp[0][0], str):
                return resp[0][0]
                
        raise ValueError(f"Could not find source ID in response structure: {resp}")

    # Helper methods for YouTube URLs
    def _is_youtube_url(self, url: str) -> bool:
        """Check if a URL is a YouTube URL."""
        return 'youtube.com' in url or 'youtu.be' in url

    def _extract_youtube_video_id(self, url: str) -> Optional[str]:
        """Extract YouTube video ID from URL."""
        # youtu.be URLs
        if 'youtu.be' in url:
            parts = urlparse(url)
            return parts.path.strip('/')
            
        # youtube.com URLs
        if 'youtube.com' in url and '/watch' in url:
            parts = urlparse(url)
            query = parse_qs(parts.query)
            return query.get('v', [''])[0]
            
        return None

    # Note operations
    def create_note(self, project_id: str, title: str, initial_content: str = "") -> Source:
        """Create a new note in a notebook."""
        from .rpc import RPC_CREATE_NOTE
        
        resp = self.rpc.do(Call(
            id=RPC_CREATE_NOTE,
            args=[
                project_id,
                initial_content,
                [1],  # note type
                None,
                title,
            ],
            notebook_id=project_id
        ))
        
        # Parse response to Source object
        if not resp or not isinstance(resp, list) or len(resp) < 2:
            raise ValueError("Invalid response format")
            
        source_id_data = resp[0]
        title = resp[1]
        
        source_id_obj = None
        if source_id_data and isinstance(source_id_data, list) and len(source_id_data) > 0:
            source_id_obj = SourceId(source_id=source_id_data[0])
        
        return Source(
            source_id=source_id_obj,
            title=title
        )

    def mutate_note(self, project_id: str, note_id: str, content: str, title: str) -> Source:
        """Update a note."""
        from .rpc import RPC_MUTATE_NOTE
        
        resp = self.rpc.do(Call(
            id=RPC_MUTATE_NOTE,
            args=[
                project_id,
                note_id,
                [[[content, title, []]]],
            ],
            notebook_id=project_id
        ))
        
        # Parse response to Source object
        if not resp or not isinstance(resp, list) or len(resp) < 2:
            raise ValueError("Invalid response format")
            
        source_id_data = resp[0]
        title = resp[1]
        
        source_id_obj = None
        if source_id_data and isinstance(source_id_data, list) and len(source_id_data) > 0:
            source_id_obj = SourceId(source_id=source_id_data[0])
        
        return Source(
            source_id=source_id_obj,
            title=title
        )

    def delete_notes(self, project_id: str, note_ids: List[str]) -> None:
        """Delete notes from a notebook."""
        from .rpc import RPC_DELETE_NOTES
        
        self.rpc.do(Call(
            id=RPC_DELETE_NOTES,
            args=[
                [[[note_ids]]],
            ],
            notebook_id=project_id
        ))

    def get_notes(self, project_id: str) -> List[Source]:
        """Get all notes in a notebook."""
        from .rpc import RPC_GET_NOTES
        
        resp = self.rpc.do(Call(
            id=RPC_GET_NOTES,
            args=[project_id],
            notebook_id=project_id
        ))
        
        if not resp or not isinstance(resp, list) or len(resp) < 1:
            return []
            
        notes = []
        # Parse response to list of Source objects
        for note_data in resp[0]:
            if not note_data or len(note_data) < 2:
                continue
                
            source_id_data = note_data[0]
            title = note_data[1]
            
            source_id_obj = None
            if source_id_data and isinstance(source_id_data, list) and len(source_id_data) > 0:
                source_id_obj = SourceId(source_id=source_id_data[0])
            
            notes.append(Source(
                source_id=source_id_obj,
                title=title
            ))
            
        return notes

    # Audio operations
    def create_audio_overview(self, project_id: str, instructions: str) -> AudioOverviewResult:
        """Create an audio overview of a notebook."""
        from .rpc import RPC_CREATE_AUDIO_OVERVIEW
        
        if not project_id:
            raise ValueError("Project ID required")
        if not instructions:
            raise ValueError("Instructions required")
            
        resp = self.rpc.do(Call(
            id=RPC_CREATE_AUDIO_OVERVIEW,
            args=[
                project_id,
                0,
                [instructions],
            ],
            notebook_id=project_id
        ))
        
        result = AudioOverviewResult(project_id=project_id)
        
        # Handle empty or nil response
        if not resp or not isinstance(resp, list) or len(resp) < 3:
            return result
            
        # Parse the wrb.fr response format
        # Format: [null,null,[3,"<base64-audio>","<id>","<title>",null,true],null,[false]]
        audio_data = resp[2]
        if not audio_data or not isinstance(audio_data, list) or len(audio_data) < 4:
            # Creation might be in progress, return result without error
            return result
            
        # Extract audio data (index 1)
        if len(audio_data) > 1 and isinstance(audio_data[1], str):
            result.audio_data = audio_data[1]
            
        # Extract ID (index 2)
        if len(audio_data) > 2 and isinstance(audio_data[2], str):
            result.audio_id = audio_data[2]
            
        # Extract title (index 3)
        if len(audio_data) > 3 and isinstance(audio_data[3], str):
            result.title = audio_data[3]
            
        # Extract ready status (index 5)
        if len(audio_data) > 5 and isinstance(audio_data[5], bool):
            result.is_ready = audio_data[5]
            
        return result

    def get_audio_overview(self, project_id: str) -> AudioOverviewResult:
        """Get an audio overview of a notebook."""
        from .rpc import RPC_GET_AUDIO_OVERVIEW
        
        resp = self.rpc.do(Call(
            id=RPC_GET_AUDIO_OVERVIEW,
            args=[
                project_id,
                1,
            ],
            notebook_id=project_id
        ))
        
        result = AudioOverviewResult(project_id=project_id)
        
        # Handle empty or nil response
        if not resp or not isinstance(resp, list) or len(resp) < 3:
            return result
            
        # Parse the wrb.fr response format
        # Format: [null,null,[3,"<base64-audio>","<id>","<title>",null,true],null,[false]]
        audio_data = resp[2]
        if not audio_data or not isinstance(audio_data, list) or len(audio_data) < 4:
            raise ValueError("Invalid audio data format")
            
        # Extract audio data (index 1)
        if len(audio_data) > 1 and isinstance(audio_data[1], str):
            result.audio_data = audio_data[1]
            
        # Extract ID (index 2)
        if len(audio_data) > 2 and isinstance(audio_data[2], str):
            result.audio_id = audio_data[2]
            
        # Extract title (index 3)
        if len(audio_data) > 3 and isinstance(audio_data[3], str):
            result.title = audio_data[3]
            
        # Extract ready status (index 5)
        if len(audio_data) > 5 and isinstance(audio_data[5], bool):
            result.is_ready = audio_data[5]
            
        return result

    def delete_audio_overview(self, project_id: str) -> None:
        """Delete an audio overview from a notebook."""
        from .rpc import RPC_DELETE_AUDIO_OVERVIEW
        
        self.rpc.do(Call(
            id=RPC_DELETE_AUDIO_OVERVIEW,
            args=[project_id],
            notebook_id=project_id
        ))

    # Sharing options
    class ShareOption:
        PRIVATE = 0
        PUBLIC = 1

    def share_audio(self, project_id: str, share_option: int) -> ShareAudioResult:
        """Share an audio overview with optional public access."""
        from .rpc import RPC_SHARE_AUDIO
        
        resp = self.rpc.do(Call(
            id=RPC_SHARE_AUDIO,
            args=[
                [share_option],
                project_id,
            ],
            notebook_id=project_id
        ))
        
        result = ShareAudioResult(
            share_url="",
            share_id="",
            is_public=(share_option == self.ShareOption.PUBLIC)
        )
        
        # Extract share URL and ID from response
        if resp and isinstance(resp, list) and len(resp) > 0:
            share_data = resp[0]
            if isinstance(share_data, list) and len(share_data) > 0:
                if isinstance(share_data[0], str):
                    result.share_url = share_data[0]
                if len(share_data) > 1 and isinstance(share_data[1], str):
                    result.share_id = share_data[1]
                    
        return result

    # Generation operations
    def generate_notebook_guide(self, project_id: str) -> GenerateNotebookGuideResponse:
        """Generate a notebook guide."""
        from .rpc import RPC_GENERATE_NOTEBOOK_GUIDE
        
        resp = self.rpc.do(Call(
            id=RPC_GENERATE_NOTEBOOK_GUIDE,
            args=[project_id],
            notebook_id=project_id
        ))
        
        # Parse response
        if not resp or not isinstance(resp, list) or len(resp) < 1:
            return GenerateNotebookGuideResponse(content="")
            
        content = resp[0] if isinstance(resp[0], str) else ""
        return GenerateNotebookGuideResponse(content=content)

    def generate_outline(self, project_id: str) -> GenerateOutlineResponse:
        """Generate a content outline."""
        from .rpc import RPC_GENERATE_OUTLINE
        
        resp = self.rpc.do(Call(
            id=RPC_GENERATE_OUTLINE,
            args=[project_id],
            notebook_id=project_id
        ))
        
        # Parse response
        if not resp or not isinstance(resp, list) or len(resp) < 1:
            return GenerateOutlineResponse(content="")
            
        content = resp[0] if isinstance(resp[0], str) else ""
        return GenerateOutlineResponse(content=content)

    def generate_section(self, project_id: str) -> GenerateSectionResponse:
        """Generate a new section."""
        from .rpc import RPC_GENERATE_SECTION
        
        resp = self.rpc.do(Call(
            id=RPC_GENERATE_SECTION,
            args=[project_id],
            notebook_id=project_id
        ))
        
        # Parse response
        if not resp or not isinstance(resp, list) or len(resp) < 1:
            return GenerateSectionResponse(content="")
            
        content = resp[0] if isinstance(resp[0], str) else ""
        return GenerateSectionResponse(content=content)
