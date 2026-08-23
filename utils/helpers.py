import os
from tkinter import filedialog
from typing import Optional

# MIME-type magic bytes (content sniffing)
# Maps common file extensions to their expected magic byte signatures.
# Used to validate that the actual file content matches the declared extension.

MAGIC_BYTES: dict[str, list[tuple[bytes, int]]] = {
    "pdf": [(b"%PDF", 0)],
    "png": [(b"\x89PNG\r\n\x1a\n", 0)],
    "jpg": [(b"\xff\xd8\xff", 0)],
    "jpeg": [(b"\xff\xd8\xff", 0)],
    "gif": [(b"GIF8", 0)],
    "xlsx": [(b"PK\x03\x04", 0)],
    "docx": [(b"PK\x03\x04", 0)],
    "csv": [],  # Plain text — no reliable magic bytes
    "txt": [],
}


def _check_magic_bytes(file_path: str, ext: str) -> bool:
    """Validate file content matches expected magic bytes for *ext*.

    Reads the first 16 bytes of the file and checks against known
    signatures. Returns ``True`` if the content matches or if the
    extension has no known signatures (e.g. CSV).
    """
    signatures = MAGIC_BYTES.get(ext, [])
    if not signatures:
        return True  # No signature to check (CSV, TXT, etc.)

    try:
        with open(file_path, "rb") as f:
            header = f.read(16)
        return any(header[offset : offset + len(sig)] == sig for sig, offset in signatures)
    except OSError:
        return False


class Helpers:
    @staticmethod
    def format_currency(amount: float) -> str:
        """Format *amount* as Indian Rupee currency string."""
        return f"₹{amount:,.2f}"

    @staticmethod
    def upload_file(
        allowed_extensions: set[str],
        max_size_mb: float,
    ) -> tuple[str | None, str | None]:
        """Open a file dialog and validate the selected file.

        Returns
        -------
        tuple[Optional[str], Optional[str]]
            ``(file_path, error_message)`` — exactly one is non-None.
        """
        file_path = filedialog.askopenfilename(
            title="Select File",
            filetypes=[("Allowed files", f"*.{ext}") for ext in allowed_extensions],
        )
        if not file_path:
            return None, "No file selected."

        ext = file_path.split(".")[-1].lower()
        if ext not in allowed_extensions:
            return None, f"Invalid file type. Allowed: {', '.join(allowed_extensions)}"

        size_mb = os.path.getsize(file_path) / (1024 * 1024)
        if size_mb > max_size_mb:
            return None, f"File too large. Max allowed: {max_size_mb} MB"

        # MIME-type content sniffing (magic bytes)
        if not _check_magic_bytes(file_path, ext):
            return (
                None,
                f"File content does not match the expected format for .{ext}. "
                f"The file may be corrupted or misnamed.",
            )

        return file_path, None
