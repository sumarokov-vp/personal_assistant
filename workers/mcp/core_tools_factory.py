from pathlib import Path

from ai_framework import BaseTool

from src.ai_tools.dropbox_read import DropboxReadTool
from src.ai_tools.dropbox_search import DropboxSearchTool
from src.ai_tools.dropbox_tree import DropboxTreeTool
from src.ai_tools.find_tasks import FindTasksTool
from src.ai_tools.read_task import ReadTaskTool
from src.ai_tools.transcript_read import TranscriptReadTool
from src.dropbox.services.boundary.dropbox_access_policy import DropboxAccessPolicy
from src.dropbox.services.boundary.dropbox_boundary import DropboxBoundary
from src.dropbox.services.boundary.dropbox_folder_writer import DropboxFolderWriter
from src.dropbox.services.reader.dropbox_reader import DropboxReader
from src.dropbox.services.search.dropbox_search import DropboxSearch
from src.dropbox.services.tree.dropbox_tree import DropboxTree
from src.files.readers.file_text_reader import FileTextReader
from src.todoist.services.todoist_task_reader import TodoistTaskReader
from src.todoist.services.todoist_task_reader.protocols import ITodoistReadClient
from src.voice_recognition.services.timecoded_transcript import TimecodedTranscript
from workers.mcp.core_settings import DEFAULT_RECORDINGS_FOLDER


def build_core_tools(
    todoist: ITodoistReadClient,
    dropbox_root: Path,
    recordings_folder: str = DEFAULT_RECORDINGS_FOLDER,
) -> list[BaseTool]:
    boundary = build_dropbox_boundary(dropbox_root)
    recordings = DropboxFolderWriter(boundary=boundary, folder=recordings_folder)
    return [
        *build_task_tools(todoist),
        *build_dropbox_tools(boundary),
        *build_transcript_tools(boundary),
        *build_recording_tools(recordings),
    ]


def build_task_tools(todoist: ITodoistReadClient) -> list[BaseTool]:
    tasks = TodoistTaskReader(todoist)
    return [FindTasksTool(finder=tasks), ReadTaskTool(reader=tasks)]


def build_dropbox_boundary(root: Path) -> DropboxBoundary:
    if not root.is_dir():
        raise ValueError(f"DROPBOX_ROOT={root} is not a directory")
    return DropboxBoundary(root=root, policy=DropboxAccessPolicy())


def build_dropbox_tools(boundary: DropboxBoundary) -> list[BaseTool]:
    return [
        DropboxTreeTool(tree_builder=DropboxTree(boundary=boundary)),
        DropboxSearchTool(finder=DropboxSearch(boundary=boundary)),
        DropboxReadTool(
            reader=DropboxReader(boundary=boundary, text_reader=FileTextReader())
        ),
    ]


def build_transcript_tools(boundary: DropboxBoundary) -> list[BaseTool]:
    return [
        TranscriptReadTool(storage=boundary, transcript_factory=TimecodedTranscript)
    ]


def build_recording_tools(recordings: DropboxFolderWriter) -> list[BaseTool]:
    return []
