from pathlib import Path

from ai_framework import BaseTool

from src.ai_tools.dropbox_read import DropboxReadTool
from src.ai_tools.dropbox_search import DropboxSearchTool
from src.ai_tools.dropbox_tree import DropboxTreeTool
from src.ai_tools.find_tasks import FindTasksTool
from src.ai_tools.read_task import ReadTaskTool
from src.dropbox.services.boundary.dropbox_access_policy import DropboxAccessPolicy
from src.dropbox.services.boundary.dropbox_boundary import DropboxBoundary
from src.dropbox.services.reader.dropbox_reader import DropboxReader
from src.dropbox.services.search.dropbox_search import DropboxSearch
from src.dropbox.services.tree.dropbox_tree import DropboxTree
from src.files.readers.file_text_reader import FileTextReader
from src.todoist.services.todoist_task_reader import TodoistTaskReader
from src.todoist.services.todoist_task_reader.protocols import ITodoistReadClient


def build_core_tools(todoist: ITodoistReadClient, dropbox_root: Path) -> list[BaseTool]:
    return [*build_task_tools(todoist), *build_dropbox_tools(dropbox_root)]


def build_task_tools(todoist: ITodoistReadClient) -> list[BaseTool]:
    tasks = TodoistTaskReader(todoist)
    return [FindTasksTool(finder=tasks), ReadTaskTool(reader=tasks)]


def build_dropbox_tools(root: Path) -> list[BaseTool]:
    if not root.is_dir():
        raise ValueError(f"DROPBOX_ROOT={root} is not a directory")
    boundary = DropboxBoundary(root=root, policy=DropboxAccessPolicy())
    return [
        DropboxTreeTool(tree_builder=DropboxTree(boundary=boundary)),
        DropboxSearchTool(finder=DropboxSearch(boundary=boundary)),
        DropboxReadTool(
            reader=DropboxReader(boundary=boundary, text_reader=FileTextReader())
        ),
    ]
