from pydantic import BaseModel


class TreeNode(BaseModel):
    name: str
    path: str
    file_count: int
    total_file_count: int
    folders: list["TreeNode"]
    files: list[str]
