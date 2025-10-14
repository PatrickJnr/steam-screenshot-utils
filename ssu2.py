"""
SSU: Steam Screenshot Utils.

Usage:
    ssu backup <steam_user_folder> [-o <output_folder>] [-q|--quiet] [-n|--dry-run]
    ssu sort <screenshots_folder> [-q|--quiet] [-n|--dry-run]
    ssu merge <compressed_screenshots> <uncompressed_screenshots> [-q|--quiet] [-n|--dry-run]
    ssu rename <screenshots_folder> [-q|--quiet] [-n|--dry-run] [-u|--update] [-f|--force]
    ssu gallery [-o <output_html>] [-d <screenshots_dir>] [-q|--quiet]

Options:
    -o <output_folder>  Specify the output folder for backups [default: backup].
    -q, --quiet         Suppress non-error output.
    -n, --dry-run       Simulate the operation without making changes.
    -u, --update        Update the appid names cache from the Steam API.
    -f, --force         Force rename even if destination folder exists (DANGEROUS).
    -d <screenshots_dir>  Specify the directory to scan for screenshots [default: output].
"""

import glob
import json
import os
import platform
import re
import shutil
import sys
from typing import List, Tuple

import requests
from docopt import docopt
import html  # Import the html module

# Set stdout and stderr to handle UTF-8 encoding properly
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")


# Constants
APPID_CACHE_FILE = "appid_names.json"
DEFAULT_OUTPUT_FOLDER = "backup"
STEAM_SCREENSHOTS_SUBDIR = "760"
STEAM_API_ENDPOINT = "https://api.steampowered.com/ISteamApps/GetAppList/v0002"


class AppIdError(Exception):
    pass


class AppidConverter:
    """Handles retrieving and caching app names from AppIDs."""

    def __init__(
        self, cache_file: str, quiet: bool = False, force_update: bool = False
    ):
        self.cache_file = cache_file
        self.appid_names: dict = {}
        self.downloaded_app_data = False
        self.quiet = quiet
        if force_update:
            self._download_app_data()  # Force update if requested
        else:
            self._load_appid_names()  # Otherwise, try to load from cache

    def _download_app_data(self):
        """Downloads app data from the Steam API and updates the cache."""
        try:
            response = requests.get(STEAM_API_ENDPOINT)
            response.raise_for_status()
            app_data = response.json()

            if "applist" not in app_data or "apps" not in app_data["applist"]:
                raise AppIdError("Invalid app data format received from Steam API.")

            self.appid_names = {
                str(app["appid"]): app["name"] for app in app_data["applist"]["apps"]
            }

            with open(self.cache_file, "w") as f:
                json.dump(self.appid_names, f)

            self.downloaded_app_data = True
            if not self.quiet:
                print("AppID names cache updated from Steam API.")

        except (
            requests.exceptions.RequestException,
            IOError,
            OSError,
            json.JSONDecodeError,
            AppIdError,
        ) as e:
            print(f"Error during app data download/save: {e}", file=sys.stderr)
            sys.exit(1)

    def _load_appid_names(self):
        """Loads appid names from cache or downloads if necessary."""
        try:
            if os.path.exists(self.cache_file):
                if not self.quiet:
                    print("Loading appid names from local cache...")
                with open(self.cache_file) as f:
                    self.appid_names = json.load(f)
            else:
                if not self.quiet:
                    print("Downloading app data from Steam API...")
                self._download_app_data()
        except (IOError, OSError, json.JSONDecodeError) as e:
            print(f"Error reading/decoding cache file: {e}", file=sys.stderr)
            print("Attempting to download app data...", file=sys.stderr)
            self._download_app_data()

    def is_valid_appid(self, appid: str) -> bool:
        """Checks if the provided string is a potentially valid Steam AppID."""
        return appid.isdigit() and 0 < int(appid) <= 2147483647  # Max 32-bit int

    def get_app_name(self, appid: str) -> str:
        """Retrieves the app name for a given appid.  Returns appid if not found."""
        if not self.appid_names:
            if not self.downloaded_app_data:
                if not self.quiet:
                    print(
                        "AppID names are empty, attempting to download...",
                        file=sys.stderr,
                    )
                self._download_app_data()
                if not self.appid_names:  # check again after attempt.
                    # print(f"Could not retrieve app name for appid: {appid}.  Using appid instead.", file=sys.stderr)
                    return appid  # Do not print here, this will be handled by rename
            else:
                # print(f"Could not retrieve app name for appid: {appid}.  Using appid instead.", file=sys.stderr)
                return appid  # Do not print here, this will be handled by rename
        return self.appid_names.get(
            appid, appid
        )  # Returns appid if the appid key doesn't exist.


def _sanitize_app_name(name: str) -> str:
    """Sanitizes the app name for use as a folder name."""
    return re.sub(
        r'[<>:"/\\|?*]' if platform.system() == "Windows" else r"[/]", "", name
    )


def _create_app_folder(root_folder: str, app_name: str, appid: str, quiet: bool) -> str:
    """Creates the app folder, handling potential errors."""
    app_folder = os.path.join(root_folder, app_name)
    try:
        os.makedirs(app_folder, exist_ok=True)
        return app_folder
    except (IOError, OSError) as e:
        print(
            f"Could not create folder for app name '{app_name}' (using appid {appid}): {e}",
            file=sys.stderr,
        )
        # Fallback to appid folder
        fallback_folder = os.path.join(root_folder, appid)
        try:
            os.makedirs(fallback_folder, exist_ok=True)
            return fallback_folder
        except (IOError, OSError) as e:
            print(
                f"Could not create fallback folder '{fallback_folder}': {e}",
                file=sys.stderr,
            )
            sys.exit(1)


def _process_screenshots(
    src_pattern: str,
    dest_folder: str,
    action: str,
    quiet: bool = False,
    dry_run: bool = False,
):
    """Helper function to process (copy or move) screenshots."""
    count = 0
    for src_path in glob.glob(src_pattern):
        filename = os.path.basename(src_path)
        dest_path = os.path.join(dest_folder, filename)

        if dry_run:
            print(f"[Dry Run] Would {action}: {src_path} to {dest_path}")
            count += 1
            continue

        if action == "copy" and not os.path.exists(dest_path):
            try:
                shutil.copy2(src_path, dest_path)
                count += 1
            except (IOError, OSError) as e:
                print(f"Error copying {src_path}: {e}", file=sys.stderr)
                sys.exit(1)
        elif action == "move":
            try:
                os.rename(src_path, dest_path)
                count += 1
            except (IOError, OSError) as e:
                print(f"Error moving {src_path}: {e}", file=sys.stderr)
                sys.exit(1)
    return count


def backup(
    steam_user_folder: str,
    appid_converter: AppidConverter,
    output_folder: str = None,
    quiet: bool = False,
    dry_run: bool = False,
):
    """Backs up Steam screenshots, organizing them by app name."""
    screenshots_root = os.path.join(
        steam_user_folder, STEAM_SCREENSHOTS_SUBDIR, "remote"
    )
    if not os.path.isdir(screenshots_root):
        print(
            f"Error: Screenshots folder not found: {screenshots_root}", file=sys.stderr
        )
        sys.exit(1)

    output_folder = output_folder or DEFAULT_OUTPUT_FOLDER
    try:
        os.makedirs(output_folder, exist_ok=True)
    except (IOError, OSError) as e:
        print(f"Error creating output directory: {e}", file=sys.stderr)
        sys.exit(1)

    total_copied = 0
    num_apps = 0

    for appid in os.listdir(screenshots_root):
        appid_folder = os.path.join(screenshots_root, appid)
        if not os.path.isdir(appid_folder):
            continue

        # Check for valid appid before getting the name
        if not appid_converter.is_valid_appid(appid):
            if not quiet:
                print(f"Skipping invalid appid folder: {appid_folder}")
            continue

        num_apps += 1
        app_name = appid_converter.get_app_name(appid)
        sanitized_app_name = _sanitize_app_name(app_name)
        app_folder = _create_app_folder(output_folder, sanitized_app_name, appid, quiet)

        if not quiet:
            print(f"Backing up screenshots from {app_name}...")

        src_pattern = os.path.join(appid_folder, "screenshots", "*.jpg")
        copied_count = _process_screenshots(
            src_pattern, app_folder, "copy", quiet, dry_run
        )
        total_copied += copied_count

        if not quiet:
            print(f"Copied {copied_count} new screenshots.")

    if not quiet:
        print(f"Finished! Backed up {total_copied} screenshots from {num_apps} apps.")


def sort(
    screenshots_folder: str,
    appid_converter: AppidConverter,
    quiet: bool = False,
    dry_run: bool = False,
):
    """Sorts uncompressed screenshots in-place by app name."""

    if not os.path.isdir(screenshots_folder):
        print(
            f"Error: Screenshots folder not found: {screenshots_folder}",
            file=sys.stderr,
        )
        sys.exit(1)

    total_moved = 0
    num_apps = 0
    for screenshot_path in glob.glob(
        os.path.join(screenshots_folder, "*.png")
    ) + glob.glob(os.path.join(screenshots_folder, "*.jpg")):
        try:
            appid, filename = os.path.basename(screenshot_path).split("_", 1)
        except ValueError as e:
            print(
                f"Error processing filename '{os.path.basename(screenshot_path)}': {e}. Skipping.",
                file=sys.stderr,
            )
            continue

        if not appid_converter.is_valid_appid(appid):
            if not quiet:
                print(
                    f"Skipping invalid appid file: {os.path.basename(screenshot_path)}"
                )
            continue

        num_apps += 1
        app_name = appid_converter.get_app_name(appid)
        sanitized_app_name = _sanitize_app_name(app_name)
        app_folder = _create_app_folder(
            screenshots_folder, sanitized_app_name, appid, quiet
        )

        if not quiet:
            print(f"Sorting screenshots from {app_name}...")

        moved_count = _process_screenshots(
            screenshot_path, app_folder, "move", quiet, dry_run
        )
        total_moved += moved_count
        if not quiet and not dry_run:
            print(f"Moved {moved_count} new screenshots.")

    if not quiet:
        print(f"Finished! Sorted {total_moved} screenshots from {num_apps} apps.")


def merge(
    compressed_folder: str,
    uncompressed_folder: str,
    appid_converter: AppidConverter,
    quiet: bool = False,
    dry_run: bool = False,
):
    """Merges compressed screenshots into the uncompressed folder."""

    if not os.path.isdir(compressed_folder) or not os.path.isdir(uncompressed_folder):
        print(
            "Error: Invalid compressed or uncompressed folder paths.", file=sys.stderr
        )
        sys.exit(1)

    total_added = 0
    num_apps = 0

    for app_name in os.listdir(compressed_folder):
        num_apps += 1
        src_app_folder = os.path.join(compressed_folder, app_name)
        if not os.path.isdir(src_app_folder):
            continue

        dest_app_folder = os.path.join(uncompressed_folder, app_name)

        if not os.path.isdir(dest_app_folder):
            print(
                f"Warning: app folder {app_name} does not exist in uncompressed directory",
                file=sys.stderr,
            )
        try:
            os.makedirs(dest_app_folder, exist_ok=True)
        except (IOError, OSError) as e:
            print(
                f"Error creating destination folder '{dest_app_folder}': {e}",
                file=sys.stderr,
            )
            sys.exit(1)

        existing_screenshots = set()
        for ext in ["png", "jpg"]:
            for screenshot_path in glob.glob(os.path.join(dest_app_folder, f"*.{ext}")):
                existing_screenshots.add(
                    os.path.splitext(os.path.basename(screenshot_path))[0]
                )

        if not quiet:
            print(f"Merging screenshots from {app_name}...")

        src_pattern = os.path.join(src_app_folder, "*.jpg")
        added_count = 0
        for src_path in glob.glob(src_pattern):
            screenshot_name = os.path.splitext(os.path.basename(src_path))[0]
            if screenshot_name not in existing_screenshots:
                dest_path = os.path.join(dest_app_folder, os.path.basename(src_path))
                if dry_run:
                    print(f"[Dry Run] Would copy: {src_path} to {dest_path}")
                    added_count += 1
                else:
                    try:
                        shutil.copy2(src_path, dest_path)
                        added_count += 1
                    except (IOError, OSError) as e:
                        print(f"Error copying {src_path}: {e}", file=sys.stderr)
                        sys.exit(1)

        if not quiet:
            print(f"Added {added_count} new compressed screenshots.")
    if not quiet:
        print(f"Finished! Merged {total_added} screenshots from {num_apps} apps.")


def rename(
    screenshots_folder: str,
    appid_converter: AppidConverter,
    quiet: bool = False,
    dry_run: bool = False,
    update_cache: bool = False,
    force: bool = False,
):
    """Renames appid folders to their corresponding app names."""

    if not os.path.isdir(screenshots_folder):
        print(
            f"Error: Screenshots folder not found: {screenshots_folder}",
            file=sys.stderr,
        )
        sys.exit(1)

    if update_cache:
        appid_converter._download_app_data()

    total_renamed = 0
    num_apps = 0
    skipped_not_found = 0
    skipped_exists = 0

    for item in os.listdir(screenshots_folder):
        item_path = os.path.join(screenshots_folder, item)
        if os.path.isdir(item_path):
            # Check for valid appid
            if appid_converter.is_valid_appid(item):
                num_apps += 1
                appid = item
                app_name = appid_converter.get_app_name(appid)
                if app_name == appid:  # App name not found
                    if not quiet:
                        print(
                            f"Skipping rename of {item_path}: App name not found for appid {appid}."
                        )
                    skipped_not_found += 1
                    continue

                sanitized_app_name = _sanitize_app_name(app_name)
                new_path = os.path.join(screenshots_folder, sanitized_app_name)

                if dry_run:
                    if os.path.exists(new_path):
                        print(
                            f"[Dry Run] Would rename: {item_path} to {new_path} (OVERWRITING existing folder!)"
                        )
                    else:
                        print(f"[Dry Run] Would rename: {item_path} to {new_path}")
                    total_renamed += 1  # Still count it in dry run
                else:
                    if os.path.exists(new_path):
                        if force:
                            print(
                                f"WARNING: Renaming {item_path} to {new_path}!",
                                file=sys.stderr,
                            )
                            print(
                                f"WARNING: This will OVERWRITE the existing folder: {new_path}!",
                                file=sys.stderr,
                            )
                            response = (
                                input(
                                    "WARNING: Are you sure you want to proceed? (y/n): "
                                )
                                .strip()
                                .lower()
                            )
                            if response == "y":
                                try:
                                    # Rename using shutil.rmtree to remove and os.rename to rename
                                    shutil.rmtree(new_path)
                                    os.rename(item_path, new_path)
                                    total_renamed += 1
                                except (IOError, OSError) as e:
                                    print(
                                        f"Error renaming {item_path} to {new_path}: {e}",
                                        file=sys.stderr,
                                    )
                            else:
                                if not quiet:
                                    print(
                                        f"Skipping rename of {item_path}: User aborted."
                                    )
                                skipped_exists += 1
                        else:
                            if not quiet:
                                print(
                                    f"Skipping rename of {item_path}: Destination folder already exists ({new_path}).  Use --force to overwrite."
                                )
                            skipped_exists += 1
                    else:
                        try:
                            os.rename(item_path, new_path)
                            total_renamed += 1
                        except (IOError, OSError) as e:
                            print(
                                f"Error renaming {item_path} to {new_path}: {e}",
                                file=sys.stderr,
                            )
            elif not quiet:
                print(f"Skipping non-appid folder: {item_path}")

    if not quiet:
        print(
            f"Finished! Renamed {total_renamed} folders, skipped {skipped_not_found} folders (app name not found), skipped {skipped_exists} folders (destination exists), from {num_apps} appid folders."
        )


def natural_sort_key(s):
    return [
        int(text) if text.isdigit() else text.lower()
        for text in re.split("([0-9]+)", s)
    ]


def generate_html_gallery(
    output_html: str = "gallery.html",
    screenshots_dir: str = "output",
    quiet: bool = False,
):
    """Generates an HTML gallery of screenshots."""

    supported_extensions = (".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp")
    images_by_category = {}

    if not os.path.isdir(screenshots_dir):
        print(
            f"Error: Screenshots directory not found: {screenshots_dir}",
            file=sys.stderr,
        )
        sys.exit(1)
    if not quiet:
        print(f"Scanning folder: {screenshots_dir}")

    for root, _, files in os.walk(screenshots_dir):
        category_name = os.path.basename(root)
        category_name = html.escape(category_name).replace(
            "®", "®"
        )  # Escape and replace ®
        images_by_category[category_name] = []
        for file in files:
            if file.lower().endswith(supported_extensions):
                # Also escape the filename itself.
                file = html.escape(file).replace("®", "®")
                images_by_category[category_name].append(os.path.join(root, file))

    for category, images in images_by_category.items():
        # Separate numerical and alphabetical filenames for sorting
        alphabetical = sorted(
            [img for img in images if not re.match(r"^\d", os.path.basename(img))],
            key=natural_sort_key,
        )
        numerical = sorted(
            [img for img in images if re.match(r"^\d", os.path.basename(img))],
            key=natural_sort_key,
        )
        images_by_category[category] = alphabetical + numerical  # type: ignore

    sorted_categories = sorted(
        images_by_category.keys(),
        key=lambda k: (not k[0].isalpha(), natural_sort_key(k)),
    )
    images_by_category = {
        k: images_by_category[k] for k in sorted_categories if images_by_category[k]
    }

    if not images_by_category:
        print("No images found in the specified folder.", file=sys.stderr)
        sys.exit(1)

    # --- Debugging output ---
    print(f"DEBUG: output_html = {output_html}")
    print(f"DEBUG: os.path.abspath(output_html) = {os.path.abspath(output_html)}")
    # --- End debugging output ---

    # Build HTML content
    html_content = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Steam Screenshots Gallery</title>
    <style>
        :root {
            --bg-color: #1a1a1a;
            --text-color: #eee;
            --accent-color: #00aaff;
            --category-bg: rgba(255, 255, 255, 0.08);
            --category-border: rgba(255, 255, 255, 0.15);
            --image-shadow: 0 4px 12px rgba(0, 0, 0, 0.5);
            --lightbox-bg: rgba(0, 0, 0, 0.9);
        }
        *, *::before, *::after { /* CSS Reset */
            box-sizing: border-box;
            margin: 0;
            padding: 0;
        }
        body {
            background-color: var(--bg-color);
            color: var(--text-color);
            font-family: 'Roboto', sans-serif;
            padding: 20px;
        }
        /* Include Google Fonts */
        @import url('https://fonts.googleapis.com/css2?family=Roboto:wght@400;700&display=swap');

        h1 {
            text-align: center;
            margin-bottom: 30px;
            font-size: 3rem;
            color: #fff;
            text-shadow: 2px 2px 4px rgba(0, 0, 0, 0.5);
        }
        .search-bar {
            display: flex;
            justify-content: center;
            margin-bottom: 30px;
        }
        .search-bar input {
            padding: 12px 18px;
            width: 60%;
            max-width: 600px;
            border: none;
            border-radius: 20px;
            background: rgba(255, 255, 255, 0.1);
            color: #fff;
            font-size: 18px;
            box-shadow: 0 4px 8px rgba(0, 0, 0, 0.5);
            backdrop-filter: blur(10px);
            outline: none;
            transition: background 0.3s ease, box-shadow 0.3s ease;
        }
        .search-bar input:focus {
            background: rgba(255, 255, 255, 0.2);
            box-shadow: 0 6px 12px rgba(0, 0, 0, 0.7);
        }
        .search-bar input::placeholder {
            color: #cccccc;
        }
       .categories-container {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); /* Adjust minmax as needed */
            gap: 20px; /* Space between categories */
        }
        .category {
            margin-top: 20px;
            background: var(--category-bg);
            border-radius: 15px;
            padding: 15px 25px;
            box-shadow: 0 4px 8px rgba(0, 0, 0, 0.5);
            border: 1px solid var(--category-border);
        }
        .category-title {
            font-size: 2rem;
            margin: 0;
            padding: 15px 0;
            cursor: pointer;
            display: flex;
            justify-content: space-between;
            align-items: center;
            border-bottom: 1px solid rgba(255, 255, 255, 0.2);
            margin-bottom: 15px;
        }
        .category-title:hover {
            color: var(--accent-color);
        }
        .category-title i { /* Style for Font Awesome icon */
            margin-left: 10px;
            font-size: 1.5em;
        }

       .gallery {
            column-count: 4; /* Start with 4 columns */
            column-gap: 20px;
            margin-top: 15px;
        }

        /* Responsive adjustments */
        @media (max-width: 1200px) {
            .gallery {
                column-count: 3; /* 3 columns on smaller screens */
            }
        }

        @media (max-width: 900px) {
            .gallery {
                column-count: 2; /* 2 columns on even smaller screens */
            }
        }
        @media (max-width: 600px) {
            .gallery{
                column-count: 1;
            }
        }


        .gallery a {
            display: block; /* Important for consistent spacing */
            margin-bottom: 20px; /* Space between images */
            break-inside: avoid; /* Avoid breaking images across columns */
            position: relative; /* Needed for the overlay positioning */
            overflow: hidden;
            border-radius: 8px;
        }

        .gallery img {
            width: 100%; /* Make images fill their container */
            display: block; /* Remove extra space below inline elements */
            border-radius: 8px;
            cursor: pointer;
            transition: transform 0.2s ease, box-shadow 0.2s ease, opacity 0.4s ease; /* Add opacity transition */
            box-shadow: 0 2px 10px rgba(0, 0, 0, 0.5); /* Consistent shadow */
            opacity: 0;  /* Initially hidden for fade-in */
            animation: fadeIn 0.5s ease forwards; /* Apply fade-in animation */
        }

        .gallery img:hover {
            transform: scale(1.03); /* Smaller zoom */
            box-shadow: 0 4px 15px rgba(0, 0, 0, 0.6);
        }
        /* Keyframes for fade-in animation */
        @keyframes fadeIn {
            from { opacity: 0; }
            to   { opacity: 1; }
        }


       .lightbox {
            display: none;
            position: fixed;
            z-index: 9999;
            left: 0;
            top: 0;
            width: 100%;
            height: 100%;
            background-color: rgba(0, 0, 0, 0.9);
            justify-content: center;
            align-items: center;
            cursor: pointer;
            backdrop-filter: blur(8px);
        }

        .lightbox img {
            max-width: 95%;
            max-height: 95%;
            border-radius: 8px;
            transition: transform 0.3s ease;
            box-shadow: 0 4px 20px rgba(0, 0, 0, 0.7);
        }

        .lightbox:target {
            display: flex;
            animation: fadeIn 0.3s ease; /* Apply fade-in to lightbox */

        }
        /* Media query for smaller screens */
        @media (max-width: 768px) {
            .gallery {
                grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); /* Smaller images on small screens */
            }
            .search-bar input{
                width: 95%;
            }
        }
        /*Placeholder Styling*/
        .gallery img[src="placeholder.svg"] {
           filter: invert(1) brightness(0.2); /* Make it dark and less prominent */
        }
        /* Style for the "Back to Top" button */
        #backToTopBtn {
            display: none; /* Hidden by default */
            position: fixed; /* Fixed position */
            bottom: 20px; /* Distance from the bottom */
            right: 30px; /* Distance from the right */
            z-index: 99; /* Make sure it sits on top */
            font-size: 24px; /* Increase font size */
            border: none;
            outline: none;
            background-color: var(--accent-color);
            color: white;
            cursor: pointer;
            padding: 15px;
            border-radius: 50%; /* Make it circular */
            box-shadow: 0 4px 8px rgba(0, 0, 0, 0.7); /* Add a shadow */
            transition: background-color 0.3s ease, transform 0.3s ease; /* Smooth transitions */
        }

        #backToTopBtn:hover {
            background-color: #007acc; /* Darker on hover */
            transform: translateY(-5px); /* Slightly move up on hover */
        }

    </style>
     <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css">
</head>
<body>
    <h1>Steam Screenshots Gallery</h1>
    <div class="search-bar">
        <input type="text" id="search" placeholder="Search categories..." onkeyup="filterCategories()">
    </div>
"""

    # Preload the first image of each category for faster initial load
    preload_links = ""
    for category, images in images_by_category.items():
        if images:
            first_image_relative_path = os.path.relpath(
                images[0], start=os.path.dirname(output_html)
            )
            preload_links += (
                f'<link rel="preload" href="{first_image_relative_path}" as="image">\n'
            )

    html_content = html_content.replace("</head>", preload_links + "</head>")
    html_content += '<div class="categories-container">'  # Wrap categories
    for category, images in images_by_category.items():
        # Add the image count to the category title.
        num_images = len(images)
        html_content += f"""
    <div class="category" data-category="{category}">
        <h2 class="category-title">
            {category} ({num_images} images)
            <i class="fas fa-plus category-toggle-icon"></i>
        </h2>
        <div class="gallery" style="display: none;">
"""
        for index, screenshot_path in enumerate(images):
            relative_path = os.path.relpath(
                screenshot_path, start=os.path.dirname(output_html)
            )
            html_content += f"""
            <a href="#lightbox-{category}-{index}">
                <img src="{relative_path}" alt="Screenshot" loading="lazy">
            </a>
            <div id="lightbox-{category}-{index}" class="lightbox" onclick="closeLightbox()">
                <img src="{relative_path}" alt="Screenshot">
            </div>
"""
        html_content += "</div></div>"
    html_content += "</div>"  # Close categories-container

    html_content += """
    <button onclick="topFunction()" id="backToTopBtn" title="Go to top"><i class="fas fa-arrow-up"></i></button>
    <script>
        //Get the button:
        mybutton = document.getElementById("backToTopBtn");

        // When the user scrolls down 20px from the top of the document, show the button
        window.onscroll = function() {scrollFunction()};

        function scrollFunction() {
          if (document.body.scrollTop > 20 || document.documentElement.scrollTop > 20) {
            mybutton.style.display = "block";
          } else {
            mybutton.style.display = "none";
          }
        }

        // When the user clicks on the button, scroll to the top of the document
        function topFunction() {
            // For Safari
            document.body.scrollTop = 0;
            // For Chrome, Firefox, IE and Opera
            document.documentElement.scrollTop = 0;

            // or  window.scrollTo({top: 0, behavior: 'smooth'});
        }

    function filterCategories() {
        const searchInput = document.getElementById('search').value.toLowerCase();
        const categories = document.querySelectorAll('.category');

        categories.forEach(category => {
            const categoryName = category.dataset.category.toLowerCase();
            const gallery = category.querySelector('.gallery');
            let hasVisibleImages = false;

            // Check if the category name matches
            if (categoryName.includes(searchInput)) {
                category.style.display = 'block'; // Show the category
                hasVisibleImages = true; // We know at least the category is visible (potentially no images, but that's fine)
            } else {
                // If category name doesn't match, check the images WITHIN that category
                let images = gallery.querySelectorAll('img');
                let allImagesHidden = true;

                images.forEach(img => {
                    const imageName = img.src.toLowerCase();
                    if (imageName.includes(searchInput)) {
                        img.style.display = 'block'; // Show matching image
                        hasVisibleImages = true;
                        allImagesHidden = false; // Found at least one visible
                    } else {
                        img.style.display = 'none'; // Hide non-matching image
                    }
                });
                 // Show/hide category based on image visibility
                category.style.display = allImagesHidden ? 'none' : 'block';

            }
        });
    }
        function toggleCategory(event) {
            const category = event.currentTarget.closest('.category');
            const gallery = category.querySelector('.gallery');
            const icon = category.querySelector('.category-toggle-icon');

            if (gallery.style.display === 'none' || gallery.style.display === '') {
                gallery.style.display = 'grid';
                icon.classList.remove('fa-plus');
                icon.classList.add('fa-minus');  // Change to minus icon
            } else {
                gallery.style.display = 'none';
                icon.classList.remove('fa-minus');
                icon.classList.add('fa-plus');   // Change back to plus icon
            }
        }

        function closeLightbox() {
            window.location.hash = '';
        }

        document.addEventListener('DOMContentLoaded', () => {
            document.querySelectorAll('.category-title').forEach(title => {
                title.addEventListener('click', toggleCategory);
            });
        });
    </script>
</body>
</html>
"""

    try:
        with open(output_html, "w", encoding="utf-8") as html_file:
            html_file.write(html_content)
        if not quiet:
            print(f"HTML gallery created at {output_html}")
    except (IOError, OSError) as e:
        print(f"Error writing to HTML file: {e}", file=sys.stderr)
        sys.exit(1)

    # Check if file exists
    if not os.path.exists(output_html):
        print(f"Error. HTML file not created at {output_html}", file=sys.stderr)
        sys.exit(1)


def main():
    """Main entry point for the script."""
    arguments = docopt(__doc__, version="SSU 0.1")
    quiet = arguments["--quiet"]
    dry_run = arguments["--dry-run"]
    force_update = arguments["--update"]
    force = arguments["--force"]  # For rename

    appid_converter = AppidConverter(APPID_CACHE_FILE, quiet, force_update)

    try:
        if arguments["backup"]:
            backup(
                arguments["<steam_user_folder>"],
                appid_converter,
                arguments["-o"],
                quiet,
                dry_run,
            )
        elif arguments["sort"]:
            sort(arguments["<screenshots_folder>"], appid_converter, quiet, dry_run)
        elif arguments["merge"]:
            merge(
                arguments["<compressed_screenshots>"],
                arguments["<uncompressed_screenshots>"],
                appid_converter,
                quiet,
                dry_run,
            )
        elif arguments["rename"]:
            rename(
                arguments["<screenshots_folder>"],
                appid_converter,
                quiet,
                dry_run,
                force_update,
                force,
            )  # Pass force
        elif arguments["gallery"]:
            output_html = (
                arguments["-o"] or "gallery.html"
            )  # Use default if -o isn't provided
            screenshots_dir = (
                arguments["-d"] or "output"
            )  # Use default if -d isn't provided
            generate_html_gallery(output_html, screenshots_dir, quiet)

    except Exception as e:
        print(f"An unexpected error occurred: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
