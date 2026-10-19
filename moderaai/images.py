"""Checking an upload really is an image we accept."""


def image_type(data: bytes) -> str | None:
    # Decide the type from the file's first bytes, not from its name or the browser's claim.
    if data.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "image/webp"
    return None
