from src.task_manager.protocols.i_task_change_feed import ITaskChangeFeed
from src.task_manager.protocols.i_task_closer import ITaskCloser
from src.task_manager.protocols.i_task_manager_identity import ITaskManagerIdentity
from src.task_manager.protocols.i_task_reader import ITaskReader
from src.task_manager.protocols.i_task_search import ITaskSearch
from src.task_manager.protocols.i_task_writer import ITaskWriter

__all__ = [
    "ITaskChangeFeed",
    "ITaskCloser",
    "ITaskManagerIdentity",
    "ITaskReader",
    "ITaskSearch",
    "ITaskWriter",
]
