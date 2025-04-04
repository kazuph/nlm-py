from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional, Union
from datetime import datetime


class SourceType(Enum):
    SOURCE_TYPE_UNSPECIFIED = 0
    SOURCE_TYPE_UNKNOWN = 1
    SOURCE_TYPE_GOOGLE_DOCS = 3
    SOURCE_TYPE_GOOGLE_SLIDES = 4
    SOURCE_TYPE_GOOGLE_SHEETS = 5
    SOURCE_TYPE_LOCAL_FILE = 6
    SOURCE_TYPE_WEB_PAGE = 7
    SOURCE_TYPE_SHARED_NOTE = 8
    SOURCE_TYPE_YOUTUBE_VIDEO = 9


class SourceStatus(Enum):
    SOURCE_STATUS_UNSPECIFIED = 0
    SOURCE_STATUS_ENABLED = 1
    SOURCE_STATUS_DISABLED = 2
    SOURCE_STATUS_ERROR = 3


class SourceIssueReason(Enum):
    REASON_UNSPECIFIED = 0
    REASON_TEMPORARY_SERVER_ERROR = 1
    REASON_PERMANENT_SERVER_ERROR = 2
    REASON_INVALID_SOURCE_ID = 3
    REASON_SOURCE_NOT_FOUND = 4
    REASON_UNSUPPORTED_MIME_TYPE = 5
    REASON_YOUTUBE_ERROR_GENERIC = 6
    REASON_YOUTUBE_ERROR_UNLISTED = 7
    REASON_YOUTUBE_ERROR_PRIVATE = 8
    REASON_YOUTUBE_ERROR_MEMBERS_ONLY = 9
    REASON_YOUTUBE_ERROR_LOGIN_REQUIRED = 10
    REASON_GOOGLE_DOCS_ERROR_GENERIC = 11
    REASON_GOOGLE_DOCS_ERROR_NO_ACCESS = 12
    REASON_GOOGLE_DOCS_ERROR_UNKNOWN = 13
    REASON_DOWNLOAD_FAILURE = 14
    REASON_UNKNOWN = 15


@dataclass
class SourceId:
    source_id: str


@dataclass
class GoogleDocsSourceMetadata:
    document_id: str


@dataclass
class YoutubeSourceMetadata:
    youtube_url: str
    video_id: str


@dataclass
class SourceMetadata:
    source_type: SourceType = SourceType.SOURCE_TYPE_UNSPECIFIED
    last_update_time_seconds: Optional[int] = None
    last_modified_time: Optional[datetime] = None
    google_docs: Optional[GoogleDocsSourceMetadata] = None
    youtube: Optional[YoutubeSourceMetadata] = None


@dataclass
class SourceSettings:
    status: SourceStatus = SourceStatus.SOURCE_STATUS_UNSPECIFIED


@dataclass
class SourceIssue:
    reason: SourceIssueReason = SourceIssueReason.REASON_UNSPECIFIED


@dataclass
class Source:
    source_id: SourceId
    title: str
    metadata: Optional[SourceMetadata] = None
    settings: Optional[SourceSettings] = None
    warnings: List[int] = field(default_factory=list)


@dataclass
class ProjectMetadata:
    user_role: int = 0
    session_active: bool = False
    create_time: Optional[datetime] = None
    modified_time: Optional[datetime] = None
    type: int = 0
    is_starred: bool = False


@dataclass
class Project:
    title: str
    project_id: str
    emoji: str
    sources: List[Source] = field(default_factory=list)
    metadata: Optional[ProjectMetadata] = None


@dataclass
class AudioOverviewResult:
    project_id: str
    audio_id: str = ""
    title: str = ""
    audio_data: str = ""  # Base64 encoded audio data
    is_ready: bool = False

    def get_audio_bytes(self):
        """Returns the decoded audio data as bytes."""
        if not self.audio_data:
            raise ValueError("No audio data available")
        import base64
        return base64.b64decode(self.audio_data)


@dataclass
class ShareAudioResult:
    share_url: str
    share_id: str
    is_public: bool


@dataclass
class DocumentGuide:
    content: str


@dataclass
class GetNotesResponse:
    notes: List[Source] = field(default_factory=list)


@dataclass
class GenerateDocumentGuidesResponse:
    guides: List[DocumentGuide] = field(default_factory=list)


@dataclass
class GenerateNotebookGuideResponse:
    content: str


@dataclass
class GenerateOutlineResponse:
    content: str


@dataclass
class GenerateSectionResponse:
    content: str
