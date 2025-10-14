"""
SSU: Steam Screenshot Utils.

- Back up Steam screenshots by specifying your Steam user folder.
  Categorizes them into folders with the corresponding app names.
  (Useful when you don't have the "Save uncompressed copy" option enabled).

- Sort uncompressed screenshots into folders with the corresponding app names.
  (Useful when you have the "Save uncompressed copy" option enabled).

- Merge backed up compressed screenshots with sorted uncompressed screenshots.
  This copies compressed screenshots to the uncompressed screenshots folder whenever
  an uncompressed copy of them is not found.
  (The compressed screenshots backup can be safely removed after this).
  (Useful when you didn't have "Save uncompressed copy" activated at the beginning,
  but activated it at some point afterwards).

Usage:
    ssu backup <steam_user_folder> [-o <output_folder>]
    ssu sort <screenshots_folder>
    ssu merge <compressed_screenshots> <uncompressed_screenshots>

Notes:
    - Your steam user folder is in Steam/userdata/<user_id>.
    - Sorting doesn't have an output argument becasue it's done in-place.
    - For merging, the compressed screenshots folder is expected to be the output of the backup command,
      and the uncompressed screenshots folder is expected to be the output of the sort command.

"""

import glob
import json
import os
import platform
import re
import shutil
import sys

import requests
from docopt import docopt

APPID_CACHE_FILE = "appid_names.json"
DEFAULT_OUTPUT_FOLDER = "backup"


class AppidConverter:
    def __init__(self, cache_file: str):
        self.cache_file = cache_file
        self.appid_names = {}
        self.downloaded_app_data = False

        self._load_appid_names()

    def _download_app_data(self):

        r = requests.get("https://api.steampowered.com/ISteamApps/GetAppList/v0002")
        if r.status_code != 200:
            raise Exception("Error getting app data from Steam API.")
        app_data = r.json()

        appid_names = {
            str(app["appid"]): app["name"] for app in app_data["applist"]["apps"]
        }
        with open(self.cache_file, "w") as f:
            json.dump(appid_names, f)

        self.downloaded_app_data = True
        self.appid_names = appid_names

    def _load_appid_names(self):

        if os.path.exists(self.cache_file):
            print("Loading appid names from local cache...")
            with open(self.cache_file) as f:
                self.appid_names = json.load(f)
        else:
            print("Downloading app data from Steam API...")
            self._download_app_data()

    def get_app_name(self, appid: str):

        name = self.appid_names.get(appid)
        if not name:
            if not self.downloaded_app_data:
                print(
                    f"Appid {appid} not found in local cache, downloading app data from Steam API..."
                )
                self._download_app_data()
                return self.get_app_name(appid)
            else:
                print(
                    f"Appid {appid} not found in the Steam database, skipping name conversion."
                )
                return appid
        return name


def sanitize_app_name(name):

    if platform.system() == "Windows":
        return re.sub(r'[<>:"/\\|?*]', "", name)
    else:

        return re.sub(r"[/]", "", name)


def create_app_folder(root_folder, app_name, appid):

    app_folder = os.path.join(root_folder, app_name)
    try:
        os.makedirs(app_folder, exist_ok=True)
        return app_folder
    except Exception:
        print(
            f'Could not create a folder with the app name "{app_name}".\n'
            f"Using appid ({appid})."
        )
        app_folder = os.path.join(root_folder, appid)
        os.makedirs(app_folder, exist_ok=True)
        return appid


def backup(steam_user_folder, output_folder=None):

    screenshots_folder = os.path.join(steam_user_folder, "760", "remote")
    if not os.path.exists(screenshots_folder):
        print(
            f"Could not find the screenshots folder at {screenshots_folder}.\n"
            f"Make sure the steam user folder is correct."
        )
        sys.exit(1)

    if not output_folder:
        output_folder = DEFAULT_OUTPUT_FOLDER
    os.makedirs(output_folder, exist_ok=True)

    appid_converter = AppidConverter(APPID_CACHE_FILE)

    for appid in os.listdir(screenshots_folder):

        appid_folder = os.path.join(screenshots_folder, appid)
        if not os.path.isdir(appid_folder):
            continue

        app_name = appid_converter.get_app_name(appid)
        sanitized_app_name = sanitize_app_name(app_name)

        app_folder = create_app_folder(output_folder, sanitized_app_name, appid)

        print(f"Backing up screenshots from {app_name}...", end=" ")
        screenshots_pattern = os.path.join(appid_folder, "screenshots", "*.jpg")
        count = 0
        for screenshot in glob.glob(screenshots_pattern):

            screenshot_filename = os.path.basename(screenshot)
            if not os.path.exists(os.path.join(app_folder, screenshot_filename)):
                shutil.copy2(screenshot, app_folder)
                count += 1
        msg = f"Copied {count}" if count else "No"
        print(f"{msg} new screenshots.")

    print("Finished!")


def sort(screenshots_folder):

    if not os.path.exists(screenshots_folder):
        print(f"Could not find the specified screenshots folder: {screenshots_folder}")
        sys.exit(1)

    appid_converter = AppidConverter(APPID_CACHE_FILE)

    appid_sp_sf = {}
    for screenshot in glob.glob(os.path.join(screenshots_folder, "*.png")):

        appid, screenshot_filename = os.path.basename(screenshot).split("_", 1)
        if appid not in appid_sp_sf:
            appid_sp_sf[appid] = []
        appid_sp_sf[appid].append((screenshot, screenshot_filename))

    for appid, sp_sf_list in appid_sp_sf.items():

        app_name = appid_converter.get_app_name(appid)
        sanitized_app_name = sanitize_app_name(app_name)

        app_folder = create_app_folder(screenshots_folder, sanitized_app_name, appid)

        print(f"Sorting screenshots from {app_name}...", end=" ")
        count = 0
        for screenshot_path, screenshot_filename in sp_sf_list:
            destination_path = os.path.join(app_folder, screenshot_filename)
            os.rename(screenshot_path, destination_path)
            count += 1
        print(f"Moved {count} new screenshots.")

    print("Finished!")


def merge(compressed_folder, uncompressed_folder):

    if not os.path.exists(compressed_folder):
        print(f"Could not find the compressed screenshots folder: {compressed_folder}")
        sys.exit(1)
    if not os.path.exists(uncompressed_folder):
        print(
            f"Could not find the uncompressed screenshots folder: {uncompressed_folder}"
        )
        sys.exit(1)

    for app_name in os.listdir(compressed_folder):

        app_folder_compressed = os.path.join(compressed_folder, app_name)
        if not os.path.isdir(app_folder_compressed):
            continue

        app_folder_uncompressed = os.path.join(uncompressed_folder, app_name)
        os.makedirs(app_folder_uncompressed, exist_ok=True)

        uncompressed_screenshots = []
        for ext in ["*.png", "*.jpg"]:
            for screenshot in glob.glob(os.path.join(app_folder_uncompressed, ext)):
                uncompressed_ss_name, _ = os.path.splitext(os.path.basename(screenshot))
                uncompressed_screenshots.append(uncompressed_ss_name)

        print(f"Merging screenshots from {app_name}...", end=" ")
        count = 0
        for screenshot in glob.glob(os.path.join(app_folder_compressed, "*.jpg")):
            compressed_ss_name, _ = os.path.splitext(os.path.basename(screenshot))
            if compressed_ss_name not in uncompressed_screenshots:
                shutil.copy2(screenshot, app_folder_uncompressed)
                count += 1
        msg = f"Added {count}" if count else "No"
        print(f"{msg} new compressed screenshots.")

    print("Finished!")


if __name__ == "__main__":

    if len(sys.argv) == 1:
        print(__doc__)
        sys.exit()

    args = docopt(__doc__, version="SSU 0.1")
    if args["backup"]:
        backup(args["<steam_user_folder>"], args["<output_folder>"])
    elif args["sort"]:
        sort(args["<screenshots_folder>"])
    elif args["merge"]:
        merge(args["<compressed_screenshots>"], args["<uncompressed_screenshots>"])
