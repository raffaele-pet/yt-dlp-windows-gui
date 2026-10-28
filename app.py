from __future__ import annotations

import json
import locale
import os
import queue
import re
import subprocess
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from urllib.parse import urlparse


APP_NAME = "YT-DLP"
APP_DIR = Path(__file__).resolve().parent
ICON_PNG = APP_DIR / "assets" / "yt-dlp-icon.png"
ICON_ICO = APP_DIR / "assets" / "yt-dlp-icon.ico"
VENV_PYTHON = APP_DIR / ".venv" / "Scripts" / "python.exe"
VENV_YTDLP = APP_DIR / ".venv" / "Scripts" / "yt-dlp.exe"
REQUIREMENTS = APP_DIR / "requirements.txt"
PLUGIN_DIR = APP_DIR / "plugins"

COLOR_BACKGROUND = "#0D1117"
COLOR_SURFACE = "#161B22"
COLOR_SURFACE_HOVER = "#21262D"
COLOR_BORDER = "#30363D"
COLOR_RED = "#FF0000"
COLOR_RED_HOVER = "#D90000"
COLOR_WHITE = "#FFFFFF"
COLOR_MUTED = "#C9D1D9"

FORMAT_OPTIONS: dict[str, list[str]] = {
    "Video MP4 (consigliato)": [
        "-f",
        "bv*+ba[ext=m4a]/bv*+ba/b",
        "--merge-output-format",
        "mp4",
        "--remux-video",
        "mp4",
    ],
    "Video - qualità massima": ["-f", "bv*+ba/b"],
    "Solo audio MP3": ["-x", "--audio-format", "mp3", "--audio-quality", "0"],
    "Solo audio M4A": ["-x", "--audio-format", "m4a", "--audio-quality", "0"],
}
BEST_RESOLUTION = "Massima disponibile"


def available_resolutions(info: dict, format_name: str) -> list[int]:
    """List video heights across codecs, including VP9 and AV1 above 1080p."""
    if "-f" not in FORMAT_OPTIONS[format_name]:
        return []
    heights: set[int] = set()
    for item in info.get("formats") or []:
        height = item.get("height")
        if (
            not isinstance(height, (int, float)) or height <= 0
            or item.get("vcodec") in {"none", "images"}
            or item.get("has_drm")
        ):
            continue
        heights.add(int(height))
    return sorted(heights, reverse=True)


def build_metadata_command(executable: str, url: str) -> list[str]:
    return [
        executable, "--plugin-dirs", str(PLUGIN_DIR),
        "--dump-single-json", "--skip-download", "--no-playlist",
        "--playlist-items", "1", "--no-warnings", "--no-colors",
        "--encoding", "utf-8", "--socket-timeout", "15", "--retries", "1",
        "--", url,
    ]


def locate_yt_dlp() -> str | None:
    """Find yt-dlp only inside this project's isolated environment."""
    return str(VENV_YTDLP.resolve()) if VENV_YTDLP.is_file() else None


def build_update_command() -> list[str]:
    """Update only the yt-dlp package installed in this project's .venv."""
    return [
        str(VENV_PYTHON), "-m", "pip", "install", "--disable-pip-version-check",
        "--upgrade", "-r", str(REQUIREMENTS),
    ]


def probe_yt_dlp(executable: str) -> str:
    """Confirm that the selected program is the yt-dlp command-line tool."""
    result = subprocess.run(
        [executable, "--version"],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding=locale.getpreferredencoding(False),
        errors="replace",
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        timeout=10,
        check=False,
    )
    version = result.stdout.strip().splitlines()[0] if result.stdout.strip() else ""
    if result.returncode != 0 or not re.match(r"^\d{4}\.\d{2}\.\d{2}", version):
        raise RuntimeError("Il programma trovato non è il comando yt-dlp corretto.")
    return version


def is_valid_url(value: str) -> bool:
    parsed = urlparse(value.strip())
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def build_command(
    executable: str,
    url: str,
    destination: str,
    format_name: str,
    download_playlist: bool,
    resolution: int | None = None,
) -> list[str]:
    command = [
        executable,
        "--plugin-dirs",
        str(PLUGIN_DIR),
        "--newline",
        "--no-colors",
        "--windows-filenames",
        "--progress-template",
        "download:PROGRESS:%(progress._percent_str)s|%(progress._speed_str)s|%(progress._eta_str)s",
        "--print",
        "after_move:FILE:%(filepath)s",
        "-P",
        destination,
        "-o",
        "%(title).180B [%(id)s].%(ext)s",
    ]
    if not download_playlist:
        command.append("--no-playlist")
    format_options = FORMAT_OPTIONS[format_name].copy()
    if resolution is not None and "-f" in format_options:
        # A playlist can contain videos smaller than the requested quality.
        height_filter = f"[height{'<=' if download_playlist else '='}{resolution}]"
        format_options[1] = re.sub(
            r"\bbv?\*?(?=\[|[+/]|$)",
            lambda match: match[0] + height_filter, format_options[1],
        )
    command.extend(format_options)
    command.extend(["--", url])
    return command


class YtDlpApp:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title(APP_NAME)
        self.app_icon: tk.PhotoImage | None = None
        try:
            self.app_icon = tk.PhotoImage(file=str(ICON_PNG))
            self.root.iconphoto(True, self.app_icon)
            if ICON_ICO.is_file():
                self.root.iconbitmap(default=str(ICON_ICO))
        except tk.TclError:
            self.app_icon = None
        self.root.geometry("780x720")
        self.root.minsize(680, 660)
        self.root.configure(background=COLOR_BACKGROUND)

        self.messages: queue.Queue[tuple] = queue.Queue()
        self.process: subprocess.Popen[str] | None = None
        self.active_operation: str | None = None
        self.cancel_requested = False
        self.downloaded_files: list[str] = []
        self.active_destination: Path | None = None
        self.destination_snapshot: dict[str, tuple[int, int]] = {}
        self.metadata_after: str | None = None
        self.metadata_revision = 0
        self.metadata_loading = False
        self.metadata_url: str | None = None
        self.metadata_info: dict = {}
        self.metadata_error = False

        self.url_var = tk.StringVar()
        default_downloads = Path.home() / "Downloads"
        self.destination_var = tk.StringVar(value=str(default_downloads))
        self.format_var = tk.StringVar(value="Video MP4 (consigliato)")
        self.resolution_var = tk.StringVar(value=BEST_RESOLUTION)
        self.resolution_hint = tk.StringVar(value="Incolla un link per leggere le risoluzioni disponibili.")
        self.playlist_var = tk.BooleanVar(value=False)
        self.status_var = tk.StringVar(value="Pronto")
        self.detail_var = tk.StringVar(value="Incolla il link di un video per iniziare.")
        self.progress_var = tk.DoubleVar(value=0)

        self._configure_style()
        self._build_ui()
        self.url_var.trace_add("write", self._url_changed)
        self.format_var.trace_add("write", lambda *_args: self._refresh_resolutions())
        self.playlist_var.trace_add("write", lambda *_args: self._refresh_resolutions())
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)
        self.root.after(100, self._drain_messages)
        self.url_entry.focus_set()

    def _configure_style(self) -> None:
        style = ttk.Style(self.root)
        style.theme_use("clam")
        style.configure("TFrame", background=COLOR_BACKGROUND)
        style.configure("TLabel", background=COLOR_BACKGROUND, foreground=COLOR_WHITE, font=("Segoe UI", 10))
        style.configure(
            "Prompt.TLabel",
            background=COLOR_BACKGROUND,
            foreground=COLOR_WHITE,
            font=("Consolas", 22, "bold"),
        )
        style.configure(
            "Brand.TLabel",
            background=COLOR_BACKGROUND,
            foreground=COLOR_RED,
            font=("Segoe UI Semibold", 22, "italic"),
        )
        style.configure("Subtitle.TLabel", font=("Segoe UI", 10), foreground=COLOR_MUTED)
        style.configure("Section.TLabel", font=("Segoe UI Semibold", 10), foreground=COLOR_WHITE)
        style.configure("Status.TLabel", font=("Segoe UI Semibold", 10), foreground=COLOR_RED)
        style.configure(
            "TEntry",
            fieldbackground=COLOR_SURFACE,
            foreground=COLOR_WHITE,
            insertcolor=COLOR_WHITE,
            bordercolor=COLOR_BORDER,
            lightcolor=COLOR_BORDER,
            darkcolor=COLOR_BORDER,
            padding=5,
        )
        style.map(
            "TEntry",
            fieldbackground=[("disabled", COLOR_SURFACE), ("readonly", COLOR_SURFACE)],
            foreground=[("disabled", COLOR_MUTED)],
            bordercolor=[("focus", COLOR_RED)],
        )
        style.configure(
            "TCombobox",
            fieldbackground=COLOR_SURFACE,
            background=COLOR_SURFACE,
            foreground=COLOR_WHITE,
            arrowcolor=COLOR_WHITE,
            bordercolor=COLOR_BORDER,
            lightcolor=COLOR_BORDER,
            darkcolor=COLOR_BORDER,
            padding=5,
        )
        style.map(
            "TCombobox",
            fieldbackground=[("readonly", COLOR_SURFACE), ("disabled", COLOR_SURFACE)],
            background=[("active", COLOR_SURFACE_HOVER), ("readonly", COLOR_SURFACE)],
            foreground=[("readonly", COLOR_WHITE), ("disabled", COLOR_MUTED)],
            bordercolor=[("focus", COLOR_RED)],
        )
        style.configure(
            "TCheckbutton",
            background=COLOR_BACKGROUND,
            foreground=COLOR_WHITE,
            indicatorbackground=COLOR_SURFACE,
            indicatorforeground=COLOR_RED,
            bordercolor=COLOR_BORDER,
            focuscolor=COLOR_BACKGROUND,
        )
        style.map(
            "TCheckbutton",
            background=[("active", COLOR_BACKGROUND)],
            foreground=[("active", COLOR_WHITE)],
            indicatorbackground=[("selected", COLOR_RED), ("active", COLOR_SURFACE_HOVER)],
        )
        style.configure(
            "Primary.TButton",
            font=("Segoe UI Semibold", 10),
            padding=(18, 9),
            background=COLOR_RED,
            foreground=COLOR_WHITE,
            bordercolor=COLOR_RED,
            lightcolor=COLOR_RED,
            darkcolor=COLOR_RED,
            focuscolor=COLOR_RED,
        )
        style.map(
            "Primary.TButton",
            background=[("active", COLOR_RED_HOVER), ("pressed", COLOR_RED_HOVER), ("disabled", "#661111")],
            foreground=[("disabled", "#B7B7B7")],
        )
        style.configure(
            "Action.TButton",
            font=("Segoe UI", 10),
            padding=(12, 7),
            background=COLOR_SURFACE,
            foreground=COLOR_WHITE,
            bordercolor=COLOR_BORDER,
            lightcolor=COLOR_BORDER,
            darkcolor=COLOR_BORDER,
            focuscolor=COLOR_SURFACE,
        )
        style.map(
            "Action.TButton",
            background=[("active", COLOR_SURFACE_HOVER), ("pressed", COLOR_SURFACE_HOVER)],
            foreground=[("active", COLOR_WHITE), ("disabled", "#777777")],
            bordercolor=[("focus", COLOR_RED)],
        )
        style.configure(
            "Red.Horizontal.TProgressbar",
            troughcolor=COLOR_SURFACE,
            background=COLOR_RED,
            bordercolor=COLOR_BORDER,
            lightcolor=COLOR_RED,
            darkcolor=COLOR_RED,
        )
        style.configure(
            "Details.Vertical.TScrollbar",
            background=COLOR_SURFACE_HOVER,
            troughcolor=COLOR_SURFACE,
            bordercolor=COLOR_BORDER,
            lightcolor=COLOR_SURFACE_HOVER,
            darkcolor=COLOR_SURFACE_HOVER,
            arrowcolor=COLOR_MUTED,
            relief="flat",
            borderwidth=0,
            arrowsize=12,
        )
        style.map(
            "Details.Vertical.TScrollbar",
            background=[("pressed", COLOR_RED), ("active", COLOR_BORDER)],
            arrowcolor=[("pressed", COLOR_WHITE), ("active", COLOR_WHITE)],
        )

    def _build_ui(self) -> None:
        container = ttk.Frame(self.root, padding=(24, 20, 24, 20))
        container.grid(row=0, column=0, sticky="nsew")
        self.root.rowconfigure(0, weight=1)
        self.root.columnconfigure(0, weight=1)
        container.columnconfigure(0, weight=1)
        container.rowconfigure(10, weight=1)

        brand = ttk.Frame(container)
        brand.grid(row=0, column=0, sticky="w")
        ttk.Label(brand, text=">_", style="Prompt.TLabel").pack(side="left")
        ttk.Label(brand, text="yt-dlp", style="Brand.TLabel").pack(side="left", padx=(8, 0))
        ttk.Label(
            container,
            text="Scarica e converti video, audio e playlist con yt-dlp",
            style="Subtitle.TLabel",
        ).grid(row=1, column=0, sticky="w", pady=(0, 18))

        ttk.Label(container, text="Link del video", style="Section.TLabel").grid(row=2, column=0, sticky="w")
        url_row = ttk.Frame(container)
        url_row.grid(row=3, column=0, sticky="ew", pady=(6, 14))
        url_row.columnconfigure(0, weight=1)
        self.url_entry = ttk.Entry(url_row, textvariable=self.url_var, font=("Segoe UI", 10))
        self.url_entry.grid(row=0, column=0, sticky="ew", ipady=5)
        self.url_entry.bind("<Return>", lambda _event: self.start_download())

        ttk.Label(container, text="Salva in", style="Section.TLabel").grid(row=4, column=0, sticky="w")
        folder_row = ttk.Frame(container)
        folder_row.grid(row=5, column=0, sticky="ew", pady=(6, 14))
        folder_row.columnconfigure(0, weight=1)
        ttk.Entry(folder_row, textvariable=self.destination_var, font=("Segoe UI", 10)).grid(
            row=0, column=0, sticky="ew", ipady=5
        )
        ttk.Button(folder_row, text="Sfoglia...", command=self._choose_folder, style="Action.TButton").grid(
            row=0, column=1, padx=(8, 0)
        )

        options = ttk.Frame(container)
        options.grid(row=6, column=0, sticky="ew", pady=(0, 16))
        options.columnconfigure(0, weight=1)
        options.columnconfigure(1, weight=1)
        ttk.Label(options, text="Formato", style="Section.TLabel").grid(row=0, column=0, sticky="w")
        self.format_box = ttk.Combobox(
            options,
            textvariable=self.format_var,
            values=list(FORMAT_OPTIONS),
            state="readonly",
            font=("Segoe UI", 10),
        )
        self.format_box.grid(row=1, column=0, sticky="ew", pady=(6, 0), ipady=4)
        ttk.Label(options, text="Risoluzione", style="Section.TLabel").grid(
            row=0, column=1, sticky="w", padx=(12, 0)
        )
        self.resolution_box = ttk.Combobox(
            options, textvariable=self.resolution_var, values=[BEST_RESOLUTION],
            state="disabled", font=("Segoe UI", 10), width=22,
        )
        self.resolution_box.grid(row=1, column=1, sticky="ew", padx=(12, 0), pady=(6, 0), ipady=4)
        ttk.Label(options, textvariable=self.resolution_hint, style="Subtitle.TLabel").grid(
            row=2, column=0, columnspan=2, sticky="w", pady=(6, 0)
        )
        ttk.Checkbutton(
            options,
            text="Scarica l'intera playlist (se il link ne contiene una)",
            variable=self.playlist_var,
        ).grid(row=3, column=0, columnspan=2, sticky="w", pady=(10, 0))

        action_row = ttk.Frame(container)
        action_row.grid(row=7, column=0, sticky="ew", pady=(0, 16))
        self.download_button = ttk.Button(
            action_row,
            text="Scarica",
            command=self.start_download,
            style="Primary.TButton",
        )
        self.download_button.pack(side="left")
        self.cancel_button = ttk.Button(
            action_row,
            text="Annulla",
            command=self.cancel_download,
            state="disabled",
            style="Action.TButton",
        )
        self.cancel_button.pack(side="left", padx=(8, 0))
        self.update_button = ttk.Button(
            action_row,
            text="Aggiorna yt-dlp",
            command=self.start_update,
            style="Action.TButton",
        )
        self.update_button.pack(side="left", padx=(8, 0))
        ttk.Button(
            action_row,
            text="Apri cartella",
            command=self._open_folder,
            style="Action.TButton",
        ).pack(side="right")

        progress_frame = ttk.Frame(container)
        progress_frame.grid(row=8, column=0, sticky="ew", pady=(0, 12))
        progress_frame.columnconfigure(0, weight=1)
        ttk.Label(progress_frame, textvariable=self.status_var, style="Status.TLabel").grid(
            row=0, column=0, sticky="w"
        )
        ttk.Label(progress_frame, textvariable=self.detail_var, style="Subtitle.TLabel").grid(
            row=0, column=1, sticky="e"
        )
        self.progress = ttk.Progressbar(
            progress_frame,
            variable=self.progress_var,
            maximum=100,
            mode="determinate",
            style="Red.Horizontal.TProgressbar",
        )
        self.progress.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(7, 0))

        ttk.Label(container, text="Dettagli", style="Section.TLabel").grid(row=9, column=0, sticky="w")
        log_frame = ttk.Frame(container)
        log_frame.grid(row=10, column=0, sticky="nsew", pady=(6, 0))
        log_frame.rowconfigure(0, weight=1)
        log_frame.columnconfigure(0, weight=1)
        self.log = tk.Text(
            log_frame,
            height=8,
            wrap="word",
            state="disabled",
            font=("Consolas", 9),
            bg=COLOR_SURFACE,
            fg=COLOR_WHITE,
            insertbackground=COLOR_WHITE,
            selectbackground=COLOR_RED,
            selectforeground=COLOR_WHITE,
            relief="solid",
            borderwidth=1,
            highlightthickness=1,
            highlightbackground=COLOR_BORDER,
            highlightcolor=COLOR_RED,
            padx=8,
            pady=8,
        )
        self.log.grid(row=0, column=0, sticky="nsew")
        self.log_scrollbar = ttk.Scrollbar(
            log_frame, orient="vertical", command=self.log.yview,
            style="Details.Vertical.TScrollbar",
        )
        self.log_scrollbar.grid(row=0, column=1, sticky="ns")
        self.log_scrollbar.grid_remove()
        self.log.configure(yscrollcommand=self._update_log_scrollbar)

    def _update_log_scrollbar(self, first: str, last: str) -> None:
        self.log_scrollbar.set(first, last)
        if float(first) <= 0 and float(last) >= 1:
            self.log_scrollbar.grid_remove()
        else:
            self.log_scrollbar.grid()

    def _url_changed(self, *_args: str) -> None:
        self.metadata_revision += 1
        self.metadata_url = None
        self.metadata_info = {}
        self.metadata_error = False
        self.resolution_var.set(BEST_RESOLUTION)
        if self.metadata_after is not None:
            self.root.after_cancel(self.metadata_after)
        self.metadata_after = None
        self._refresh_resolutions()
        if is_valid_url(self.url_var.get()):
            self.metadata_after = self.root.after(700, self._start_metadata)

    def _refresh_resolutions(self) -> None:
        is_video = "-f" in FORMAT_OPTIONS[self.format_var.get()]
        heights = available_resolutions(self.metadata_info, self.format_var.get()) if is_video else []
        choices = [BEST_RESOLUTION] + [f"{height}p" for height in heights]
        if self.resolution_var.get() not in choices:
            self.resolution_var.set(BEST_RESOLUTION)
        self.resolution_box.configure(
            values=choices,
            state="readonly" if is_video and heights and not self.active_operation else "disabled",
        )
        if not is_video:
            hint = "La risoluzione non si applica ai download solo audio."
        elif not is_valid_url(self.url_var.get()):
            hint = "Incolla un link per leggere le risoluzioni disponibili."
        elif self.metadata_url != self.url_var.get().strip():
            hint = "Lettura delle risoluzioni disponibili..."
        elif self.metadata_error:
            hint = "Risoluzioni non rilevate; puoi scaricare alla qualità massima."
        elif not heights:
            hint = "Nessuna risoluzione video rilevata per questo formato."
        elif self.playlist_var.get():
            hint = "Per la playlist la risoluzione scelta è un limite massimo."
        else:
            hint = "Risoluzioni disponibili per il video e il formato scelto."
        self.resolution_hint.set(hint)

    def _start_metadata(self) -> None:
        self.metadata_after = None
        url = self.url_var.get().strip()
        if self.metadata_loading or not is_valid_url(url):
            return
        executable = locate_yt_dlp()
        if not executable:
            self.metadata_url = url
            self.metadata_error = True
            self._refresh_resolutions()
            return
        self.metadata_loading = True
        threading.Thread(
            target=self._metadata_worker,
            args=(executable, url, self.metadata_revision), daemon=True,
        ).start()

    def _metadata_worker(self, executable: str, url: str, revision: int) -> None:
        try:
            result = subprocess.run(
                build_metadata_command(executable, url), stdout=subprocess.PIPE,
                stderr=subprocess.PIPE, text=True, encoding="utf-8", errors="replace",
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
                timeout=60, check=False,
            )
            if result.returncode:
                raise RuntimeError(result.stderr.strip() or "Impossibile leggere le risoluzioni.")
            info = json.loads(result.stdout)
            if not isinstance(info, dict):
                raise ValueError("Metadati video non validi.")
            if info.get("entries") is not None:
                info = next((entry for entry in info["entries"] if entry), {})
            self.messages.put(("metadata", revision, url, info, ""))
        except (OSError, subprocess.SubprocessError, ValueError, RuntimeError) as exc:
            self.messages.put(("metadata", revision, url, {}, str(exc)))

    def _choose_folder(self) -> None:
        selected = filedialog.askdirectory(
            title="Scegli la cartella dei download",
            initialdir=self.destination_var.get() or str(Path.home()),
        )
        if selected:
            self.destination_var.set(selected)

    def _open_folder(self) -> None:
        folder = Path(self.destination_var.get().strip())
        try:
            folder.mkdir(parents=True, exist_ok=True)
            os.startfile(str(folder))  # type: ignore[attr-defined]
        except OSError as exc:
            messagebox.showerror(APP_NAME, f"Impossibile aprire la cartella:\n{exc}")

    def _append_log(self, text: str) -> None:
        self.log.configure(state="normal")
        self.log.insert("end", text.rstrip() + "\n")
        self.log.see("end")
        self.log.configure(state="disabled")

    def _set_running(self, running: bool, cancellable: bool = True) -> None:
        self.download_button.configure(state="disabled" if running else "normal")
        self.update_button.configure(state="disabled" if running else "normal")
        self.cancel_button.configure(state="normal" if running and cancellable else "disabled")
        self.url_entry.configure(state="disabled" if running else "normal")
        self.format_box.configure(state="disabled" if running else "readonly")
        self._refresh_resolutions()

    def start_download(self) -> None:
        if self.active_operation:
            return

        url = self.url_var.get().strip()
        if not is_valid_url(url):
            messagebox.showwarning(APP_NAME, "Inserisci un link valido che inizi con http:// o https://.")
            self.url_entry.focus_set()
            return

        executable = locate_yt_dlp()
        if not executable:
            messagebox.showerror(
                APP_NAME,
                "yt-dlp non è stato trovato. Avvia INSTALL.bat e riprova.",
            )
            return

        if "-f" in FORMAT_OPTIONS[self.format_var.get()] and self.metadata_url != url:
            if self.metadata_after is not None:
                self.root.after_cancel(self.metadata_after)
                self.metadata_after = None
            self._start_metadata()
            self.resolution_hint.set("Attendi la lettura, poi scegli la risoluzione e premi Scarica.")
            return
        try:
            yt_dlp_version = probe_yt_dlp(executable)
        except (OSError, subprocess.SubprocessError, RuntimeError) as exc:
            messagebox.showerror(APP_NAME, f"Impossibile verificare yt-dlp:\n{exc}")
            return

        destination = Path(self.destination_var.get().strip())
        try:
            destination.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            messagebox.showerror(APP_NAME, f"La cartella scelta non è utilizzabile:\n{exc}")
            return

        command = build_command(
            executable,
            url,
            str(destination),
            self.format_var.get(),
            self.playlist_var.get(),
            None if self.resolution_var.get() == BEST_RESOLUTION else int(self.resolution_var.get()[:-1]),
        )
        self.cancel_requested = False
        self.downloaded_files = []
        self.active_destination = destination
        self.destination_snapshot = self._snapshot_destination(destination)
        self.progress_var.set(0)
        self.status_var.set("Preparazione...")
        self.detail_var.set("")
        self.log.configure(state="normal")
        self.log.delete("1.0", "end")
        self.log.configure(state="disabled")
        self._append_log(f"Motore: yt-dlp {yt_dlp_version}")
        self._append_log(f"Destinazione: {destination}")
        if "-f" in FORMAT_OPTIONS[self.format_var.get()]:
            self._append_log(f"Risoluzione: {self.resolution_var.get()}")
        self.active_operation = "download"
        self._set_running(True)

        threading.Thread(target=self._download_worker, args=(command,), daemon=True).start()

    def _download_worker(self, command: list[str]) -> None:
        creation_flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
        try:
            self.process = subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding=locale.getpreferredencoding(False),
                errors="replace",
                creationflags=creation_flags,
            )
            self.messages.put(("status", "Download in corso...", "Connessione al sito"))
            assert self.process.stdout is not None
            for raw_line in self.process.stdout:
                line = raw_line.rstrip("\r\n")
                progress_match = re.match(r"PROGRESS:\s*([\d.,]+)%\|(.*?)\|(.*)", line)
                if progress_match:
                    percentage = float(progress_match.group(1).replace(",", "."))
                    speed = progress_match.group(2).strip()
                    eta = progress_match.group(3).strip()
                    detail = speed
                    if eta and eta.upper() != "NA":
                        detail += f"  •  {eta} rimanenti"
                    self.messages.put(("progress", percentage, detail))
                elif line.startswith("FILE:"):
                    downloaded_file = line[5:].strip()
                    self.downloaded_files.append(downloaded_file)
                    self.messages.put(("file", downloaded_file))
                elif line:
                    self.messages.put(("log", line))

            return_code = self.process.wait()
            self.messages.put(("done", return_code, self.cancel_requested))
        except Exception as exc:  # Keeps GUI errors visible instead of losing them in pythonw.
            self.messages.put(("error", "download", str(exc)))
        finally:
            self.process = None

    def start_update(self) -> None:
        if self.active_operation:
            return

        executable = locate_yt_dlp()
        if not executable:
            messagebox.showerror(
                APP_NAME,
                "yt-dlp non è stato trovato. Avvia INSTALL.bat e riprova.",
            )
            return
        try:
            current_version = probe_yt_dlp(executable)
        except (OSError, subprocess.SubprocessError, RuntimeError) as exc:
            messagebox.showerror(APP_NAME, f"Impossibile verificare yt-dlp:\n{exc}")
            return

        self.log.configure(state="normal")
        self.log.delete("1.0", "end")
        self.log.configure(state="disabled")
        self.status_var.set("Controllo aggiornamenti...")
        self.detail_var.set(f"Versione installata: {current_version}")
        self.progress_var.set(0)
        self.progress.configure(mode="indeterminate")
        self.progress.start(12)
        self._append_log(f"Versione installata: yt-dlp {current_version}")
        self._append_log("Controllo della release stabile ufficiale...")
        self.active_operation = "update"
        self._set_running(True, cancellable=False)

        threading.Thread(
            target=self._update_worker,
            args=(executable, current_version),
            daemon=True,
        ).start()

    def _update_worker(self, executable: str, previous_version: str) -> None:
        creation_flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
        try:
            self.process = subprocess.Popen(
                build_update_command(),
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding=locale.getpreferredencoding(False),
                errors="replace",
                creationflags=creation_flags,
            )
            assert self.process.stdout is not None
            for raw_line in self.process.stdout:
                line = raw_line.rstrip("\r\n")
                if line:
                    self.messages.put(("log", line))

            return_code = self.process.wait()
            updated_version = previous_version
            if return_code == 0:
                updated_version = probe_yt_dlp(executable)
            self.messages.put(("update_done", return_code, previous_version, updated_version))
        except Exception as exc:  # Keeps GUI errors visible instead of losing them in pythonw.
            self.messages.put(("error", "update", str(exc)))
        finally:
            self.process = None

    def _drain_messages(self) -> None:
        try:
            while True:
                message = self.messages.get_nowait()
                kind = message[0]
                if kind == "metadata":
                    self.metadata_loading = False
                    if message[1] != self.metadata_revision:
                        if self.metadata_after is None:
                            self._start_metadata()
                        continue
                    self.metadata_url = message[2]
                    self.metadata_info = message[3]
                    self.metadata_error = bool(message[4])
                    if message[4]:
                        self._append_log(f"Lettura risoluzioni: {message[4]}")
                    self._refresh_resolutions()
                elif kind == "status":
                    self.status_var.set(message[1])
                    self.detail_var.set(message[2])
                elif kind == "progress":
                    self.progress_var.set(message[1])
                    self.status_var.set(f"Download {message[1]:.0f}%")
                    self.detail_var.set(message[2])
                elif kind == "file":
                    self._append_log(f"Salvato: {message[1]}")
                elif kind == "log":
                    self._append_log(message[1])
                elif kind == "done":
                    self._handle_done(message[1], message[2])
                elif kind == "update_done":
                    self._handle_update_done(message[1], message[2], message[3])
                elif kind == "error":
                    operation = message[1]
                    self.progress.stop()
                    self.progress.configure(mode="determinate")
                    self.progress_var.set(0)
                    self.active_operation = None
                    self._set_running(False)
                    self.status_var.set("Errore")
                    self.detail_var.set("")
                    self._append_log(message[2])
                    activity = "l'aggiornamento" if operation == "update" else "il download"
                    messagebox.showerror(APP_NAME, f"Impossibile completare {activity}:\n{message[2]}")
        except queue.Empty:
            pass
        self.root.after(100, self._drain_messages)

    def _handle_done(self, return_code: int, was_cancelled: bool) -> None:
        self.active_operation = None
        self._set_running(False)
        if was_cancelled:
            self.status_var.set("Download annullato")
            self.detail_var.set("")
            self._append_log("Operazione annullata.")
        elif return_code == 0:
            verified_files: list[Path] = []
            for raw_path in self.downloaded_files:
                try:
                    candidate = Path(raw_path)
                    if candidate.is_file():
                        verified_files.append(candidate)
                except OSError:
                    continue

            if not verified_files and self.active_destination:
                verified_files = self._find_changed_files(
                    self.active_destination,
                    self.destination_snapshot,
                )

            if verified_files:
                self.progress_var.set(100)
                self.status_var.set("Completato")
                count = len(verified_files)
                self.detail_var.set("File salvato" if count == 1 else f"{count} file salvati")
                for downloaded_file in verified_files:
                    self._append_log(f"Download verificato: {downloaded_file}")
                self.root.bell()
            else:
                self.status_var.set("Nessun file creato")
                self.detail_var.set("")
                self._append_log("yt-dlp è terminato senza creare un file verificabile.")
                messagebox.showerror(
                    APP_NAME,
                    "yt-dlp è terminato, ma non è stato trovato alcun file scaricato. "
                    "Controlla i dettagli nella finestra.",
                )
        else:
            self.status_var.set("Download non riuscito")
            self.detail_var.set(f"Codice errore {return_code}")
            messagebox.showerror(
                APP_NAME,
                "Il download non è riuscito. Controlla i dettagli nella finestra.",
            )

    def _handle_update_done(
        self,
        return_code: int,
        previous_version: str,
        updated_version: str,
    ) -> None:
        self.progress.stop()
        self.progress.configure(mode="determinate")
        self.active_operation = None
        self._set_running(False)

        if return_code != 0:
            self.progress_var.set(0)
            self.status_var.set("Aggiornamento non riuscito")
            self.detail_var.set(f"Codice errore {return_code}")
            messagebox.showerror(
                APP_NAME,
                "Non è stato possibile aggiornare yt-dlp. Controlla i dettagli nella finestra.",
            )
            return

        self.progress_var.set(100)
        if updated_version == previous_version:
            self.status_var.set("yt-dlp è già aggiornato")
            self.detail_var.set(f"Versione {updated_version}")
            self._append_log(f"Nessun aggiornamento necessario: yt-dlp {updated_version}.")
            messagebox.showinfo(APP_NAME, f"yt-dlp è già aggiornato alla versione {updated_version}.")
        else:
            self.status_var.set("Aggiornamento completato")
            self.detail_var.set(f"Versione {updated_version}")
            self._append_log(f"Aggiornamento verificato: {previous_version} → {updated_version}.")
            self.root.bell()
            messagebox.showinfo(
                APP_NAME,
                f"yt-dlp è stato aggiornato dalla versione {previous_version} alla {updated_version}.",
            )

    @staticmethod
    def _snapshot_destination(folder: Path) -> dict[str, tuple[int, int]]:
        snapshot: dict[str, tuple[int, int]] = {}
        try:
            for item in folder.iterdir():
                if not item.is_file():
                    continue
                stat = item.stat()
                key = os.path.normcase(str(item.resolve()))
                snapshot[key] = (stat.st_size, stat.st_mtime_ns)
        except OSError:
            pass
        return snapshot

    @staticmethod
    def _find_changed_files(
        folder: Path,
        before: dict[str, tuple[int, int]],
    ) -> list[Path]:
        changed: list[Path] = []
        temporary_suffixes = {".part", ".ytdl", ".temp"}
        try:
            for item in folder.iterdir():
                if not item.is_file() or item.suffix.lower() in temporary_suffixes:
                    continue
                stat = item.stat()
                key = os.path.normcase(str(item.resolve()))
                signature = (stat.st_size, stat.st_mtime_ns)
                if key not in before or before[key] != signature:
                    changed.append(item)
        except OSError:
            return []
        return sorted(changed, key=lambda item: item.stat().st_mtime_ns)

    def cancel_download(self) -> None:
        process = self.process
        if self.active_operation != "download" or not process or process.poll() is not None:
            return
        self.cancel_requested = True
        self.status_var.set("Annullamento...")
        self.detail_var.set("")
        self.cancel_button.configure(state="disabled")

        def stop_process_tree() -> None:
            subprocess.run(
                ["taskkill", "/PID", str(process.pid), "/T", "/F"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
                check=False,
            )

        threading.Thread(target=stop_process_tree, daemon=True).start()

    def _on_close(self) -> None:
        if self.process and self.process.poll() is None:
            activity = "un aggiornamento" if self.active_operation == "update" else "un download"
            if not messagebox.askyesno(APP_NAME, f"È in corso {activity}. Interromperlo e chiudere?"):
                return
            process = self.process
            subprocess.run(
                ["taskkill", "/PID", str(process.pid), "/T", "/F"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
                check=False,
            )
        self.root.destroy()


def main() -> None:
    root = tk.Tk()
    YtDlpApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
