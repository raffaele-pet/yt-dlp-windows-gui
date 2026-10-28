"""VidXgo embeds, exposed to yt-dlp through its supported plugin mechanism."""

import base64
import binascii
import json
import re
from urllib.parse import parse_qs, urlencode, urlsplit, urlunsplit

from yt_dlp.extractor.common import InfoExtractor
from yt_dlp.utils import (
    ExtractorError,
    js_to_json,
    smuggle_url,
    unescapeHTML,
    unsmuggle_url,
)


def _script_sources(webpage):
    """Read the player's inline scripts without executing third-party JavaScript."""
    scripts = re.findall(r"(?is)<script\b[^>]*>(.*?)</script\s*>", webpage)
    for script in scripts:
        for match in re.finditer(
            r"""(?s)\b(?:var|let|const)\s+\w+\s*=\s*(["'])(.*?)\1\s*,\s*\w+\s*=\s*atob\(\s*(["'])([A-Za-z0-9+/=\s]+)\3""",
            script,
        ):
            try:
                key = json.loads(js_to_json(match[1] + match[2] + match[1]))
                if not key:
                    continue
                payload = base64.b64decode(re.sub(r"\s+", "", match[4]), validate=True)
                yield bytes(
                    byte ^ (ord(key[index % len(key)]) & 255)
                    for index, byte in enumerate(payload)
                ).decode("utf-8")
            except (ValueError, UnicodeError, binascii.Error):
                continue
    yield from scripts


def _find_hls_url(webpage):
    scripts = [script.replace(r"\/", "/") for script in _script_sources(webpage)]
    for pattern in (
        r"""\bcurrentSrc\b[^;]{0,4096}?(["'])(https?://[^"'\s<>]+\.m3u8[^"'\s<>]*)\1""",
        r"""(["'])(https?://[^"'\s<>]+\.m3u8[^"'\s<>]*)\1""",
    ):
        for script in scripts:
            match = re.search(pattern, script)
            if match:
                try:
                    return unescapeHTML(json.loads(js_to_json(match[1] + match[2] + match[1])))
                except ValueError:
                    continue
    return None


def _inherit_query(url, source_url):
    """Carry the CDN session query to variants, retaining their explicit values."""
    source, target = urlsplit(source_url), urlsplit(url)
    if (target.scheme, target.netloc) != (source.scheme, source.netloc):
        return url
    query = parse_qs(source.query, keep_blank_values=True)
    query.update(parse_qs(target.query, keep_blank_values=True))
    return urlunsplit(target._replace(query=urlencode(query, doseq=True)))


class VidxgoIE(InfoExtractor):
    IE_NAME = "vidxgo"
    _VALID_URL = (
        r"https?://(?:v\.)?vidxgo\.co/(?P<id>(?:tt)?\d+)"
        r"(?:/(?P<season>\d+)/(?P<episode>\d+))?/?(?:[?#]|$)"
    )
    _EMBED_REGEX = [
        r"""(?i)<iframe\b[^>]*\bsrc\s*=\s*["'](?P<url>(?:https?:)?//(?:v\.)?vidxgo\.co/[^"']+)""",
    ]

    @classmethod
    def _extract_from_webpage(cls, url, webpage):
        for embed in dict.fromkeys(cls._extract_embed_urls(url, webpage)):
            yield cls.url_result(smuggle_url(embed, {"referer": url}), cls)

    def _configure_transport(self):
        # Apply only when this player is extracted, including its HLS fragments.
        if self.get_param("impersonate") is None:
            target, _ = self._downloader._parse_impersonate_targets("chrome")
            if target is None:
                raise ExtractorError(
                    "VidXgo richiede curl-cffi. Premi 'Aggiorna yt-dlp' "
                    "oppure esegui INSTALL.bat per installare le dipendenze.",
                    expected=True,
                )
            self._downloader.params["impersonate"] = target

    def _real_extract(self, url):
        url, context = unsmuggle_url(url, {})
        match = self._match_valid_url(url)
        token, season, episode = match.group("id", "season", "episode")
        video_id = token + (f"-s{int(season):02}e{int(episode):02}" if season else "")
        parts = urlsplit(url)
        origin = f"{parts.scheme}://{parts.netloc}"
        self._configure_transport()
        webpage, response = self._download_webpage_handle(
            url, video_id, note="Lettura del player VidXgo",
            headers={"Referer": context.get("referer") or origin + "/"},
            expected_status=(403, 429, 503),
        )
        if response.status in (403, 429, 503):
            if re.search(r"stiamo lavorando|torniamo presto|under maintenance", webpage, re.I):
                message = "il player segnala manutenzione. Riprova quando il sito torna disponibile."
            else:
                message = "accesso rifiutato dal sito o dalla protezione anti-bot."
            raise ExtractorError(f"VidXgo HTTP {response.status}: {message}", expected=True)

        endpoint = origin + "/t/" + token + (f"/{season}/{episode}" if season else "")
        data = self._download_json(
            endpoint, video_id, note="Lettura della sorgente VidXgo", fatal=False,
            headers={"Referer": url, "Accept": "application/json, text/plain, */*"},
            expected_status=(403, 404, 429, 503),
        )
        media_url = data.get("url") if isinstance(data, dict) else None
        if not isinstance(media_url, str) or not re.match(r"https?://", media_url):
            media_url = _find_hls_url(webpage)
        if not media_url:
            raise ExtractorError(
                "VidXgo non ha fornito una sorgente HLS riconoscibile per questo video.",
                expected=True,
            )

        headers = {"Referer": origin + "/", "Origin": origin}
        manifest, manifest_response = self._download_webpage_handle(
            media_url, video_id, note="Lettura delle risoluzioni VidXgo", headers=headers,
        )
        if not manifest.lstrip().startswith("#EXTM3U"):
            raise ExtractorError("VidXgo ha restituito un manifest video non valido.", expected=True)
        manifest_url = manifest_response.url
        formats, subtitles = self._parse_m3u8_formats_and_subtitles(
            manifest, manifest_url, ext="mp4", m3u8_id="hls", headers=headers,
            video_id=video_id,
        )
        query = urlsplit(manifest_url).query
        for item in formats:
            item["url"] = _inherit_query(item["url"], manifest_url)
            item["http_headers"] = headers.copy()
            if query and urlsplit(item["url"]).netloc == urlsplit(manifest_url).netloc:
                item["extra_param_to_segment_url"] = query
        for tracks in subtitles.values():
            for track in tracks:
                track["url"] = _inherit_query(track["url"], manifest_url)
                track["http_headers"] = headers.copy()

        title = self._og_search_title(webpage, default=None) or self._html_extract_title(webpage) or token
        if season:
            title += f" - S{int(season):02}E{int(episode):02}"
        return {
            "id": video_id,
            "title": title,
            "season_number": int(season) if season else None,
            "episode_number": int(episode) if episode else None,
            "formats": formats,
            "subtitles": subtitles,
            "http_headers": headers,
        }
