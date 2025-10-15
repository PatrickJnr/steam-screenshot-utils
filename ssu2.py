"""
SSU: Steam Screenshot Utils - Improved Version.

A comprehensive tool for managing Steam screenshots with enhanced features,
better error handling, and improved performance.

Usage:
    ssu backup <steam_user_folder> [-o <output_folder>] [-q|--quiet] [-n|--dry-run]
    ssu sort <screenshots_folder> [-q|--quiet] [-n|--dry-run]
    ssu merge <compressed_screenshots> <uncompressed_screenshots> [-q|--quiet] [-n|--dry-run]
    ssu rename <screenshots_folder> [-q|--quiet] [-n|--dry-run] [-u|--update] [-f|--force]
    ssu update [-q|--quiet]
    ssu gallery [-o <output_html>] [-d <screenshots_dir>] [-q|--quiet]

Options:
    -o <output_folder>    Specify the output folder for backups [default: backup].
    -q, --quiet          Suppress non-error output.
    -n, --dry-run        Simulate the operation without making changes.
    -u, --update         Update the appid names cache from the Steam API.
    -f, --force          Force rename even if destination folder exists (DANGEROUS).
    -d <screenshots_dir> Specify the directory to scan for screenshots [default: output].
"""

import asyncio
import glob
import json
import logging
import os
import platform
import re
import shutil
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple, Union
from urllib.parse import quote

import requests
from docopt import docopt

# Third-party imports with fallbacks
try:
    import html
except ImportError:
    html = None

# Configure UTF-8 encoding
sys.stdout.reconfigure(encoding="utf-8")
sys.stderr.reconfigure(encoding="utf-8")


# Constants
@dataclass(frozen=True)
class Config:
    """Configuration constants for the application."""

    APPID_CACHE_FILE: str = "appid_names.json"
    DEFAULT_OUTPUT_FOLDER: str = "backup"
    STEAM_SCREENSHOTS_SUBDIR: str = "760"
    STEAM_API_ENDPOINT: str = "https://api.steampowered.com/ISteamApps/GetAppList/v0002"
    SUPPORTED_EXTENSIONS: Tuple[str, ...] = (
        ".png",
        ".jpg",
        ".jpeg",
        ".gif",
        ".bmp",
        ".webp",
    )
    MAX_APPID_VALUE: int = 2147483647  # Max 32-bit signed integer


# Custom Exceptions
class SSUError(Exception):
    """Base exception for SSU operations."""

    pass


class AppIdError(SSUError):
    """Raised when there's an error with AppID operations."""

    pass


class FileOperationError(SSUError):
    """Raised when file operations fail."""

    pass


class ValidationError(SSUError):
    """Raised when input validation fails."""

    pass


# Configure logging
def setup_logging(quiet: bool = False) -> logging.Logger:
    """Set up logging configuration."""
    logger = logging.getLogger("ssu")
    logger.setLevel(logging.ERROR if quiet else logging.INFO)

    if not logger.handlers:
        handler = logging.StreamHandler(sys.stderr if quiet else sys.stdout)
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)

    return logger


@dataclass
class AppIdConverter:
    """Enhanced AppID converter with better caching and error handling."""

    cache_file: Path = field(default_factory=lambda: Path(Config.APPID_CACHE_FILE))
    appid_names: Dict[str, str] = field(default_factory=dict)
    quiet: bool = False
    force_update: bool = False
    logger: logging.Logger = field(default_factory=lambda: logging.getLogger("ssu"))

    def __post_init__(self):
        """Initialize the converter and load cache."""
        if self.force_update:
            self._download_app_data()
        else:
            self._load_appid_names()

    def _download_app_data(self) -> None:
        """Download app data from Steam API with retry logic."""
        max_retries = 3
        retry_delay = 1.0

        for attempt in range(max_retries):
            try:
                self.logger.info("Downloading app data from Steam API...")
                response = requests.get(Config.STEAM_API_ENDPOINT, timeout=30)
                response.raise_for_status()

                app_data = response.json()
                if not self._validate_api_response(app_data):
                    raise AppIdError("Invalid API response format")

                self.appid_names = {
                    str(app["appid"]): app["name"]
                    for app in app_data["applist"]["apps"]
                }

                self._save_cache()
                self.logger.info(f"Downloaded {len(self.appid_names)} app names")
                return

            except requests.exceptions.RequestException as e:
                if attempt == max_retries - 1:
                    raise AppIdError(
                        f"Failed to download app data after {max_retries} attempts: {e}"
                    )
                self.logger.warning(
                    f"Attempt {attempt + 1} failed: {e}. Retrying in {retry_delay}s..."
                )
                time.sleep(retry_delay)
                retry_delay *= 2

            except (json.JSONDecodeError, KeyError, AppIdError) as e:
                raise AppIdError(f"Error processing API response: {e}")

    def _validate_api_response(self, app_data: dict) -> bool:
        """Validate the structure of API response."""
        return (
            isinstance(app_data, dict)
            and "applist" in app_data
            and isinstance(app_data["applist"], dict)
            and "apps" in app_data["applist"]
            and isinstance(app_data["applist"]["apps"], list)
        )

    def _load_appid_names(self) -> None:
        """Load appid names from cache or download if necessary."""
        try:
            if self.cache_file.exists():
                self.logger.info("Loading appid names from local cache...")
                with open(self.cache_file, encoding="utf-8") as f:
                    self.appid_names = json.load(f)
            else:
                self.logger.info("Cache not found, downloading app data...")
                self._download_app_data()
        except (OSError, json.JSONDecodeError, AppIdError) as e:
            self.logger.error(f"Error loading cache: {e}")
            self._download_app_data()

    def _save_cache(self) -> None:
        """Save appid names to cache file."""
        try:
            self.cache_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.cache_file, "w", encoding="utf-8") as f:
                json.dump(self.appid_names, f, ensure_ascii=False, indent=2)
        except OSError as e:
            raise AppIdError(f"Failed to save cache: {e}")

    def is_valid_appid(self, appid: str) -> bool:
        """Check if the provided string is a valid Steam AppID."""
        try:
            return appid.isdigit() and 0 < int(appid) <= Config.MAX_APPID_VALUE
        except ValueError:
            return False

    def get_app_name(self, appid: str) -> str:
        """Get app name for given appid, with fallback handling."""
        if not self.appid_names:
            if not self._ensure_data_loaded():
                return appid
        return self.appid_names.get(appid, appid)

    def _ensure_data_loaded(self) -> bool:
        """Ensure app data is loaded, downloading if necessary."""
        if not self.appid_names:
            try:
                self._download_app_data()
                return True
            except AppIdError as e:
                self.logger.error(f"Could not load app data: {e}")
                return False
        return True


class FileManager:
    """Enhanced file management with better error handling and progress tracking."""

    def __init__(self, logger: logging.Logger):
        self.logger = logger

    @staticmethod
    def sanitize_filename(name: str) -> str:
        """Sanitize filename for cross-platform compatibility."""
        # More comprehensive sanitization
        if platform.system() == "Windows":
            invalid_chars = '<>:"/\\|?*'
        else:
            invalid_chars = "/"

        sanitized = re.sub(f"[{re.escape(invalid_chars)}]", "", name)

        # Also remove control characters
        sanitized = re.sub(r"[\x00-\x1f\x7f-\x9f]", "", sanitized)

        # Limit length to avoid filesystem issues
        return sanitized[:255].strip()

    def create_directory(self, path: Union[str, Path], exist_ok: bool = True) -> Path:
        """Create directory with enhanced error handling."""
        try:
            path = Path(path)
            path.mkdir(parents=True, exist_ok=exist_ok)
            return path
        except OSError as e:
            raise FileOperationError(f"Failed to create directory {path}: {e}")

    def copy_file(self, src: Union[str, Path], dst: Union[str, Path]) -> None:
        """Copy file with metadata preservation."""
        try:
            shutil.copy2(src, dst)
        except OSError as e:
            raise FileOperationError(f"Failed to copy {src} to {dst}: {e}")

    def move_file(self, src: Union[str, Path], dst: Union[str, Path]) -> None:
        """Move file with error handling."""
        try:
            os.rename(src, dst)
        except OSError as e:
            raise FileOperationError(f"Failed to move {src} to {dst}: {e}")

    def find_files(self, pattern: str) -> List[Path]:
        """Find files matching pattern."""
        return [Path(p) for p in glob.glob(pattern)]

    def get_file_size(self, path: Union[str, Path]) -> int:
        """Get file size in bytes."""
        try:
            return Path(path).stat().st_size
        except OSError as e:
            self.logger.warning(f"Could not get size of {path}: {e}")
            return 0


class ProgressTracker:
    """Track progress for long-running operations."""

    def __init__(self, logger: logging.Logger, quiet: bool = False):
        self.logger = logger
        self.quiet = quiet
        self.start_time = time.time()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        elapsed = time.time() - self.start_time
        if not self.quiet:
            self.logger.info(f"Operation completed in {elapsed:.2f}s")

    def log_progress(self, message: str) -> None:
        """Log progress message if not in quiet mode."""
        if not self.quiet:
            self.logger.info(message)


class SteamScreenshotManager:
    """Main class for Steam screenshot operations."""

    def __init__(self, logger: logging.Logger, quiet: bool = False):
        self.logger = logger
        self.quiet = quiet
        self.file_manager = FileManager(logger)
        self.appid_converter = AppIdConverter(quiet=quiet, logger=logger)

    def backup_screenshots(
        self,
        steam_user_folder: Union[str, Path],
        output_folder: Optional[Union[str, Path]] = None,
        dry_run: bool = False,
    ) -> Dict[str, int]:
        """Backup Steam screenshots organized by app name."""
        steam_user_folder = Path(steam_user_folder)
        screenshots_root = (
            steam_user_folder / Config.STEAM_SCREENSHOTS_SUBDIR / "remote"
        )

        if not screenshots_root.exists():
            raise ValidationError(f"Screenshots folder not found: {screenshots_root}")

        output_folder = self.file_manager.create_directory(
            output_folder or Config.DEFAULT_OUTPUT_FOLDER
        )

        stats = {"apps": 0, "screenshots": 0, "bytes": 0}

        with ProgressTracker(self.logger, self.quiet) as tracker:
            for appid_dir in screenshots_root.iterdir():
                if not appid_dir.is_dir():
                    continue

                appid = appid_dir.name
                if not self.appid_converter.is_valid_appid(appid):
                    tracker.log_progress(f"Skipping invalid appid folder: {appid}")
                    continue

                stats["apps"] += 1
                app_name = self.appid_converter.get_app_name(appid)
                sanitized_name = self.file_manager.sanitize_filename(app_name)
                app_folder = self.file_manager.create_directory(
                    output_folder / sanitized_name
                )

                screenshots_dir = appid_dir / "screenshots"
                if not screenshots_dir.exists():
                    continue

                copied_count = 0
                for screenshot in screenshots_dir.glob("*.jpg"):
                    dest_path = app_folder / screenshot.name

                    if dry_run:
                        tracker.log_progress(
                            f"[DRY RUN] Would copy: {screenshot} -> {dest_path}"
                        )
                        copied_count += 1
                        stats["bytes"] += self.file_manager.get_file_size(screenshot)
                    elif not dest_path.exists():
                        try:
                            self.file_manager.copy_file(screenshot, dest_path)
                            copied_count += 1
                            stats["bytes"] += dest_path.stat().st_size
                        except FileOperationError as e:
                            self.logger.error(f"Failed to copy {screenshot}: {e}")

                if copied_count > 0:
                    tracker.log_progress(
                        f"Copied {copied_count} screenshots for {app_name}"
                    )
                stats["screenshots"] += copied_count

        return stats

    def sort_screenshots(
        self,
        screenshots_folder: Union[str, Path],
        dry_run: bool = False,
    ) -> Dict[str, int]:
        """Sort screenshots by app name in-place."""
        screenshots_folder = Path(screenshots_folder)

        if not screenshots_folder.exists():
            raise ValidationError(f"Screenshots folder not found: {screenshots_folder}")

        stats = {"apps": 0, "screenshots": 0}

        with ProgressTracker(self.logger, self.quiet) as tracker:
            # Group screenshots by appid
            screenshots_by_appid = {}
            for screenshot in screenshots_folder.glob("*"):
                if screenshot.suffix.lower() not in [".png", ".jpg"]:
                    continue

                try:
                    appid = screenshot.stem.split("_")[0]
                    if self.appid_converter.is_valid_appid(appid):
                        screenshots_by_appid.setdefault(appid, []).append(screenshot)
                except (ValueError, IndexError):
                    self.logger.warning(f"Could not parse appid from {screenshot.name}")

            # Process each appid group
            for appid, screenshots in screenshots_by_appid.items():
                stats["apps"] += 1
                app_name = self.appid_converter.get_app_name(appid)
                sanitized_name = self.file_manager.sanitize_filename(app_name)
                app_folder = self.file_manager.create_directory(
                    screenshots_folder / sanitized_name
                )

                moved_count = 0
                for screenshot in screenshots:
                    dest_path = app_folder / screenshot.name

                    if dry_run:
                        tracker.log_progress(
                            f"[DRY RUN] Would move: {screenshot} -> {dest_path}"
                        )
                        moved_count += 1
                    else:
                        try:
                            self.file_manager.move_file(screenshot, dest_path)
                            moved_count += 1
                        except FileOperationError as e:
                            self.logger.error(f"Failed to move {screenshot}: {e}")

                if moved_count > 0:
                    tracker.log_progress(
                        f"Moved {moved_count} screenshots for {app_name}"
                    )
                stats["screenshots"] += moved_count

        return stats

    def merge_screenshots(
        self,
        compressed_folder: Union[str, Path],
        uncompressed_folder: Union[str, Path],
        dry_run: bool = False,
    ) -> Dict[str, int]:
        """Merge compressed screenshots into uncompressed folder."""
        compressed_folder = Path(compressed_folder)
        uncompressed_folder = Path(uncompressed_folder)

        if not compressed_folder.exists() or not uncompressed_folder.exists():
            raise ValidationError("Both source and destination folders must exist")

        stats = {"apps": 0, "screenshots": 0}

        with ProgressTracker(self.logger, self.quiet) as tracker:
            for app_dir in compressed_folder.iterdir():
                if not app_dir.is_dir():
                    continue

                stats["apps"] += 1
                dest_app_dir = uncompressed_folder / app_dir.name

                if not dest_app_dir.exists():
                    self.logger.warning(
                        f"App folder {app_dir.name} does not exist in uncompressed directory"
                    )
                    continue

                self.file_manager.create_directory(dest_app_dir, exist_ok=True)

                # Get existing screenshots for duplicate detection
                existing_files = {
                    screenshot.stem for screenshot in dest_app_dir.glob("*.jpg")
                }

                added_count = 0
                for screenshot in app_dir.glob("*.jpg"):
                    if screenshot.stem not in existing_files:
                        dest_path = dest_app_dir / screenshot.name

                        if dry_run:
                            tracker.log_progress(
                                f"[DRY RUN] Would copy: {screenshot} -> {dest_path}"
                            )
                            added_count += 1
                        else:
                            try:
                                self.file_manager.copy_file(screenshot, dest_path)
                                added_count += 1
                            except FileOperationError as e:
                                self.logger.error(f"Failed to copy {screenshot}: {e}")

                if added_count > 0:
                    tracker.log_progress(
                        f"Added {added_count} screenshots for {app_dir.name}"
                    )
                stats["screenshots"] += added_count

        return stats

    def rename_app_folders(
        self,
        screenshots_folder: Union[str, Path],
        force: bool = False,
        dry_run: bool = False,
    ) -> Dict[str, int]:
        """Rename appid folders to app names."""
        screenshots_folder = Path(screenshots_folder)

        if not screenshots_folder.exists():
            raise ValidationError(f"Screenshots folder not found: {screenshots_folder}")

        stats = {"renamed": 0, "skipped_not_found": 0, "skipped_exists": 0}

        with ProgressTracker(self.logger, self.quiet) as tracker:
            for item in screenshots_folder.iterdir():
                if not item.is_dir():
                    continue

                appid = item.name
                if not self.appid_converter.is_valid_appid(appid):
                    continue

                app_name = self.appid_converter.get_app_name(appid)
                if app_name == appid:  # App name not found
                    stats["skipped_not_found"] += 1
                    tracker.log_progress(f"Skipping {appid}: App name not found")
                    continue

                sanitized_name = self.file_manager.sanitize_filename(app_name)
                new_path = screenshots_folder / sanitized_name

                if new_path.exists() and not force:
                    stats["skipped_exists"] += 1
                    tracker.log_progress(
                        f"Skipping {appid}: Destination exists ({sanitized_name})"
                    )
                    continue

                if dry_run:
                    action = "OVERWRITE" if new_path.exists() else "rename"
                    tracker.log_progress(
                        f"[DRY RUN] Would {action}: {appid} -> {sanitized_name}"
                    )
                    stats["renamed"] += 1
                else:
                    try:
                        if new_path.exists():
                            if force:
                                self.logger.warning(
                                    f"Removing existing folder: {new_path}"
                                )
                                shutil.rmtree(new_path)
                            else:
                                continue

                        item.rename(new_path)
                        stats["renamed"] += 1
                        tracker.log_progress(f"Renamed {appid} -> {sanitized_name}")
                    except OSError as e:
                        self.logger.error(f"Failed to rename {item} to {new_path}: {e}")

        return stats


class GalleryGenerator:
    """Enhanced HTML gallery generator with modern features."""

    def __init__(self, logger: logging.Logger, quiet: bool = False):
        self.logger = logger
        self.quiet = quiet

    def generate_gallery(
        self,
        screenshots_dir: Union[str, Path] = "output",
        output_html: Union[str, Path] = "gallery.html",
    ) -> None:
        """Generate an enhanced HTML gallery."""
        screenshots_dir = Path(screenshots_dir)
        output_html = Path(output_html)

        if not screenshots_dir.exists():
            raise ValidationError(f"Screenshots directory not found: {screenshots_dir}")

        self.logger.info(f"Scanning directory: {screenshots_dir}")

        # Organize images by category
        images_by_category = self._scan_images(screenshots_dir)

        if not images_by_category:
            raise ValidationError("No images found in the specified folder")

        # Generate HTML content
        html_content = self._generate_html_content(images_by_category, output_html)

        # Write HTML file
        try:
            output_html.parent.mkdir(parents=True, exist_ok=True)
            with open(output_html, "w", encoding="utf-8") as f:
                f.write(html_content)

            if not self.quiet:
                self.logger.info(f"Gallery created at {output_html}")
        except OSError as e:
            raise FileOperationError(f"Failed to write HTML file: {e}")

    def _scan_images(self, screenshots_dir: Path) -> Dict[str, List[Path]]:
        """Scan directory for images organized by category."""
        images_by_category = {}

        for root in screenshots_dir.rglob("*"):
            if root.is_file() and root.suffix.lower() in [
                ".png",
                ".jpg",
                ".jpeg",
                ".gif",
                ".bmp",
                ".webp",
            ]:
                category_name = root.parent.name
                if category_name not in images_by_category:
                    images_by_category[category_name] = []
                images_by_category[category_name].append(root)

        # Sort images within each category
        for category in images_by_category:
            images_by_category[category] = self._sort_images(
                images_by_category[category]
            )

        # Sort categories
        sorted_categories = sorted(
            images_by_category.keys(),
            key=lambda k: (not k[0].isalpha(), self._natural_sort_key(k)),
        )

        return {
            k: images_by_category[k] for k in sorted_categories if images_by_category[k]
        }

    def _sort_images(self, images: List[Path]) -> List[Path]:
        """Sort images using natural sort order."""

        def sort_key(path: Path) -> List[Union[int, str]]:
            name = path.stem
            return [
                int(text) if text.isdigit() else text.lower()
                for text in re.split(r"(\d+)", name)
            ]

        # Separate numerical and alphabetical filenames
        alphabetical = [img for img in images if not re.match(r"^\d", img.stem)]
        numerical = [img for img in images if re.match(r"^\d", img.stem)]

        return sorted(alphabetical, key=sort_key) + sorted(numerical, key=sort_key)

    def _natural_sort_key(self, s: str) -> List[Union[int, str]]:
        """Natural sort key function."""
        return [
            int(text) if text.isdigit() else text.lower()
            for text in re.split(r"(\d+)", s)
        ]

    def _generate_html_content(
        self, images_by_category: Dict[str, List[Path]], output_html: Path
    ) -> str:
        """Generate the complete HTML content."""
        # Enhanced HTML template with modern features
        html_template = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Steam Screenshots Gallery</title>
    <style>
        :root {
            --bg-color: #0a0a0a;
            --surface-color: #1a1a1a;
            --text-color: #e0e0e0;
            --text-secondary: #b0b0b0;
            --accent-color: #00d4ff;
            --accent-hover: #00b8e6;
            --success-color: #4caf50;
            --warning-color: #ff9800;
            --error-color: #f44336;
            --border-color: #333;
            --shadow: 0 4px 20px rgba(0, 0, 0, 0.3);
            --shadow-hover: 0 8px 30px rgba(0, 0, 0, 0.4);
        }

        * {
            box-sizing: border-box;
            margin: 0;
            padding: 0;
        }

        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, var(--bg-color) 0%, var(--surface-color) 100%);
            color: var(--text-color);
            line-height: 1.6;
            min-height: 100vh;
        }

        .container {
            max-width: 1400px;
            margin: 0 auto;
            padding: 20px;
        }

        h1 {
            text-align: center;
            margin-bottom: 30px;
            font-size: clamp(2rem, 5vw, 3.5rem);
            background: linear-gradient(135deg, var(--accent-color), var(--accent-hover));
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
            text-shadow: 0 2px 10px rgba(0, 212, 255, 0.3);
        }

        .search-container {
            margin-bottom: 30px;
        }

        #search {
            width: 100%;
            max-width: 600px;
            padding: 15px 20px;
            font-size: 16px;
            border: 2px solid var(--border-color);
            border-radius: 25px;
            background: var(--surface-color);
            color: var(--text-color);
            outline: none;
            transition: all 0.3s ease;
        }

        #search:focus {
            border-color: var(--accent-color);
            box-shadow: 0 0 0 3px rgba(0, 212, 255, 0.1);
        }

        .categories-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(350px, 1fr));
            gap: 25px;
        }

        .category {
            background: var(--surface-color);
            border-radius: 15px;
            padding: 20px;
            box-shadow: var(--shadow);
            border: 1px solid var(--border-color);
            transition: transform 0.3s ease, box-shadow 0.3s ease;
        }

        .category:hover {
            transform: translateY(-5px);
            box-shadow: var(--shadow-hover);
        }

        .category-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 15px;
            padding-bottom: 10px;
            border-bottom: 1px solid var(--border-color);
            cursor: pointer;
        }

        .category-title {
            font-size: 1.3rem;
            font-weight: 600;
            color: var(--accent-color);
        }

        .image-count {
            background: var(--accent-color);
            color: var(--bg-color);
            padding: 4px 8px;
            border-radius: 12px;
            font-size: 0.85rem;
            font-weight: 500;
        }

        .toggle-icon {
            font-size: 1.2rem;
            transition: transform 0.3s ease;
        }

        .category.collapsed .toggle-icon {
            transform: rotate(-90deg);
        }

        .gallery-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
            margin-top: 15px;
        }

        .gallery-item {
            position: relative;
            overflow: hidden;
            border-radius: 10px;
            cursor: pointer;
            transition: transform 0.3s ease;
        }

        .gallery-item:hover {
            transform: scale(1.05);
        }

        .gallery-item img {
            width: 100%;
            height: 150px;
            object-fit: cover;
            display: block;
            transition: opacity 0.3s ease;
        }

        .gallery-item:hover img {
            opacity: 0.8;
        }

        .lightbox {
            display: none;
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(0, 0, 0, 0.95);
            justify-content: center;
            align-items: center;
            z-index: 1000;
            backdrop-filter: blur(10px);
        }

        .lightbox.active {
            display: flex;
        }

        .lightbox img {
            max-width: 90%;
            max-height: 90%;
            border-radius: 10px;
            box-shadow: 0 10px 40px rgba(0, 0, 0, 0.5);
        }

        .lightbox-close {
            position: absolute;
            top: 20px;
            right: 30px;
            background: var(--error-color);
            color: white;
            border: none;
            width: 40px;
            height: 40px;
            border-radius: 50%;
            font-size: 20px;
            cursor: pointer;
            transition: background-color 0.3s ease;
        }

        .lightbox-close:hover {
            background: #d32f2f;
        }

        .stats {
            margin-top: 30px;
            padding: 20px;
            background: var(--surface-color);
            border-radius: 10px;
            text-align: center;
        }

        .back-to-top {
            position: fixed;
            bottom: 30px;
            right: 30px;
            background: var(--accent-color);
            color: var(--bg-color);
            border: none;
            width: 50px;
            height: 50px;
            border-radius: 50%;
            font-size: 20px;
            cursor: pointer;
            opacity: 0;
            visibility: hidden;
            transition: all 0.3s ease;
            box-shadow: var(--shadow);
        }

        .back-to-top.visible {
            opacity: 1;
            visibility: visible;
        }

        .back-to-top:hover {
            background: var(--accent-hover);
            transform: translateY(-3px);
        }

        @media (max-width: 768px) {
            .container {
                padding: 15px;
            }

            .categories-grid {
                grid-template-columns: 1fr;
                gap: 20px;
            }

            .gallery-grid {
                grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
            }
        }
    </style>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css">
</head>
<body>
    <div class="container">
        <h1><i class="fas fa-images"></i> Steam Screenshots Gallery</h1>

        <div class="search-container">
            <input type="text" id="search" placeholder="Search categories..." autocomplete="off">
        </div>

        <div class="categories-grid" id="categoriesGrid">
"""

        # Add categories and images
        for category, images in images_by_category.items():
            html_template += f"""
            <div class="category" data-category="{category}">
                <div class="category-header" onclick="toggleCategory(this)">
                    <span class="category-title">{category}</span>
                    <span class="image-count">{len(images)} images</span>
                    <i class="fas fa-chevron-down toggle-icon"></i>
                </div>
                <div class="gallery-grid">
"""

            for idx, image_path in enumerate(images):
                relative_path = os.path.relpath(image_path, output_html.parent)
                html_template += f"""
                    <div class="gallery-item" onclick="openLightbox('{category}', {idx})">
                        <img src="{relative_path}" alt="Screenshot" loading="lazy">
                    </div>
"""

            html_template += """
                </div>
            </div>
"""

        # Add lightbox and scripts
        html_template += """
        </div>

        <div class="stats">
            <p>Total categories: {len(images_by_category)} | Total images: {sum(len(images) for images in images_by_category.values())}</p>
        </div>
    </div>

    <!-- Lightbox -->
    <div class="lightbox" id="lightbox">
        <button class="lightbox-close" onclick="closeLightbox()">
            <i class="fas fa-times"></i>
        </button>
        <img id="lightboxImage" src="" alt="Screenshot">
    </div>

    <button class="back-to-top" onclick="scrollToTop()">
        <i class="fas fa-arrow-up"></i>
    </button>

    <script>
        // Search functionality
        document.getElementById('search').addEventListener('input', function(e) {
            const searchTerm = e.target.value.toLowerCase();
            const categories = document.querySelectorAll('.category');

            categories.forEach(category => {
                const categoryName = category.dataset.category.toLowerCase();
                const images = category.querySelectorAll('.gallery-item');
                let categoryVisible = false;

                if (categoryName.includes(searchTerm)) {
                    category.style.display = 'block';
                    categoryVisible = true;
                } else {
                    // Check individual images
                    images.forEach(img => {
                        const shouldShow = searchTerm === '' ||
                                         img.querySelector('img').src.toLowerCase().includes(searchTerm);
                        img.style.display = shouldShow ? 'block' : 'none';
                        if (shouldShow) categoryVisible = true;
                    });
                    category.style.display = categoryVisible ? 'block' : 'none';
                }
            });
        });

        // Category toggle
        function toggleCategory(header) {
            const category = header.closest('.category');
            const grid = category.querySelector('.gallery-grid');
            const icon = header.querySelector('.toggle-icon');

            if (grid.style.display === 'none') {
                grid.style.display = 'grid';
                category.classList.remove('collapsed');
            } else {
                grid.style.display = 'none';
                category.classList.add('collapsed');
            }
        }

        // Lightbox functionality
        function openLightbox(category, index) {
            const lightbox = document.getElementById('lightbox');
            const lightboxImg = document.getElementById('lightboxImage');
            const categoryElement = document.querySelector(`[data-category="${category}"]`);
            const image = categoryElement.querySelectorAll('.gallery-item img')[index];

            lightboxImg.src = image.src;
            lightbox.classList.add('active');
        }

        function closeLightbox() {
            document.getElementById('lightbox').classList.remove('active');
        }

        // Back to top
        window.addEventListener('scroll', function() {
            const btn = document.querySelector('.back-to-top');
            if (window.pageYOffset > 300) {
                btn.classList.add('visible');
            } else {
                btn.classList.remove('visible');
            }
        });

        function scrollToTop() {
            window.scrollTo({ top: 0, behavior: 'smooth' });
        }

        // Close lightbox on outside click
        document.getElementById('lightbox').addEventListener('click', function(e) {
            if (e.target === this) {
                closeLightbox();
            }
        });

        // Keyboard navigation
        document.addEventListener('keydown', function(e) {
            if (e.key === 'Escape') {
                closeLightbox();
            }
        });
    </script>
</body>
</html>
"""

        return html_template


def main():
    """Main entry point with enhanced error handling."""
    arguments = docopt(__doc__, version="SSU 2.0")

    # Parse arguments
    quiet = arguments["--quiet"]
    dry_run = arguments["--dry-run"]
    force_update = arguments["--update"]
    force = arguments["--force"]

    # Setup logging
    logger = setup_logging(quiet)

    try:
        # Initialize main manager
        manager = SteamScreenshotManager(logger, quiet)

        # Execute requested operation
        if arguments["backup"]:
            stats = manager.backup_screenshots(
                arguments["<steam_user_folder>"],
                arguments.get("-o"),
                dry_run,
            )
            if not quiet:
                logger.info(
                    f"Backup completed: {stats['screenshots']} screenshots from {stats['apps']} apps ({stats['bytes'] / 1024 / 1024:.1f} MB)"
                )

        elif arguments["sort"]:
            stats = manager.sort_screenshots(arguments["<screenshots_folder>"], dry_run)
            if not quiet:
                logger.info(
                    f"Sort completed: {stats['screenshots']} screenshots from {stats['apps']} apps"
                )

        elif arguments["merge"]:
            stats = manager.merge_screenshots(
                arguments["<compressed_screenshots>"],
                arguments["<uncompressed_screenshots>"],
                dry_run,
            )
            if not quiet:
                logger.info(
                    f"Merge completed: {stats['screenshots']} screenshots from {stats['apps']} apps"
                )

        elif arguments["rename"]:
            stats = manager.rename_app_folders(
                arguments["<screenshots_folder>"],
                force,
                dry_run,
            )
            if not quiet:
                logger.info(
                    f"Rename completed: {stats['renamed']} renamed, {stats['skipped_not_found']} skipped (not found), {stats['skipped_exists']} skipped (exists)"
                )

        elif arguments["update"]:
            # Force update the app cache
            appid_converter = AppIdConverter(
                quiet=quiet, force_update=True, logger=logger
            )
            if not quiet:
                logger.info("AppID cache updated successfully")

        elif arguments["gallery"]:
            generator = GalleryGenerator(logger, quiet)
            generator.generate_gallery(
                arguments.get("-d") or "output",
                arguments.get("-o") or "gallery.html",
            )

    except (SSUError, requests.exceptions.RequestException) as e:
        logger.error(f"Operation failed: {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        logger.info("Operation cancelled by user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
