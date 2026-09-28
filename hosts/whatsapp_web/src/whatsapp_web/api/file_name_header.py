from urllib.parse import quote


def file_name_header(file_name: str) -> str:
    return "UTF-8''" + quote(file_name, safe="")
