"""File Tools - Deep Agents SDK file operations wrapper.

This module provides file operation tools that wrap the MCP filesystem server,
exposing convenient functions for agents to read, write, and search files.
"""

import logging
from pathlib import Path
from typing import Optional, List, Dict, Any
import json
import csv

logger = logging.getLogger(__name__)


def read_file(file_path: str, file_type: str = "auto") -> Any:
    """Read a file and return its contents.

    This wraps the MCP filesystem server's read_csv tool and adds support
    for other file types.

    Args:
        file_path: Path to the file to read
        file_type: Type of file ("csv", "json", "txt", "auto")
                   Auto will detect based on extension

    Returns:
        File contents in appropriate format:
        - CSV: List of dictionaries
        - JSON: Parsed JSON object
        - TXT: String content

    Raises:
        FileNotFoundError: If file doesn't exist
        ValueError: If file type is unsupported
    """
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    # Auto-detect file type
    if file_type == "auto":
        ext = path.suffix.lower()
        if ext == ".csv":
            file_type = "csv"
        elif ext == ".json":
            file_type = "json"
        elif ext in [".txt", ".md", ".log"]:
            file_type = "txt"
        else:
            raise ValueError(f"Cannot auto-detect file type for: {file_path}")

    logger.info(f"Reading {file_type} file: {file_path}")

    try:
        if file_type == "csv":
            with open(path, 'r', newline='', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                data = list(reader)
                logger.debug(f"Read {len(data)} rows from CSV")
                return data

        elif file_type == "json":
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                logger.debug(f"Read JSON file with {len(data) if isinstance(data, (list, dict)) else 0} items")
                return data

        elif file_type == "txt":
            with open(path, 'r', encoding='utf-8') as f:
                content = f.read()
                logger.debug(f"Read {len(content)} characters from text file")
                return content

        else:
            raise ValueError(f"Unsupported file type: {file_type}")

    except Exception as e:
        logger.error(f"Failed to read file {file_path}: {e}")
        raise


def write_file(
    file_path: str,
    content: Any,
    file_type: str = "auto",
    mode: str = "overwrite"
) -> str:
    """Write content to a file.

    This wraps the MCP filesystem server's write_po_document tool and adds
    support for other file types.

    Args:
        file_path: Path where file should be written
        content: Content to write (format depends on file_type)
        file_type: Type of file ("csv", "json", "txt", "auto")
        mode: Write mode ("overwrite", "append")

    Returns:
        Path to the written file

    Raises:
        ValueError: If file type is unsupported or content format is invalid
    """
    path = Path(file_path)

    # Auto-detect file type
    if file_type == "auto":
        ext = path.suffix.lower()
        if ext == ".csv":
            file_type = "csv"
        elif ext == ".json":
            file_type = "json"
        elif ext in [".txt", ".md", ".log"]:
            file_type = "txt"
        else:
            raise ValueError(f"Cannot auto-detect file type for: {file_path}")

    # Create parent directory if needed
    path.parent.mkdir(parents=True, exist_ok=True)

    logger.info(f"Writing {file_type} file: {file_path} (mode: {mode})")

    try:
        if file_type == "json":
            write_mode = 'a' if mode == "append" else 'w'
            with open(path, write_mode, encoding='utf-8') as f:
                json.dump(content, f, indent=2)
                logger.debug(f"Wrote JSON content to {file_path}")

        elif file_type == "csv":
            if not isinstance(content, list) or not content:
                raise ValueError("CSV content must be a non-empty list of dictionaries")

            write_mode = 'a' if mode == "append" else 'w'
            with open(path, write_mode, newline='', encoding='utf-8') as f:
                fieldnames = content[0].keys()
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                if mode != "append" or not path.exists():
                    writer.writeheader()
                writer.writerows(content)
                logger.debug(f"Wrote {len(content)} rows to CSV")

        elif file_type == "txt":
            write_mode = 'a' if mode == "append" else 'w'
            with open(path, write_mode, encoding='utf-8') as f:
                f.write(str(content))
                logger.debug(f"Wrote {len(str(content))} characters to text file")

        else:
            raise ValueError(f"Unsupported file type: {file_type}")

        return str(path)

    except Exception as e:
        logger.error(f"Failed to write file {file_path}: {e}")
        raise


def search_files(
    directory: str,
    pattern: str = "*",
    recursive: bool = True,
    file_type: Optional[str] = None
) -> List[str]:
    """Search for files matching a pattern.

    Args:
        directory: Directory to search in
        pattern: Glob pattern (e.g., "*.csv", "po_*")
        recursive: Whether to search recursively
        file_type: Optional file type filter (e.g., ".csv", ".json")

    Returns:
        List of matching file paths (as strings)
    """
    dir_path = Path(directory)
    if not dir_path.exists():
        logger.warning(f"Directory not found: {directory}")
        return []

    logger.info(f"Searching for files in {directory}: {pattern} (recursive={recursive})")

    try:
        if recursive:
            matches = dir_path.rglob(pattern)
        else:
            matches = dir_path.glob(pattern)

        # Filter by file type if specified
        if file_type:
            matches = [p for p in matches if p.suffix.lower() == file_type.lower()]
        else:
            matches = list(matches)

        # Convert to strings and filter for files only
        file_paths = [str(p) for p in matches if p.is_file()]

        logger.info(f"Found {len(file_paths)} matching files")
        return sorted(file_paths)

    except Exception as e:
        logger.error(f"Failed to search files in {directory}: {e}")
        return []


def list_directory(directory: str, files_only: bool = False) -> List[Dict[str, Any]]:
    """List contents of a directory.

    Args:
        directory: Directory to list
        files_only: If True, only include files (not directories)

    Returns:
        List of dictionaries with file/directory information:
        - name: File/directory name
        - path: Full path
        - is_file: Boolean indicating if it's a file
        - size: Size in bytes (for files)
    """
    dir_path = Path(directory)
    if not dir_path.exists():
        logger.warning(f"Directory not found: {directory}")
        return []

    logger.info(f"Listing directory: {directory} (files_only={files_only})")

    try:
        items = []
        for item in dir_path.iterdir():
            if files_only and not item.is_file():
                continue

            info = {
                "name": item.name,
                "path": str(item),
                "is_file": item.is_file()
            }

            if item.is_file():
                info["size"] = item.stat().st_size

            items.append(info)

        logger.debug(f"Found {len(items)} items in directory")
        return sorted(items, key=lambda x: x["name"])

    except Exception as e:
        logger.error(f"Failed to list directory {directory}: {e}")
        return []


def file_exists(file_path: str) -> bool:
    """Check if a file exists.

    Args:
        file_path: Path to check

    Returns:
        True if file exists, False otherwise
    """
    return Path(file_path).is_file()


def get_file_info(file_path: str) -> Optional[Dict[str, Any]]:
    """Get information about a file.

    Args:
        file_path: Path to the file

    Returns:
        Dictionary with file information or None if file doesn't exist:
        - name: File name
        - path: Full path
        - size: Size in bytes
        - extension: File extension
        - exists: Boolean
    """
    path = Path(file_path)

    info = {
        "name": path.name,
        "path": str(path),
        "extension": path.suffix,
        "exists": path.exists()
    }

    if path.exists() and path.is_file():
        info["size"] = path.stat().st_size

    return info
