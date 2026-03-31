import json
import os
import re
import subprocess
from typing import Any, Optional, Union

import requests
from yt_dlp.utils import js_to_json

from app.downloaders.base import Downloader
from app.enmus.note_enums import DownloadQuality
from app.models.audio_model import AudioDownloadResult
from app.services.cookie_manager import CookieConfigManager
from app.utils.logger import get_logger
from app.utils.path_helper import get_data_dir

logger = get_logger(__name__)
cookie_manager = CookieConfigManager()


class XiaoHongShuDownloader(Downloader):
    BASE_HEADERS = {
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36"
        ),
        "Referer": "https://www.xiaohongshu.com/",
        "Cookie": None,
    }

    def __init__(self, cookie: Optional[str] = None):
        super().__init__()
        self.headers_config = self.BASE_HEADERS.copy()
        effective_cookie = cookie.strip() if cookie else cookie_manager.get("xiaohongshu")
        if effective_cookie:
            self.headers_config["Cookie"] = effective_cookie.strip()

    @staticmethod
    def _mask_cookie(cookie: Optional[str]) -> Optional[str]:
        if not cookie:
            return cookie
        if len(cookie) <= 12:
            return "***"
        return f"{cookie[:6]}***{cookie[-6:]}"

    @staticmethod
    def _extract_note_id(url: str) -> str:
        match = re.search(r"/(?:explore|discovery/item)/([\da-fA-F]+)", url)
        return match.group(1) if match else ""

    @staticmethod
    def _extract_initial_state(webpage: str) -> dict[str, Any]:
        match = re.search(r"window\.__INITIAL_STATE__\s*=\s*(\{.*?\})\s*</script>", webpage, re.DOTALL)
        if not match:
            raise ValueError("未找到小红书页面初始数据")
        payload = match.group(1)
        return json.loads(js_to_json(payload))

    @staticmethod
    def _pick_image_urls(note_info: dict[str, Any]) -> list[str]:
        images = []
        for image_info in note_info.get("imageList") or []:
            url = image_info.get("urlDefault") or image_info.get("urlPre")
            if url and url not in images:
                images.append(url)
        return images

    @staticmethod
    def _pick_tags(note_info: dict[str, Any]) -> list[str]:
        tags = []
        for tag in note_info.get("tagList") or []:
            name = str(tag.get("name") or "").strip()
            if name:
                tags.append(name)
        return tags

    @classmethod
    def _extract_content(cls, note_info: dict[str, Any], resolved_url: str) -> dict[str, Any]:
        title = str(note_info.get("title") or "").strip()
        body = str(note_info.get("desc") or "").strip()
        author = (
            str((note_info.get("user") or {}).get("nickname") or "").strip()
            or str((note_info.get("user") or {}).get("userId") or "").strip()
        )
        note_id = str(note_info.get("noteId") or note_info.get("id") or "").strip()
        return {
            "title": title,
            "body": body,
            "images": cls._pick_image_urls(note_info),
            "author": author,
            "note_id": note_id,
            "tags": cls._pick_tags(note_info),
            "resolved_url": resolved_url,
        }

    @staticmethod
    def _iter_stream_nodes(node: Any) -> list[dict[str, Any]]:
        results: list[dict[str, Any]] = []
        if isinstance(node, dict):
            if any(key in node for key in ("masterUrl", "backupUrls", "avgBitrate", "qualityType")):
                results.append(node)
            for value in node.values():
                results.extend(XiaoHongShuDownloader._iter_stream_nodes(value))
        elif isinstance(node, list):
            for item in node:
                results.extend(XiaoHongShuDownloader._iter_stream_nodes(item))
        return results

    @classmethod
    def _pick_video_url(cls, note_info: dict[str, Any]) -> tuple[Optional[str], float]:
        stream_nodes = cls._iter_stream_nodes(((note_info.get("video") or {}).get("media") or {}).get("stream"))
        best_url = None
        best_duration = 0.0
        for node in stream_nodes:
            candidate = node.get("masterUrl")
            if not candidate:
                backup_urls = node.get("backupUrls") or []
                candidate = backup_urls[0] if backup_urls else None
            if candidate:
                best_url = candidate
                duration = float(node.get("duration") or 0) / 1000 if node.get("duration") else 0.0
                best_duration = max(best_duration, duration)
                break
        if best_url:
            return best_url, best_duration
        origin_key = (((note_info.get("video") or {}).get("consumer") or {}).get("originVideoKey") or "").strip()
        if origin_key:
            direct_url = f"https://sns-video-bd.xhscdn.com/{origin_key}"
            return direct_url, best_duration
        return None, best_duration

    @staticmethod
    def _ensure_ffmpeg_to_mp3(video_path: str, mp3_path: str) -> None:
        try:
            subprocess.run(
                ["ffmpeg", "-y", "-i", video_path, "-vn", "-acodec", "libmp3lame", mp3_path],
                check=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        except subprocess.CalledProcessError as exc:
            raise ValueError("ffmpeg 转换 MP3 失败") from exc

    def resolve_url(self, url: str) -> str:
        try:
            response = requests.head(url, headers=self.headers_config, allow_redirects=True, timeout=10)
            if response.ok and response.url and response.url != url:
                return response.url
        except requests.RequestException:
            pass
        try:
            response = requests.get(url, headers=self.headers_config, allow_redirects=True, timeout=10)
            if response.ok and response.url:
                return response.url
        except requests.RequestException:
            logger.info("小红书短链解析失败，回退使用原始链接")
        return url

    def fetch_note(self, url: str) -> dict[str, Any]:
        if not self.headers_config.get("Cookie"):
            raise ValueError("小红书 Cookie 缺失，请先配置有效 Cookie")

        resolved_url = self.resolve_url(url)
        note_id = self._extract_note_id(resolved_url)
        if not note_id:
            raise ValueError("无法识别小红书 note_id")

        logger.info(
            "Fetching xiaohongshu note, note_id=%s, cookie=%s",
            note_id,
            self._mask_cookie(self.headers_config.get("Cookie")),
        )
        response = requests.get(resolved_url, headers=self.headers_config, timeout=15)
        response.raise_for_status()
        initial_state = self._extract_initial_state(response.text)

        note_detail_map = ((initial_state.get("note") or {}).get("noteDetailMap") or {})
        note_wrapper = note_detail_map.get(note_id) or next(iter(note_detail_map.values()), None)
        note_info = ((note_wrapper or {}).get("note") or {})
        if not note_info:
            raise ValueError("小红书笔记不存在或不可访问")

        content = self._extract_content(note_info, resolved_url)
        content_type = "video" if note_info.get("video") else "article"
        return {
            "content_type": content_type,
            "resolved_url": resolved_url,
            "note_id": content["note_id"] or note_id,
            "note_info": note_info,
            "content": content,
        }

    def download(
        self,
        video_url: str,
        output_dir: Union[str, None] = None,
        quality: DownloadQuality = "fast",
        need_video: Optional[bool] = False,
        note_payload: Optional[dict[str, Any]] = None,
    ) -> AudioDownloadResult:
        payload = note_payload or self.fetch_note(video_url)
        if payload.get("content_type") != "video":
            raise ValueError("当前小红书内容不是视频，无法执行转写下载")

        note_info = payload["note_info"]
        content = payload["content"]
        video_file_url, duration = self._pick_video_url(note_info)
        if not video_file_url:
            raise ValueError("小红书视频资源地址提取失败")

        if output_dir is None:
            output_dir = get_data_dir()
        if not output_dir:
            output_dir = self.cache_data
        os.makedirs(output_dir, exist_ok=True)

        note_id = payload["note_id"]
        mp4_path = os.path.join(output_dir, f"{note_id}.mp4")
        mp3_path = os.path.join(output_dir, f"{note_id}.mp3")

        with requests.get(video_file_url, headers=self.headers_config, stream=True, timeout=60) as response:
            response.raise_for_status()
            with open(mp4_path, "wb") as file_obj:
                for chunk in response.iter_content(1024 * 1024):
                    if chunk:
                        file_obj.write(chunk)

        self._ensure_ffmpeg_to_mp3(mp4_path, mp3_path)

        raw_info = {
            "tags": " ".join(content.get("tags") or []),
            "images": content.get("images") or [],
            "author": content.get("author"),
        }
        return AudioDownloadResult(
            file_path=mp3_path,
            title=content.get("title") or content.get("body")[:40],
            duration=duration,
            cover_url=(content.get("images") or [None])[0],
            platform="xiaohongshu",
            video_id=note_id,
            raw_info=raw_info,
            video_path=mp4_path if need_video else None,
        )
