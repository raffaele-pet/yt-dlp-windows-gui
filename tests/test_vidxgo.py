import base64
import functools
import http.server
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import threading
import unittest
from unittest.mock import Mock, patch
from urllib.parse import parse_qs, urlsplit

from yt_dlp import YoutubeDL
from yt_dlp.utils import ExtractorError, unsmuggle_url

import app
from plugins.vidxgo.yt_dlp_plugins.extractor.vidxgo import (
    VidxgoIE, _find_hls_url, _inherit_query,
)


PLAYER = "https://v.vidxgo.co/4644488/1/5?se=0&info=0"
PAGE = "https://streaming-community.biz/titles/25182-dragon-ball-super-streaming/watching?s=1&e=5"
MANIFEST = """#EXTM3U
#EXT-X-STREAM-INF:BANDWIDTH=800000,RESOLUTION=1280x720,CODECS="avc1.4d401f,mp4a.40.2"
720.m3u8
#EXT-X-STREAM-INF:BANDWIDTH=2000000,RESOLUTION=1920x1080,CODECS="avc1.640028,mp4a.40.2"
1080.m3u8
"""


def obfuscate(source, key="fixture-key"):
    payload = base64.b64encode(bytes(
        byte ^ ord(key[index % len(key)]) for index, byte in enumerate(source.encode())
    )).decode()
    return f"<script>var k='{key}',d=atob('{payload}');</script>"


class VidxgoTests(unittest.TestCase):
    def setUp(self):
        self.downloader = YoutubeDL({"quiet": True})
        self.addCleanup(self.downloader.close)
        self.extractor = VidxgoIE(self.downloader)

    def test_decodes_all_script_blocks_and_prefers_current_source(self):
        source = r'''var other="https://cdn.example/advert.m3u8";window.currentSrc="https:\/\/cdn.example\/master.m3u8?token=abc\u0026expire=5";'''
        html = "<script src='unrelated.js'></script>" + obfuscate('var advert="https://cdn.example/advert.m3u8";') + obfuscate(source)
        self.assertEqual(_find_hls_url(html), "https://cdn.example/master.m3u8?token=abc&expire=5")

    def test_plain_script_and_malformed_payload(self):
        self.assertEqual(_find_hls_url('<script>currentSrc="https://cdn.example/master.m3u8";</script>'), "https://cdn.example/master.m3u8")
        self.assertIsNone(_find_hls_url("<script>var k='',d=atob('YQ==');</script>"))
        self.assertIsNone(_find_hls_url("<script>var k='a',d=atob('a');</script>"))

    def test_embed_keeps_parent_and_episode_and_deduplicates(self):
        iframe = '<iframe src="https://v.vidxgo.co/4644488/1/5?se=0&amp;info=0"></iframe>'
        results = list(VidxgoIE._extract_from_webpage(PAGE, iframe * 2))
        self.assertEqual(len(results), 1)
        url, context = unsmuggle_url(results[0]["url"], {})
        self.assertEqual(url, PLAYER)
        self.assertEqual(context["referer"], PAGE)
        self.assertTrue(VidxgoIE.suitable(url))
        self.assertFalse(VidxgoIE.suitable("https://vidxgo.co.example.org/123"))

    def test_signed_query_preserves_variant_values_and_stays_on_cdn(self):
        source = "https://cdn.example/master.m3u8?token=old&expire=5&empty="
        variant = _inherit_query("https://cdn.example/720.m3u8?token=new", source)
        self.assertEqual(parse_qs(urlsplit(variant).query, keep_blank_values=True), {"token": ["new"], "expire": ["5"], "empty": [""]})
        for target in ("https://other.example/sub.vtt", "http://cdn.example/720.m3u8"):
            self.assertEqual(_inherit_query(target, source), target)

    def test_missing_transport_reports_installation_instructions(self):
        with patch.object(self.downloader, "_parse_impersonate_targets", return_value=(None, [])):
            with self.assertRaisesRegex(ExtractorError, "Aggiorna yt-dlp"):
                self.extractor._configure_transport()

    def test_maintenance_is_reported_without_attempting_media_download(self):
        with patch.object(self.extractor, "_configure_transport"), patch.object(
            self.extractor, "_download_webpage_handle",
            return_value=("<p>Stiamo lavorando, torniamo presto.</p>", Mock(status=403)),
        ), patch.object(self.extractor, "_download_json") as api:
            with self.assertRaisesRegex(ExtractorError, "manutenzione"):
                self.extractor._real_extract(PLAYER)
        api.assert_not_called()

    def test_api_and_obfuscated_page_share_hls_and_episode_metadata(self):
        stream = "https://cdn.example/master.m3u8?token=session"
        for api_available in (True, False):
            page = "<title>Dragon Ball Super</title>" + obfuscate(f'currentSrc="{stream}";')
            with patch.object(self.extractor, "_configure_transport"), patch.object(
                self.extractor, "_download_webpage_handle", side_effect=[
                    (page, Mock(status=200, url=PLAYER)),
                    (MANIFEST, Mock(status=200, url=stream)),
                ],
            ), patch.object(self.extractor, "_download_json", return_value={"url": stream} if api_available else None) as api:
                info = self.extractor._real_extract(PLAYER)
            self.assertEqual(api.call_args.args[0], "https://v.vidxgo.co/t/4644488/1/5")
            self.assertEqual(info["id"], "4644488-s01e05")
            self.assertEqual(info["episode_number"], 5)
            self.assertEqual(info["season_number"], 1)
            self.assertIn("S01E05", info["title"])
            self.assertEqual(app.available_resolutions(info, next(iter(app.FORMAT_OPTIONS))), [1080, 720])
            self.assertTrue(all(item["http_headers"]["Origin"] == "https://v.vidxgo.co" for item in info["formats"]))
            self.assertTrue(all(item["extra_param_to_segment_url"] == "token=session" for item in info["formats"]))

    def test_project_plugin_is_enabled_for_metadata_and_download(self):
        commands = [
            app.build_metadata_command("yt-dlp", PAGE),
            app.build_command("yt-dlp", PAGE, ".", next(iter(app.FORMAT_OPTIONS)), False),
        ]
        for command in commands:
            self.assertEqual(command[command.index("--plugin-dirs") + 1], str(app.PLUGIN_DIR))

    def test_ytdlp_discovers_the_bundled_extractor(self):
        script = (
            "import sys,yt_dlp; "
            "from yt_dlp.globals import plugin_dirs,plugin_ies; "
            "from yt_dlp.plugins import load_all_plugins; "
            "plugin_dirs.value=[sys.argv[1]]; load_all_plugins(); "
            "print(','.join(plugin_ies.value))"
        )
        result = subprocess.run([
            sys.executable, "-c", script, str(app.PLUGIN_DIR),
        ], check=True, capture_output=True, text=True, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        self.assertIn("VidxgoIE", result.stdout.strip().split(","))


class FixtureVidxgoIE(VidxgoIE):
    """Exercise the production extractor against a local HTTP fixture only."""

    _VALID_URL = r"http://127\.0\.0\.1:\d+/(?P<id>\d+)/(?P<season>\d+)/(?P<episode>\d+)(?:[?#]|$)"

    def _configure_transport(self):
        pass


class LocalHlsTests(unittest.TestCase):
    @unittest.skipUnless(shutil.which("ffmpeg") and shutil.which("ffprobe"), "FFmpeg is required for the HLS download test")
    def test_http_player_to_selected_mp4_with_signed_segments(self):
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary)
            for height in (720, 1080):
                subprocess.run([
                    shutil.which("ffmpeg"), "-hide_banner", "-loglevel", "error",
                    "-f", "lavfi", "-i", f"color=s={height * 16 // 9}x{height}:r=5",
                    "-f", "lavfi", "-i", "sine=frequency=440", "-t", "0.2",
                    "-c:v", "libx264", "-c:a", "aac", "-f", "mpegts", str(folder / f"{height}.ts"),
                ], check=True, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))

            requests = []

            class Handler(http.server.SimpleHTTPRequestHandler):
                def do_GET(self):
                    path = urlsplit(self.path)
                    origin = f"http://127.0.0.1:{self.server.server_port}"
                    if path.path.startswith(("/master", "/720", "/1080")):
                        requests.append((path.path, parse_qs(path.query), self.headers.get("Referer")))
                        if parse_qs(path.query).get("token") != ["fixture"] or self.headers.get("Referer") != origin + "/":
                            self.send_error(403)
                            return
                    if path.path == "/123/1/5":
                        body = "<title>Episode fixture</title>"
                    elif path.path == "/t/123/1/5":
                        body = json.dumps({"url": origin + "/master.m3u8?token=fixture"})
                    elif path.path == "/master.m3u8":
                        body = MANIFEST
                    elif path.path in ("/720.m3u8", "/1080.m3u8"):
                        height = path.path.split(".")[0].lstrip("/")
                        body = f"#EXTM3U\n#EXT-X-TARGETDURATION:1\n#EXTINF:0.2,\n{height}.ts\n#EXT-X-ENDLIST\n"
                    else:
                        return super().do_GET()
                    self.send_response(200)
                    self.end_headers()
                    self.wfile.write(body.encode())

                def log_message(self, *args):
                    pass

            server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), functools.partial(Handler, directory=str(folder)))
            threading.Thread(target=server.serve_forever, daemon=True).start()
            try:
                with YoutubeDL({
                    "quiet": True, "noprogress": True, "format": "b[height=720]",
                    "outtmpl": str(folder / "download.%(ext)s"),
                    "postprocessors": [{"key": "FFmpegVideoRemuxer", "preferedformat": "mp4"}],
                }) as downloader:
                    downloader.add_info_extractor(FixtureVidxgoIE())
                    info = downloader.extract_info(
                        f"http://127.0.0.1:{server.server_port}/123/1/5",
                        ie_key=FixtureVidxgoIE.ie_key(),
                    )
                self.assertEqual(info["height"], 720)
                probe = subprocess.run([
                    shutil.which("ffprobe"), "-v", "error", "-show_streams", "-of", "json", str(folder / "download.mp4"),
                ], check=True, capture_output=True, text=True, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
                streams = json.loads(probe.stdout)["streams"]
                self.assertEqual(next(item for item in streams if item["codec_type"] == "video")["height"], 720)
                self.assertTrue(any(item["codec_type"] == "audio" for item in streams))
                self.assertTrue(any(path == "/720.ts" for path, _, _ in requests))
                self.assertFalse(any(path == "/1080.ts" for path, _, _ in requests))
            finally:
                server.shutdown()
                server.server_close()


if __name__ == "__main__":
    unittest.main()
