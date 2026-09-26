def text_with_attachment_labels(filenames: list[str], caption: str) -> str:
    labels = "\n".join(f"[вложение: {filename}]" for filename in filenames)
    return f"{labels}\n\n{caption}" if caption else labels
