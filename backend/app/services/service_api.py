import json
import os
import uuid
from dataclasses import asdict
from pathlib import Path
from typing import Any, Optional

import requests

from app.downloaders.douyin_downloader import DouyinDownloader
from app.downloaders.xiaohongshu_downloader import XiaoHongShuDownloader
from app.enmus.note_enums import DownloadQuality
from app.enmus.task_status_enums import TaskStatus
from app.models.model_config import ModelConfig
from app.models.transcriber_model import TranscriptResult, TranscriptSegment
from app.services.provider import ProviderService
from app.services.task_serial_executor import task_serial_executor
from app.services.transcriber_config_manager import TranscriberConfigManager
from app.services.cookie_manager import CookieConfigManager
from app.transcriber.transcriber_provider import get_transcriber
from app.gpt.provider.OpenAI_compatible_provider import OpenAICompatibleProvider
from app.utils.logger import get_logger

logger = get_logger(__name__)
SUPPORTED_PLATFORMS = {"douyin", "xiaohongshu"}

SERVICE_TASK_DIR = Path(os.getenv("NOTE_OUTPUT_DIR", "note_results")) / "service_tasks"
SERVICE_TASK_DIR.mkdir(parents=True, exist_ok=True)

DEFAULT_SUMMARY_PROMPT = os.getenv(
    "SERVICE_SUMMARY_PROMPT",
    (
        "你是一个专业的中文内容总结助手。请根据给定的转写文本输出结构化 Markdown 总结。\n"
        "要求：\n"
        "1. 使用中文输出。\n"
        "2. 只基于提供的转写内容，不要杜撰。\n"
        "3. 优先提炼核心观点、关键事实、步骤和结论。\n"
        "4. 如果文本偏口语化，请整理成更清晰的书面表达。\n"
        "5. 输出中不要使用代码块。\n"
        "6. 如果适合，可使用二级标题和项目符号增强可读性。"
    ),
)


class ServiceApiError(Exception):
    pass


class ServiceTaskStore:
    @staticmethod
    def _task_path(task_id: str) -> Path:
        return SERVICE_TASK_DIR / f"{task_id}.json"

    @classmethod
    def create(cls, payload: dict[str, Any]) -> None:
        path = cls._task_path(payload["task_id"])
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, default=str), encoding="utf-8")

    @classmethod
    def load(cls, task_id: str) -> Optional[dict[str, Any]]:
        path = cls._task_path(task_id)
        if not path.exists():
            return None
        return json.loads(path.read_text(encoding="utf-8"))

    @classmethod
    def update(cls, task_id: str, **fields: Any) -> dict[str, Any]:
        data = cls.load(task_id)
        if data is None:
            raise ServiceApiError(f"转写任务不存在: {task_id}")
        data.update(fields)
        cls.create(data)
        return data

    @classmethod
    def list_all(cls) -> list[dict[str, Any]]:
        tasks: list[dict[str, Any]] = []
        for path in sorted(SERVICE_TASK_DIR.glob("*.json")):
            try:
                tasks.append(json.loads(path.read_text(encoding="utf-8")))
            except Exception:
                logger.warning("跳过损坏的服务任务文件: %s", path)
        return tasks


class ServiceApi:
    @staticmethod
    def _find_reusable_task(platform: str, url: str, resolved_url: Optional[str] = None) -> Optional[dict[str, Any]]:
        for task in reversed(ServiceTaskStore.list_all()):
            if task.get("platform") != platform:
                continue
            if task.get("status") != TaskStatus.SUCCESS.value:
                continue
            transcript = task.get("transcript") or {}
            if not transcript.get("full_text"):
                continue
            source = task.get("source") or {}
            if source.get("url") == url:
                return task
            if resolved_url and source.get("resolved_url") == resolved_url:
                return task
        return None

    @staticmethod
    def _resolve_douyin_url(url: str) -> str:
        if "v.douyin.com" not in url:
            return url
        try:
            response = requests.head(url, allow_redirects=True, timeout=10)
            if response.url:
                return response.url
        except requests.RequestException:
            try:
                response = requests.get(url, allow_redirects=True, timeout=10)
                if response.url:
                    return response.url
            except requests.RequestException:
                logger.info("抖音短链解析失败，回退使用原始链接")
        return url

    @staticmethod
    def _resolve_url(url: str, platform: str, cookie: Optional[str] = None) -> str:
        if platform == "douyin":
            return ServiceApi._resolve_douyin_url(url)
        if platform == "xiaohongshu":
            return ServiceApi._make_downloader(platform=platform, cookie=cookie).resolve_url(url)
        raise ServiceApiError(f"暂不支持的平台: {platform}")

    @staticmethod
    def _make_downloader(platform: str, cookie: Optional[str] = None):
        if platform == "douyin":
            downloader = DouyinDownloader()
        elif platform == "xiaohongshu":
            downloader = XiaoHongShuDownloader(cookie=cookie)
        else:
            raise ServiceApiError(f"暂不支持的平台: {platform}")

        effective_cookie = cookie.strip() if cookie else CookieConfigManager().get(platform)
        if effective_cookie and hasattr(downloader, "headers_config"):
            downloader.headers_config["Cookie"] = effective_cookie.strip()
        return downloader

    @staticmethod
    def _update_status(task_id: str, status: str, error_message: Optional[str] = None) -> None:
        payload: dict[str, Any] = {"status": status}
        if error_message is not None:
            payload["error_message"] = error_message
        ServiceTaskStore.update(task_id, **payload)

    @staticmethod
    def create_transcription_task(url: str, platform: str, cookie: Optional[str] = None) -> dict[str, str]:
        if platform not in SUPPORTED_PLATFORMS:
            raise ServiceApiError(f"首版仅支持 {', '.join(sorted(SUPPORTED_PLATFORMS))} 平台")

        resolved_url = ServiceApi._resolve_url(url=url, platform=platform, cookie=cookie)
        reusable_task = ServiceApi._find_reusable_task(platform=platform, url=url, resolved_url=resolved_url)
        if reusable_task:
            return {
                "task_id": reusable_task["task_id"],
                "status": reusable_task["status"],
                "cookie": cookie,
                "reused": True,
            }

        task_id = str(uuid.uuid4())
        ServiceTaskStore.create(
            {
                "task_id": task_id,
                "status": TaskStatus.PENDING.value,
                "platform": platform,
                "content_type": None,
                "source": {
                    "platform": platform,
                    "url": url,
                    "resolved_url": resolved_url,
                },
                "audio_meta": None,
                "transcript": None,
                "content": None,
                "error_message": None,
            }
        )

        return {"task_id": task_id, "status": TaskStatus.PENDING.value, "cookie": cookie, "reused": False}

    @staticmethod
    def _transcribe_audio(audio_meta) -> TranscriptResult:
        config_manager = TranscriberConfigManager()
        transcriber = get_transcriber(
            transcriber_type=config_manager.get_transcriber_type(),
            model_size=config_manager.get_whisper_model_size(),
            device="cuda",
        )
        transcript = transcriber.transcript(file_path=audio_meta.file_path)
        if transcript is None or not transcript.full_text:
            raise ServiceApiError("转写结果为空")
        return transcript

    @staticmethod
    def _build_article_transcript(title: str, body: str, raw: Optional[dict[str, Any]] = None) -> TranscriptResult:
        parts = [part.strip() for part in (title, body) if part and part.strip()]
        full_text = "\n\n".join(parts)
        if not full_text:
            raise ServiceApiError("图文正文为空")
        return TranscriptResult(language="zh", full_text=full_text, segments=[], raw=raw)

    @staticmethod
    def _run_douyin_task(task_id: str, resolved_url: str, cookie: Optional[str]) -> None:
        ServiceApi._update_status(task_id, TaskStatus.DOWNLOADING.value, None)
        downloader = ServiceApi._make_downloader(platform="douyin", cookie=cookie)
        audio_meta = downloader.download(
            video_url=resolved_url,
            quality=DownloadQuality.medium,
            output_dir=None,
            need_video=False,
        )

        ServiceApi._update_status(task_id, TaskStatus.TRANSCRIBING.value, None)
        transcript = ServiceApi._transcribe_audio(audio_meta)
        ServiceTaskStore.update(
            task_id,
            status=TaskStatus.SUCCESS.value,
            content_type="video",
            audio_meta=asdict(audio_meta),
            transcript=asdict(transcript),
            content=None,
            error_message=None,
        )

    @staticmethod
    def _run_xiaohongshu_task(task_id: str, resolved_url: str, cookie: Optional[str]) -> None:
        downloader = ServiceApi._make_downloader(platform="xiaohongshu", cookie=cookie)
        note_payload = downloader.fetch_note(resolved_url)
        content = note_payload["content"]

        if note_payload["content_type"] == "article":
            transcript = ServiceApi._build_article_transcript(
                title=content.get("title") or "",
                body=content.get("body") or "",
                raw=note_payload.get("note_info"),
            )
            ServiceTaskStore.update(
                task_id,
                status=TaskStatus.SUCCESS.value,
                content_type="article",
                audio_meta=None,
                transcript=asdict(transcript),
                content=content,
                error_message=None,
            )
            return

        ServiceApi._update_status(task_id, TaskStatus.DOWNLOADING.value, None)
        audio_meta = downloader.download(
            video_url=resolved_url,
            quality=DownloadQuality.medium,
            output_dir=None,
            need_video=False,
            note_payload=note_payload,
        )
        ServiceApi._update_status(task_id, TaskStatus.TRANSCRIBING.value, None)
        transcript = ServiceApi._transcribe_audio(audio_meta)
        ServiceTaskStore.update(
            task_id,
            status=TaskStatus.SUCCESS.value,
            content_type="video",
            audio_meta=asdict(audio_meta),
            transcript=asdict(transcript),
            content=content,
            error_message=None,
        )

    @staticmethod
    def run_transcription_task(task_id: str, url: str, platform: str, cookie: Optional[str] = None) -> None:
        def _execute() -> None:
            try:
                ServiceApi._update_status(task_id, TaskStatus.PARSING.value, None)
                task = ServiceTaskStore.load(task_id) or {}
                resolved_url = ((task.get("source") or {}).get("resolved_url")) or ServiceApi._resolve_url(
                    url=url,
                    platform=platform,
                    cookie=cookie,
                )
                ServiceTaskStore.update(task_id, source={"platform": platform, "url": url, "resolved_url": resolved_url})
                if platform == "douyin":
                    ServiceApi._run_douyin_task(task_id, resolved_url, cookie)
                elif platform == "xiaohongshu":
                    ServiceApi._run_xiaohongshu_task(task_id, resolved_url, cookie)
                else:
                    raise ServiceApiError(f"暂不支持的平台: {platform}")
            except Exception as exc:
                logger.error("服务化转写任务失败: %s", exc, exc_info=True)
                ServiceTaskStore.update(task_id, status=TaskStatus.FAILED.value, error_message=str(exc))

        task_serial_executor.run(_execute)

    @staticmethod
    def get_transcription_task(task_id: str) -> dict[str, Any]:
        task = ServiceTaskStore.load(task_id)
        if task is None:
            raise ServiceApiError(f"转写任务不存在: {task_id}")
        return task

    @staticmethod
    def _build_summary_prompt(prompt: Optional[str], transcript: TranscriptResult) -> tuple[str, str]:
        prompt_text = (prompt or DEFAULT_SUMMARY_PROMPT).strip()
        transcript_text = ServiceApi._segments_to_markdown_text(transcript)
        if "{transcript}" in prompt_text:
            final_prompt = prompt_text.replace("{transcript}", transcript_text)
        else:
            final_prompt = f"{prompt_text}\n\n转写文本如下：\n{transcript_text}"
        return final_prompt, ("request" if prompt else "default")

    @staticmethod
    def _segments_to_markdown_text(transcript: TranscriptResult) -> str:
        if transcript.segments:
            parts = []
            for segment in transcript.segments:
                parts.append(
                    f"[{ServiceApi._format_seconds(segment.start)}-{ServiceApi._format_seconds(segment.end)}] {segment.text}"
                )
            return "\n".join(parts)
        return transcript.full_text

    @staticmethod
    def _format_seconds(seconds: float) -> str:
        total = max(int(seconds), 0)
        minutes = total // 60
        remain = total % 60
        return f"{minutes:02d}:{remain:02d}"

    @staticmethod
    def _normalize_transcript(payload: dict[str, Any]) -> TranscriptResult:
        segments = [
            TranscriptSegment(
                start=float(segment.get("start", 0)),
                end=float(segment.get("end", 0)),
                text=str(segment.get("text", "")).strip(),
            )
            for segment in payload.get("segments", []) or []
            if str(segment.get("text", "")).strip()
        ]
        full_text = str(payload.get("full_text", "")).strip()
        if not full_text and segments:
            full_text = "\n".join(segment.text for segment in segments)
        if not full_text:
            raise ServiceApiError("transcript 不能为空")
        return TranscriptResult(
            language=payload.get("language"),
            full_text=full_text,
            segments=segments,
            raw=payload.get("raw"),
        )

    @staticmethod
    def _get_summary_client(provider_id: str, model_name: str):
        provider = ProviderService.get_provider_by_id(provider_id)
        if not provider:
            raise ServiceApiError(f"未找到模型供应商: {provider_id}")
        config = ModelConfig(
            api_key=provider["api_key"],
            base_url=provider["base_url"],
            model_name=model_name,
            provider=provider["type"],
            name=provider["name"],
        )
        return OpenAICompatibleProvider(api_key=config.api_key, base_url=config.base_url).get_client

    @staticmethod
    def summarize(
        provider_id: str,
        model_name: str,
        prompt: Optional[str] = None,
        transcription_task_id: Optional[str] = None,
        transcript_payload: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]:
        if transcription_task_id:
            task = ServiceApi.get_transcription_task(transcription_task_id)
            if task["status"] != TaskStatus.SUCCESS.value:
                raise ServiceApiError("转写任务未完成，暂时无法总结")
            transcript = ServiceApi._normalize_transcript(task.get("transcript") or {})
        elif transcript_payload:
            transcript = ServiceApi._normalize_transcript(transcript_payload)
        else:
            raise ServiceApiError("必须提供 transcription_task_id 或 transcript")

        final_prompt, prompt_source = ServiceApi._build_summary_prompt(prompt, transcript)
        client = ServiceApi._get_summary_client(provider_id, model_name)
        response = client.chat.completions.create(
            model=model_name,
            messages=[{"role": "user", "content": final_prompt}],
            temperature=0.7,
        )
        summary_markdown = (response.choices[0].message.content or "").strip()
        if not summary_markdown:
            raise ServiceApiError("总结结果为空")
        return {
            "summary_markdown": summary_markdown,
            "prompt_source": prompt_source,
        }
