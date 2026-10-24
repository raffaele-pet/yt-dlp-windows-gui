import copy
import json
import subprocess
import tkinter as tk
import unittest
from tkinter import ttk
from unittest.mock import patch

import app


MP4, VIDEO, MP3, M4A = app.FORMAT_OPTIONS
FORMATS = [
    {"format_id": "360", "height": 360, "vcodec": "avc1.4d", "acodec": "aac", "ext": "mp4"},
    {"format_id": "720", "height": 720, "vcodec": "avc1.4d", "acodec": "none", "ext": "mp4"},
    {"format_id": "720-60", "height": 720, "vcodec": "avc1.4d", "acodec": "none", "ext": "mp4"},
    {"format_id": "1080", "height": 1080, "vcodec": "avc1.64", "acodec": "none", "ext": "mp4"},
    {"format_id": "audio", "vcodec": "none", "acodec": "aac", "ext": "m4a"},
    {"format_id": "1440", "height": 1440, "vcodec": "av01.0.12", "acodec": "none", "ext": "mp4"},
    {"format_id": "2160", "height": 2160, "vcodec": "vp9", "acodec": "none", "ext": "webm"},
]


class ResolutionTests(unittest.TestCase):
    def test_only_downloadable_heights_sorted_and_deduplicated(self):
        info = {"formats": FORMATS + [
            {"height": 1440, "vcodec": "avc1.64", "ext": "mkv"},
            {"height": 4320, "vcodec": "avc1.64", "ext": "mp4", "has_drm": True},
            {"height": None, "vcodec": "avc1.64", "ext": "mp4"},
            {"height": 8640, "vcodec": "none", "ext": "mhtml"},
            {"height": 4320, "vcodec": "images", "ext": "mhtml"},
        ]}
        self.assertEqual(app.available_resolutions(info, MP4), [2160, 1440, 1080, 720, 360])
        self.assertEqual(app.available_resolutions(info, VIDEO), [2160, 1440, 1080, 720, 360])
        self.assertEqual(app.available_resolutions(info, MP3), [])
        self.assertEqual(app.available_resolutions({}, MP4), [])

    def test_default_and_audio_arguments_stay_unchanged(self):
        for name, options in app.FORMAT_OPTIONS.items():
            command = app.build_command("yt-dlp", "https://example.com/video", "downloads", name, False)
            self.assertEqual(command[-len(options)-2:-2], options)
        for name in (MP3, M4A):
            self.assertNotIn("height", " ".join(app.build_command("yt-dlp", "https://example.com", ".", name, False, 720)))

    def test_real_ytdlp_selector_respects_resolution_and_preserves_audio(self):
        try:
            from yt_dlp import YoutubeDL
        except ImportError:
            self.skipTest("Install requirements.txt to test yt-dlp's format selector")
        formats = copy.deepcopy(FORMATS)
        for item in formats:
            item["url"] = "https://example.com/" + item["format_id"]
            item["protocol"] = "https"
        with YoutubeDL({"quiet": True}) as ydl:
            for name in (MP4, VIDEO):
                for playlist, height, expected in (
                    (False, 720, 720), (False, 360, 360), (True, 900, 720),
                    (False, 1440, 1440), (False, 2160, 2160), (True, 2000, 1440),
                    (False, None, 2160),
                ):
                    command = app.build_command("yt-dlp", "https://example.com", ".", name, playlist, height)
                    selector = command[command.index("-f") + 1]
                    self.assertIn("+ba", selector)
                    selected = list(ydl.build_format_selector(selector)({"formats": formats, "incomplete_formats": False}))
                    self.assertEqual(selected[0]["height"], expected)
                    self.assertNotEqual(selected[0]["acodec"], "none")
                command = app.build_command("yt-dlp", "https://example.com", ".", name, False, 480)
                selected = list(ydl.build_format_selector(command[command.index("-f") + 1])({"formats": formats, "incomplete_formats": False}))
                self.assertEqual(selected, [])

    def test_mp4_remuxes_other_containers_without_forcing_h264(self):
        command = app.build_command("yt-dlp", "https://example.com", ".", MP4, False, 2160)
        self.assertEqual(command[command.index("--merge-output-format") + 1], "mp4")
        self.assertEqual(command[command.index("--remux-video") + 1], "mp4")
        self.assertNotIn("vcodec", command[command.index("-f") + 1])


class InterfaceTests(unittest.TestCase):
    def setUp(self):
        self.root = tk.Tk()
        self.addCleanup(self.close_root)
        self.gui = app.YtDlpApp(self.root)
        self.root.update()

    def close_root(self):
        for timer in self.root.tk.call("after", "info"):
            self.root.after_cancel(timer)
        self.root.destroy()

    def set_video(self):
        self.gui.url_var.set("https://example.com/video")
        self.root.after_cancel(self.gui.metadata_after)
        self.gui.metadata_after = None
        self.gui.metadata_url = self.gui.url_var.get()
        self.gui.metadata_info = {"formats": FORMATS}
        self.gui._refresh_resolutions()

    def test_scrollbar_hides_shows_clears_and_adapts_to_resize(self):
        self.assertFalse(self.gui.log_scrollbar.winfo_ismapped())
        for number in range(12):
            self.gui._append_log(f"Dettaglio {number}")
        self.root.geometry("680x660")
        self.root.update()
        self.assertGreater(self.gui.log.winfo_height(), 60)
        self.assertTrue(self.gui.log_scrollbar.winfo_ismapped())
        self.root.geometry("900x1000")
        self.root.update()
        self.assertFalse(self.gui.log_scrollbar.winfo_ismapped())
        for number in range(100):
            self.gui._append_log(str(number))
        self.root.update()
        self.assertTrue(self.gui.log_scrollbar.winfo_ismapped())
        self.gui.log.configure(state="normal")
        self.gui.log.delete("1.0", "end")
        self.gui.log.configure(state="disabled")
        self.root.update()
        self.assertFalse(self.gui.log_scrollbar.winfo_ismapped())
        style = ttk.Style(self.root)
        self.assertEqual(style.lookup("Details.Vertical.TScrollbar", "troughcolor"), app.COLOR_SURFACE)

    def test_native_paste_and_available_choices(self):
        self.root.clipboard_clear()
        self.root.clipboard_append("https://example.com/video")
        self.gui.url_entry.event_generate("<<Paste>>")
        self.assertEqual(self.gui.url_var.get(), "https://example.com/video")
        self.set_video()
        self.assertEqual(self.gui.resolution_box.cget("values"), (app.BEST_RESOLUTION, "2160p", "1440p", "1080p", "720p", "360p"))
        self.assertEqual(str(self.gui.resolution_box.cget("state")), "readonly")

    def test_audio_busy_and_link_changes_reset_controls(self):
        self.set_video()
        self.gui.resolution_var.set("720p")
        self.gui.active_operation = "download"
        self.gui._set_running(True)
        self.assertEqual(str(self.gui.resolution_box.cget("state")), "disabled")
        self.gui.active_operation = None
        self.gui._set_running(False)
        self.assertEqual(str(self.gui.resolution_box.cget("state")), "readonly")
        self.gui.format_var.set(MP3)
        self.assertEqual(self.gui.resolution_var.get(), app.BEST_RESOLUTION)
        self.assertEqual(str(self.gui.resolution_box.cget("state")), "disabled")
        self.gui.format_var.set(MP4)
        self.gui.resolution_var.set("720p")
        self.gui.url_var.set("https://example.com/other")
        self.assertEqual(self.gui.resolution_var.get(), app.BEST_RESOLUTION)
        self.assertEqual(self.gui.metadata_info, {})

    def test_stale_metadata_is_ignored_and_latest_link_is_queried(self):
        self.set_video()
        old_revision = self.gui.metadata_revision
        self.gui.url_var.set("https://example.com/new")
        self.root.after_cancel(self.gui.metadata_after)
        self.gui.metadata_after = None
        self.gui.metadata_loading = True
        self.gui.messages.put(("metadata", old_revision, "https://example.com/video", {"formats": FORMATS}, ""))
        with patch.object(self.gui, "_start_metadata") as start:
            self.gui._drain_messages()
        start.assert_called_once()
        self.assertIsNone(self.gui.metadata_url)
        self.assertFalse(self.gui.metadata_loading)

    def test_download_waits_for_quality_detection(self):
        self.gui.url_var.set("https://example.com/video")
        with patch.object(self.gui, "_start_metadata") as start, patch("app.locate_yt_dlp", return_value="yt-dlp"), patch("app.probe_yt_dlp") as probe:
            self.gui.start_download()
        start.assert_called_once()
        probe.assert_not_called()
        self.assertIsNone(self.gui.active_operation)

    def test_selected_resolution_reaches_download_worker(self):
        self.set_video()
        self.gui.resolution_var.set("720p")
        with patch("app.locate_yt_dlp", return_value="yt-dlp"), patch("app.probe_yt_dlp", return_value="2026.10.21"), patch("app.threading.Thread") as thread, patch.object(self.gui, "_snapshot_destination", return_value={}), patch("app.Path.mkdir"):
            self.gui.start_download()
        command = thread.call_args.kwargs["args"][0]
        self.assertIn("[height=720]", command[command.index("-f") + 1])

    def test_metadata_failure_keeps_default_download_available(self):
        self.set_video()
        self.gui.metadata_loading = True
        self.gui.messages.put(("metadata", self.gui.metadata_revision, self.gui.url_var.get(), {}, "Sito non raggiungibile"))
        self.gui._drain_messages()
        self.assertTrue(self.gui.metadata_error)
        self.assertEqual(self.gui.resolution_var.get(), app.BEST_RESOLUTION)
        self.assertIn("qualità massima", self.gui.resolution_hint.get())

    def test_metadata_worker_parses_json_and_handles_timeout(self):
        result = subprocess.CompletedProcess([], 0, json.dumps({"formats": FORMATS}), "")
        with patch("app.subprocess.run", return_value=result) as run:
            self.gui._metadata_worker("yt-dlp", "https://example.com/video", 1)
        self.assertEqual(self.gui.messages.get_nowait()[3], {"formats": FORMATS})
        self.assertIn("--skip-download", run.call_args.args[0])
        self.assertEqual(run.call_args.kwargs["encoding"], "utf-8")
        with patch("app.subprocess.run", side_effect=subprocess.TimeoutExpired("yt-dlp", 60)):
            self.gui._metadata_worker("yt-dlp", "https://example.com/video", 2)
        self.assertTrue(self.gui.messages.get_nowait()[4])


if __name__ == "__main__":
    unittest.main()
