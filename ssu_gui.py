"""
Steam Screenshot Utils - GUI Version

A modern graphical interface for the Steam Screenshot Utils application.
Built with CustomTkinter for a clean, modern look.
"""

import customtkinter as ctk
import tkinter as tk
from tkinter import filedialog, messagebox
import threading
import queue
import os
import sys
from pathlib import Path

# Import the existing Steam Screenshot Manager
from ssu2 import SteamScreenshotManager, GalleryGenerator, AppIdConverter, setup_logging

# Import configuration manager
from ssu_config import config_manager, SSUConfig

class SSUGUI(ctk.CTk):
    """Main GUI class for Steam Screenshot Utils."""

    def __init__(self):
        super().__init__()

        # GUI state variables (must be created before loading config)
        self.steam_path = tk.StringVar()
        self.output_path = tk.StringVar()
        self.screenshots_path = tk.StringVar()
        self.dry_run = tk.BooleanVar()
        self.force_rename = tk.BooleanVar()

        # Load configuration first
        self.load_configuration()

        # Initialize core components
        self.logger = setup_logging(quiet=False)
        self.manager = SteamScreenshotManager(self.logger, quiet=False)
        self.gallery_generator = GalleryGenerator(self.logger, quiet=False)

        # Queue for thread communication
        self.queue = queue.Queue()

        self.setup_gui()
        self.check_queue()  # Start checking for thread messages

    def load_configuration(self):
        """Load configuration from file."""
        global config_manager
        self.config = config_manager.load_config()

        # Apply window settings
        self.geometry(f"{self.config.window_width}x{self.config.window_height}")

        # Apply theme
        ctk.set_appearance_mode(self.config.theme)

        # Load saved paths into GUI fields
        self.steam_path.set(self.config.paths.get("steam", ""))
        self.output_path.set(self.config.paths.get("output", ""))
        self.screenshots_path.set(self.config.paths.get("screenshots", ""))

    def browse_steam_folder(self):
        """Browse for Steam user folder."""
        folder = filedialog.askdirectory(title="Select Steam User Folder")
        if folder:
            self.steam_path.set(folder)
            config_manager.update_path("steam", folder)
            self.log_message(f"Selected Steam folder: {folder}")

    def browse_output_folder(self):
        """Browse for output folder."""
        folder = filedialog.askdirectory(title="Select Output Folder")
        if folder:
            self.output_path.set(folder)
            config_manager.update_path("output", folder)
            self.log_message(f"Selected output folder: {folder}")

    def browse_screenshots_folder(self):
        """Browse for screenshots folder."""
        folder = filedialog.askdirectory(title="Select Screenshots Folder")
        if folder:
            self.screenshots_path.set(folder)
            config_manager.update_path("screenshots", folder)
            self.log_message(f"Selected screenshots folder: {folder}")

    def setup_gui(self):
        """Set up the main GUI layout."""
        # Window configuration
        self.title("Steam Screenshot Utils")
        self.geometry("900x700")
        self.minsize(800, 600)

        # Configure grid weights
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # Create main container
        self.main_container = ctk.CTkFrame(self)
        self.main_container.grid(row=0, column=0, padx=20, pady=20, sticky="nsew")
        self.main_container.grid_columnconfigure(0, weight=1)

        self.create_path_selection_section()
        self.create_operations_section()
        self.create_options_section()
        self.create_progress_section()
        self.create_log_section()

    def create_path_selection_section(self):
        """Create the file/folder path selection section."""
        path_frame = ctk.CTkFrame(self.main_container)
        path_frame.grid(row=0, column=0, padx=10, pady=10, sticky="ew")
        path_frame.grid_columnconfigure(1, weight=1)

        # Title
        title_label = ctk.CTkLabel(
            path_frame,
            text="📁 Path Selection",
            font=ctk.CTkFont(size=16, weight="bold")
        )
        title_label.grid(row=0, column=0, columnspan=2, pady=(0, 15))

        # Steam User Folder
        ctk.CTkLabel(path_frame, text="Steam User Folder:").grid(row=1, column=0, sticky="w", padx=5)
        steam_entry = ctk.CTkEntry(path_frame, textvariable=self.steam_path)
        steam_entry.grid(row=1, column=1, padx=5, pady=5, sticky="ew")

        steam_browse_btn = ctk.CTkButton(
            path_frame,
            text="Browse",
            command=self.browse_steam_folder,
            width=80
        )
        steam_browse_btn.grid(row=1, column=2, padx=5, pady=5)

        # Output Folder
        ctk.CTkLabel(path_frame, text="Output Folder:").grid(row=2, column=0, sticky="w", padx=5)
        output_entry = ctk.CTkEntry(path_frame, textvariable=self.output_path)
        output_entry.grid(row=2, column=1, padx=5, pady=5, sticky="ew")

        output_browse_btn = ctk.CTkButton(
            path_frame,
            text="Browse",
            command=self.browse_output_folder,
            width=80
        )
        output_browse_btn.grid(row=2, column=2, padx=5, pady=5)

        # Screenshots Folder (for sort/rename operations)
        ctk.CTkLabel(path_frame, text="Screenshots Folder:").grid(row=3, column=0, sticky="w", padx=5)
        screenshots_entry = ctk.CTkEntry(path_frame, textvariable=self.screenshots_path)
        screenshots_entry.grid(row=3, column=1, padx=5, pady=5, sticky="ew")

        screenshots_browse_btn = ctk.CTkButton(
            path_frame,
            text="Browse",
            command=self.browse_screenshots_folder,
            width=80
        )
        screenshots_browse_btn.grid(row=3, column=2, padx=5, pady=5)

    def create_operations_section(self):
        """Create the operations buttons section."""
        ops_frame = ctk.CTkFrame(self.main_container)
        ops_frame.grid(row=1, column=0, padx=10, pady=10, sticky="ew")

        # Title
        title_label = ctk.CTkLabel(
            ops_frame,
            text="⚡ Operations",
            font=ctk.CTkFont(size=16, weight="bold")
        )
        title_label.pack(anchor="w", pady=(0, 15))

        # Button container
        button_container = ctk.CTkFrame(ops_frame)
        button_container.pack(fill="x")

        # Row 1: Main operations
        row1_frame = ctk.CTkFrame(button_container)
        row1_frame.pack(fill="x", pady=5)

        ctk.CTkButton(
            row1_frame,
            text="🔄 Backup Screenshots",
            command=self.run_backup,
            fg_color="#1f6aa5",
            hover_color="#1a5a8a"
        ).pack(side="left", expand=True, padx=5)

        ctk.CTkButton(
            row1_frame,
            text="📂 Sort Screenshots",
            command=self.run_sort,
            fg_color="#2e7d32",
            hover_color="#256b28"
        ).pack(side="left", expand=True, padx=5)

        # Row 2: Secondary operations
        row2_frame = ctk.CTkFrame(button_container)
        row2_frame.pack(fill="x", pady=5)

        ctk.CTkButton(
            row2_frame,
            text="🎨 Generate Gallery",
            command=self.run_gallery,
            fg_color="#8e24aa",
            hover_color="#7b1fa2"
        ).pack(side="left", expand=True, padx=5)

        ctk.CTkButton(
            row2_frame,
            text="✏️ Rename Folders",
            command=self.run_rename,
            fg_color="#f57c00",
            hover_color="#ef6c00"
        ).pack(side="left", expand=True, padx=5)

        # Row 3: Utility operations
        row3_frame = ctk.CTkFrame(button_container)
        row3_frame.pack(fill="x", pady=5)

        ctk.CTkButton(
            row3_frame,
            text="🔄 Update App Cache",
            command=self.run_update_cache,
            fg_color="#455a64",
            hover_color="#37474f"
        ).pack(side="left", expand=True, padx=5)

        ctk.CTkButton(
            row3_frame,
            text="🧹 Merge Screenshots",
            command=self.run_merge,
            fg_color="#d32f2f",
            hover_color="#b71c1c"
        ).pack(side="left", expand=True, padx=5)

    def create_options_section(self):
        """Create the options checkboxes section."""
        options_frame = ctk.CTkFrame(self.main_container)
        options_frame.grid(row=2, column=0, padx=10, pady=10, sticky="ew")

        title_label = ctk.CTkLabel(
            options_frame,
            text="⚙️ Options",
            font=ctk.CTkFont(size=16, weight="bold")
        )
        title_label.pack(anchor="w", pady=(0, 10))

        # Checkboxes
        self.dry_run_cb = ctk.CTkCheckBox(
            options_frame,
            text="Dry Run (Preview only)",
            variable=self.dry_run
        )
        self.dry_run_cb.pack(anchor="w", pady=5)

        self.force_cb = ctk.CTkCheckBox(
            options_frame,
            text="Force Rename (Dangerous - overwrites existing)",
            variable=self.force_rename
        )
        self.force_cb.pack(anchor="w", pady=5)

    def create_progress_section(self):
        """Create the progress bar section."""
        progress_frame = ctk.CTkFrame(self.main_container)
        progress_frame.grid(row=3, column=0, padx=10, pady=10, sticky="ew")

        title_label = ctk.CTkLabel(
            progress_frame,
            text="📊 Progress",
            font=ctk.CTkFont(size=16, weight="bold")
        )
        title_label.pack(anchor="w", pady=(0, 10))

        self.progress_bar = ctk.CTkProgressBar(progress_frame)
        self.progress_bar.pack(fill="x", pady=5)
        self.progress_bar.set(0)

        self.progress_label = ctk.CTkLabel(progress_frame, text="Ready")
        self.progress_label.pack(anchor="w")

    def create_log_section(self):
        """Create the log output section."""
        log_frame = ctk.CTkFrame(self.main_container)
        log_frame.grid(row=4, column=0, padx=10, pady=10, sticky="ew")
        log_frame.grid_rowconfigure(0, weight=1)
        log_frame.grid_columnconfigure(0, weight=1)

        title_label = ctk.CTkLabel(
            log_frame,
            text="📋 Activity Log",
            font=ctk.CTkFont(size=16, weight="bold")
        )
        title_label.grid(row=0, column=0, sticky="w")

        # Scrollable log area
        self.log_text = ctk.CTkTextbox(log_frame, wrap="word")
        self.log_text.grid(row=1, column=0, padx=5, pady=5, sticky="nsew")

        # Scrollbar
        scrollbar = ctk.CTkScrollbar(log_frame, command=self.log_text.yview)
        scrollbar.grid(row=1, column=1, sticky="ns")
        self.log_text.configure(yscrollcommand=scrollbar.set)

        # Clear button
        clear_btn = ctk.CTkButton(
            log_frame,
            text="Clear Log",
            command=self.clear_log,
            width=100
        )
        clear_btn.grid(row=2, column=0, columnspan=2, pady=5)



    def run_backup(self):
        """Run backup operation in a separate thread."""
        if not self.steam_path.get():
            messagebox.showerror("Error", "Please select a Steam user folder first.")
            return

        self.run_in_thread("backup", self.backup_thread)

    def run_sort(self):
        """Run sort operation in a separate thread."""
        if not self.screenshots_path.get():
            messagebox.showerror("Error", "Please select a screenshots folder first.")
            return

        self.run_in_thread("sort", self.sort_thread)

    def run_gallery(self):
        """Run gallery generation in a separate thread."""
        if not self.screenshots_path.get():
            messagebox.showerror("Error", "Please select a screenshots folder first.")
            return

        self.run_in_thread("gallery", self.gallery_thread)

    def run_rename(self):
        """Run rename operation in a separate thread."""
        if not self.screenshots_path.get():
            messagebox.showerror("Error", "Please select a screenshots folder first.")
            return

        self.run_in_thread("rename", self.rename_thread)

    def run_update_cache(self):
        """Run cache update operation in a separate thread."""
        self.run_in_thread("update", self.update_thread)

    def run_merge(self):
        """Run merge operation in a separate thread."""
        # For merge, we need both compressed and uncompressed folders
        # This would need additional UI elements for selecting both folders
        messagebox.showinfo("Info", "Merge operation requires additional folder selection UI.")

    def run_in_thread(self, operation_name, thread_func):
        """Run an operation in a separate thread."""
        thread = threading.Thread(target=thread_func, daemon=True)
        thread.start()
        self.log_message(f"Started {operation_name} operation...")

    def backup_thread(self):
        """Thread function for backup operation."""
        try:
            self.queue.put(("progress", 0, "Starting backup..."))
            stats = self.manager.backup_screenshots(
                self.steam_path.get(),
                self.output_path.get() if self.output_path.get() else None,
                self.dry_run.get()
            )
            self.queue.put(("complete", "backup", stats))
        except Exception as e:
            self.queue.put(("error", str(e)))

    def sort_thread(self):
        """Thread function for sort operation."""
        try:
            self.queue.put(("progress", 0, "Starting sort..."))
            stats = self.manager.sort_screenshots(
                self.screenshots_path.get(),
                self.dry_run.get()
            )
            self.queue.put(("complete", "sort", stats))
        except Exception as e:
            self.queue.put(("error", str(e)))

    def gallery_thread(self):
        """Thread function for gallery generation."""
        try:
            self.queue.put(("progress", 0, "Generating gallery..."))
            output_file = os.path.join(
                self.output_path.get() if self.output_path.get() else "output",
                "gallery.html"
            )
            self.gallery_generator.generate_gallery(
                self.screenshots_path.get(),
                output_file
            )
            self.queue.put(("complete", "gallery", {"output": output_file}))
        except Exception as e:
            self.queue.put(("error", str(e)))

    def rename_thread(self):
        """Thread function for rename operation."""
        try:
            self.queue.put(("progress", 0, "Starting rename..."))
            stats = self.manager.rename_app_folders(
                self.screenshots_path.get(),
                self.force_rename.get(),
                self.dry_run.get()
            )
            self.queue.put(("complete", "rename", stats))
        except Exception as e:
            self.queue.put(("error", str(e)))

    def update_thread(self):
        """Thread function for cache update."""
        try:
            self.queue.put(("progress", 0, "Updating app cache..."))
            appid_converter = AppIdConverter(
                quiet=False, force_update=True, logger=self.logger
            )
            self.queue.put(("complete", "update", {"message": "Cache updated successfully"}))
        except Exception as e:
            self.queue.put(("error", str(e)))

    def check_queue(self):
        """Check for messages from worker threads."""
        try:
            while True:
                message = self.queue.get_nowait()
                msg_type = message[0]

                if msg_type == "progress":
                    progress, status = message[1], message[2]
                    self.progress_bar.set(progress)
                    self.progress_label.configure(text=status)

                elif msg_type == "complete":
                    operation, stats = message[1], message[2]
                    self.progress_bar.set(1.0)
                    self.progress_label.configure(text="Complete!")

                    # Show results
                    self.show_operation_results(operation, stats)

                    # Reset progress after a delay
                    self.after(2000, lambda: self.reset_progress())

                elif msg_type == "error":
                    error_msg = message[1]
                    self.progress_label.configure(text="Error!")
                    messagebox.showerror("Operation Failed", f"An error occurred:\n\n{error_msg}")
                    self.reset_progress()

        except queue.Empty:
            pass

        # Check again after 100ms
        self.after(100, self.check_queue)

    def show_operation_results(self, operation, stats):
        """Show the results of an operation."""
        if operation == "backup":
            message = f"Backup completed successfully!\n\n" \
                     f"Apps processed: {stats['apps']}\n" \
                     f"Screenshots backed up: {stats['screenshots']}\n" \
                     f"Total size: {stats['bytes'] / 1024 / 1024:.1f} MB"
        elif operation == "sort":
            message = f"Sort completed successfully!\n\n" \
                     f"Apps processed: {stats['apps']}\n" \
                     f"Screenshots sorted: {stats['screenshots']}"
        elif operation == "gallery":
            message = f"Gallery generated successfully!\n\n" \
                     f"Output file: {stats['output']}\n\n" \
                     f"Open gallery.html in your browser to view."
        elif operation == "rename":
            message = f"Rename completed!\n\n" \
                     f"Renamed: {stats['renamed']}\n" \
                     f"Skipped (not found): {stats['skipped_not_found']}\n" \
                     f"Skipped (exists): {stats['skipped_exists']}"
        elif operation == "update":
            message = stats['message']
        else:
            message = "Operation completed successfully!"

        self.log_message(f"✓ {message}")
        messagebox.showinfo("Operation Complete", message)

    def reset_progress(self):
        """Reset the progress bar and label."""
        self.progress_bar.set(0)
        self.progress_label.configure(text="Ready")

    def log_message(self, message):
        """Add a message to the log."""
        self.log_text.insert("end", f"{message}\n")
        self.log_text.see("end")  # Scroll to the end

    def clear_log(self):
        """Clear the log output."""
        self.log_text.delete("1.0", "end")


def main():
    """Main entry point for the GUI application."""
    # Set appearance mode
    ctk.set_appearance_mode("dark")  # Dark mode for modern look
    ctk.set_default_color_theme("blue")

    # Create and run the application
    app = SSUGUI()
    app.mainloop()


if __name__ == "__main__":
    main()
