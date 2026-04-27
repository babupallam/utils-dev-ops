class YTSubtitleError(Exception):
    """Base exception for YouTube subtitle application errors."""


class TranscriptNotFoundError(YTSubtitleError):
    """Raised when a transcript cannot be found for a video."""


class SearchLimitExceeded(YTSubtitleError):
    """Raised when the requested search limit exceeds the configured maximum."""


class SearchServiceError(YTSubtitleError):
    """Raised when the search service fails."""


class ArchiveServiceError(YTSubtitleError):
    """Raised when ZIP archive creation fails."""


class ConfigFileError(YTSubtitleError):
    """Raised when the configuration file is invalid or unreadable."""