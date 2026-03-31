import importlib.util
import json
import pathlib
import sys
import types
import unittest
from dataclasses import dataclass
from datetime import date, timedelta


ROOT = pathlib.Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "app" / "services" / "service_api.py"


def _install_stubs():
    app_mod = types.ModuleType("app")
    app_mod.__path__ = []
    downloaders_pkg = types.ModuleType("app.downloaders")
    enmus_pkg = types.ModuleType("app.enmus")
    models_pkg = types.ModuleType("app.models")
    services_pkg = types.ModuleType("app.services")
    transcriber_pkg = types.ModuleType("app.transcriber")
    gpt_pkg = types.ModuleType("app.gpt")
    provider_pkg = types.ModuleType("app.gpt.provider")
    utils_pkg = types.ModuleType("app.utils")

    douyin_mod = types.ModuleType("app.downloaders.douyin_downloader")
    xhs_mod = types.ModuleType("app.downloaders.xiaohongshu_downloader")

    class _DouyinDownloader:
        def __init__(self):
            self.headers_config = {"Cookie": None}

        def download(self, **_kwargs):
            return None

    douyin_mod.DouyinDownloader = _DouyinDownloader

    @dataclass
    class _AudioDownloadResult:
        file_path: str = ""
        title: str = ""
        duration: float = 0
        cover_url: str | None = None
        platform: str = ""
        video_id: str = ""
        raw_info: dict | None = None
        video_path: str | None = None

    class _XiaoHongShuDownloader:
        note_payload = {
            "content_type": "article",
            "resolved_url": "https://www.xiaohongshu.com/explore/abc123",
            "note_id": "abc123",
            "note_info": {"id": "abc123"},
            "content": {
                "title": "标题",
                "body": "正文",
                "images": ["https://img/1.jpg"],
                "author": "作者",
                "note_id": "abc123",
                "tags": ["标签"],
                "resolved_url": "https://www.xiaohongshu.com/explore/abc123",
            },
        }

        def __init__(self, cookie=None):
            self.headers_config = {"Cookie": cookie}

        def resolve_url(self, url):
            return self.note_payload.get("resolved_url") or url

        def fetch_note(self, _url):
            return self.note_payload

        def download(self, **_kwargs):
            return _AudioDownloadResult(
                file_path="/tmp/test.mp3",
                title="视频标题",
                duration=3.2,
                cover_url="https://img/cover.jpg",
                platform="xiaohongshu",
                video_id="video123",
                raw_info={"tags": "标签"},
            )

    xhs_mod.XiaoHongShuDownloader = _XiaoHongShuDownloader

    note_enums_mod = types.ModuleType("app.enmus.note_enums")

    class _DownloadQuality:
        medium = "medium"

    note_enums_mod.DownloadQuality = _DownloadQuality

    task_status_mod = types.ModuleType("app.enmus.task_status_enums")

    class _EnumValue:
        def __init__(self, value):
            self.value = value

    class _TaskStatus:
        PENDING = _EnumValue("PENDING")
        PARSING = _EnumValue("PARSING")
        DOWNLOADING = _EnumValue("DOWNLOADING")
        TRANSCRIBING = _EnumValue("TRANSCRIBING")
        SUCCESS = _EnumValue("SUCCESS")
        FAILED = _EnumValue("FAILED")

    task_status_mod.TaskStatus = _TaskStatus

    model_config_mod = types.ModuleType("app.models.model_config")

    class _ModelConfig:
        def __init__(self, **kwargs):
            self.__dict__.update(kwargs)

    model_config_mod.ModelConfig = _ModelConfig

    transcriber_model_mod = types.ModuleType("app.models.transcriber_model")

    @dataclass
    class _TranscriptSegment:
        start: float = 0
        end: float = 0
        text: str = ""

    @dataclass
    class _TranscriptResult:
        language: str | None = None
        full_text: str = ""
        segments: list | None = None
        raw: dict | None = None

        def __post_init__(self):
            if self.segments is None:
                self.segments = []

    transcriber_model_mod.TranscriptSegment = _TranscriptSegment
    transcriber_model_mod.TranscriptResult = _TranscriptResult

    provider_service_mod = types.ModuleType("app.services.provider")

    class _ProviderService:
        @staticmethod
        def get_provider_by_id(_provider_id):
            return None

    provider_service_mod.ProviderService = _ProviderService

    task_executor_mod = types.ModuleType("app.services.task_serial_executor")

    class _Executor:
        @staticmethod
        def run(fn):
            return fn()

    task_executor_mod.task_serial_executor = _Executor()

    transcriber_config_mod = types.ModuleType("app.services.transcriber_config_manager")

    class _ConfigManager:
        @staticmethod
        def get_transcriber_type():
            return "fast-whisper"

        @staticmethod
        def get_whisper_model_size():
            return "base"

    transcriber_config_mod.TranscriberConfigManager = _ConfigManager

    cookie_manager_mod = types.ModuleType("app.services.cookie_manager")

    class _CookieConfigManager:
        @staticmethod
        def get(_platform):
            return "stored-cookie"

    cookie_manager_mod.CookieConfigManager = _CookieConfigManager

    transcriber_provider_mod = types.ModuleType("app.transcriber.transcriber_provider")

    def _get_transcriber(**_kwargs):
        return None

    transcriber_provider_mod.get_transcriber = _get_transcriber

    openai_provider_mod = types.ModuleType("app.gpt.provider.OpenAI_compatible_provider")

    class _OpenAICompatibleProvider:
        def __init__(self, **_kwargs):
            self._client = None

        @property
        def get_client(self):
            return self._client

    openai_provider_mod.OpenAICompatibleProvider = _OpenAICompatibleProvider

    logger_mod = types.ModuleType("app.utils.logger")

    class _Logger:
        def info(self, *_args, **_kwargs):
            pass

        def error(self, *_args, **_kwargs):
            pass

    def _get_logger(_name):
        return _Logger()

    logger_mod.get_logger = _get_logger

    sys.modules.setdefault("app", app_mod)
    sys.modules.setdefault("app.downloaders", downloaders_pkg)
    sys.modules.setdefault("app.enmus", enmus_pkg)
    sys.modules.setdefault("app.models", models_pkg)
    sys.modules.setdefault("app.services", services_pkg)
    sys.modules.setdefault("app.transcriber", transcriber_pkg)
    sys.modules.setdefault("app.gpt", gpt_pkg)
    sys.modules.setdefault("app.gpt.provider", provider_pkg)
    sys.modules.setdefault("app.utils", utils_pkg)
    sys.modules["app.downloaders.douyin_downloader"] = douyin_mod
    sys.modules["app.downloaders.xiaohongshu_downloader"] = xhs_mod
    sys.modules["app.enmus.note_enums"] = note_enums_mod
    sys.modules["app.enmus.task_status_enums"] = task_status_mod
    sys.modules["app.models.model_config"] = model_config_mod
    sys.modules["app.models.transcriber_model"] = transcriber_model_mod
    sys.modules["app.services.provider"] = provider_service_mod
    sys.modules["app.services.task_serial_executor"] = task_executor_mod
    sys.modules["app.services.transcriber_config_manager"] = transcriber_config_mod
    sys.modules["app.services.cookie_manager"] = cookie_manager_mod
    sys.modules["app.transcriber.transcriber_provider"] = transcriber_provider_mod
    sys.modules["app.gpt.provider.OpenAI_compatible_provider"] = openai_provider_mod
    sys.modules["app.utils.logger"] = logger_mod


_install_stubs()
spec = importlib.util.spec_from_file_location("service_api", MODULE_PATH)
if spec is None or spec.loader is None:
    raise ImportError("service_api module spec not found")
service_api = importlib.util.module_from_spec(spec)
spec.loader.exec_module(service_api)


class TestServiceApi(unittest.TestCase):
    def setUp(self):
        for path in service_api.SERVICE_TASK_DIR.glob("*.json"):
            path.unlink()
        if service_api.QUOTA_STATE_PATH.exists():
            service_api.QUOTA_STATE_PATH.unlink()
        service_api.XiaoHongShuDownloader.note_payload = {
            "content_type": "article",
            "resolved_url": "https://www.xiaohongshu.com/explore/abc123",
            "note_id": "abc123",
            "note_info": {"id": "abc123"},
            "content": {
                "title": "标题",
                "body": "正文",
                "images": ["https://img/1.jpg"],
                "author": "作者",
                "note_id": "abc123",
                "tags": ["标签"],
                "resolved_url": "https://www.xiaohongshu.com/explore/abc123",
            },
        }

    def test_build_summary_prompt_uses_placeholder_when_present(self):
        transcript = service_api.TranscriptResult(
            language="zh",
            full_text="全文",
            segments=[service_api.TranscriptSegment(start=0, end=3, text="第一句")],
        )
        prompt, source = service_api.ServiceApi._build_summary_prompt(
            "请总结以下内容：\n{transcript}",
            transcript,
        )
        self.assertIn("第一句", prompt)
        self.assertNotIn("转写文本如下：", prompt)
        self.assertEqual(source, "request")

    def test_build_summary_prompt_uses_structured_todolist_template_by_default(self):
        transcript = service_api.TranscriptResult(
            language="zh",
            full_text="全文",
            segments=[],
        )
        prompt, source = service_api.ServiceApi._build_summary_prompt(None, transcript)
        self.assertIn("一句话总结：", prompt)
        self.assertIn("TodoList：", prompt)
        self.assertIn("提醒时间：", prompt)
        self.assertIn("全文", prompt)
        self.assertEqual(source, "default")

    def test_normalize_transcript_falls_back_to_segments(self):
        transcript = service_api.ServiceApi._normalize_transcript(
            {
                "segments": [
                    {"start": 0, "end": 1, "text": "你好"},
                    {"start": 1, "end": 2, "text": "世界"},
                ]
            }
        )
        self.assertEqual(transcript.full_text, "你好\n世界")
        self.assertEqual(len(transcript.segments), 2)

    def test_create_transcription_task_accepts_xiaohongshu(self):
        created = service_api.ServiceApi.create_transcription_task("https://xhslink.com/abc", "xiaohongshu")
        self.assertEqual(created["status"], "PENDING")
        self.assertFalse(created["reused"])
        quota_state = service_api.ServiceQuotaStore.load()
        self.assertEqual(quota_state["used_count"], 1)

    def test_make_downloader_uses_stored_cookie_when_request_cookie_missing(self):
        downloader = service_api.ServiceApi._make_downloader(platform="douyin")
        self.assertEqual(downloader.headers_config["Cookie"], "stored-cookie")

    def test_make_xiaohongshu_downloader_uses_stored_cookie_when_request_cookie_missing(self):
        downloader = service_api.ServiceApi._make_downloader(platform="xiaohongshu")
        self.assertEqual(downloader.headers_config["Cookie"], "stored-cookie")

    def test_build_article_transcript_uses_title_and_body(self):
        transcript = service_api.ServiceApi._build_article_transcript("标题", "正文")
        self.assertEqual(transcript.full_text, "标题\n\n正文")
        self.assertEqual(transcript.segments, [])

    def test_run_xiaohongshu_article_task_skips_transcriber(self):
        task_id = "xhs-article"
        service_api.ServiceTaskStore.create(
            {
                "task_id": task_id,
                "status": "PENDING",
                "platform": "xiaohongshu",
                "content_type": None,
                "source": {"platform": "xiaohongshu", "url": "https://xhslink.com/a", "resolved_url": None},
                "audio_meta": None,
                "transcript": None,
                "content": None,
                "error_message": None,
            }
        )
        service_api.ServiceApi.run_transcription_task(task_id, "https://xhslink.com/a", "xiaohongshu")
        task = service_api.ServiceTaskStore.load(task_id)
        self.assertEqual(task["status"], "SUCCESS")
        self.assertEqual(task["content_type"], "article")
        self.assertEqual(task["content"]["author"], "作者")
        self.assertEqual(task["transcript"]["full_text"], "标题\n\n正文")

    def test_run_xiaohongshu_video_task_returns_audio_meta_and_content(self):
        task_id = "xhs-video"
        service_api.ServiceTaskStore.create(
            {
                "task_id": task_id,
                "status": "PENDING",
                "platform": "xiaohongshu",
                "content_type": None,
                "source": {"platform": "xiaohongshu", "url": "https://xhslink.com/v", "resolved_url": None},
                "audio_meta": None,
                "transcript": None,
                "content": None,
                "error_message": None,
            }
        )
        service_api.XiaoHongShuDownloader.note_payload = {
            "content_type": "video",
            "resolved_url": "https://www.xiaohongshu.com/explore/video123",
            "note_id": "video123",
            "note_info": {"id": "video123"},
            "content": {
                "title": "视频标题",
                "body": "视频正文",
                "images": ["https://img/cover.jpg"],
                "author": "作者",
                "note_id": "video123",
                "tags": ["标签"],
                "resolved_url": "https://www.xiaohongshu.com/explore/video123",
            },
        }

        class _Transcriber:
            @staticmethod
            def transcript(file_path):
                return service_api.TranscriptResult(
                    language="zh",
                    full_text=f"来自 {file_path} 的转写",
                    segments=[],
                )

        service_api.get_transcriber = lambda **_kwargs: _Transcriber()
        service_api.ServiceApi.run_transcription_task(task_id, "https://xhslink.com/v", "xiaohongshu")
        task = service_api.ServiceTaskStore.load(task_id)
        self.assertEqual(task["status"], "SUCCESS")
        self.assertEqual(task["content_type"], "video")
        self.assertEqual(task["audio_meta"]["platform"], "xiaohongshu")
        self.assertEqual(task["content"]["note_id"], "video123")
        self.assertIn("转写", task["transcript"]["full_text"])

    def test_create_transcription_task_reuses_existing_success_task_by_same_url(self):
        existing_task_id = "existing-success"
        service_api.ServiceTaskStore.create(
            {
                "task_id": existing_task_id,
                "status": "SUCCESS",
                "platform": "xiaohongshu",
                "content_type": "article",
                "source": {
                    "platform": "xiaohongshu",
                    "url": "https://xhslink.com/reuse",
                    "resolved_url": "https://www.xiaohongshu.com/explore/reuse123",
                },
                "audio_meta": None,
                "transcript": {"full_text": "已存在的正文", "segments": []},
                "content": {"title": "旧标题"},
                "error_message": None,
            }
        )
        created = service_api.ServiceApi.create_transcription_task("https://xhslink.com/reuse", "xiaohongshu")
        self.assertEqual(created["task_id"], existing_task_id)
        self.assertEqual(created["status"], "SUCCESS")
        self.assertTrue(created["reused"])
        self.assertEqual(service_api.ServiceQuotaStore.load()["used_count"], 0)

    def test_create_transcription_task_reuses_existing_success_task_by_resolved_url(self):
        existing_task_id = "existing-by-resolved"
        service_api.ServiceTaskStore.create(
            {
                "task_id": existing_task_id,
                "status": "SUCCESS",
                "platform": "xiaohongshu",
                "content_type": "video",
                "source": {
                    "platform": "xiaohongshu",
                    "url": "https://www.xiaohongshu.com/explore/video123",
                    "resolved_url": "https://www.xiaohongshu.com/explore/video123",
                },
                "audio_meta": {"platform": "xiaohongshu"},
                "transcript": {"full_text": "旧转写", "segments": []},
                "content": {"title": "旧视频"},
                "error_message": None,
            }
        )
        service_api.XiaoHongShuDownloader.note_payload = {
            "content_type": "video",
            "resolved_url": "https://www.xiaohongshu.com/explore/video123",
            "note_id": "video123",
            "note_info": {"id": "video123"},
            "content": {
                "title": "视频标题",
                "body": "视频正文",
                "images": ["https://img/cover.jpg"],
                "author": "作者",
                "note_id": "video123",
                "tags": ["标签"],
                "resolved_url": "https://www.xiaohongshu.com/explore/video123",
            },
        }
        created = service_api.ServiceApi.create_transcription_task("https://xhslink.com/v2", "xiaohongshu")
        self.assertEqual(created["task_id"], existing_task_id)
        self.assertEqual(created["status"], "SUCCESS")
        self.assertTrue(created["reused"])

    def test_quota_blocks_new_transcription_after_limit(self):
        state = {
            "date": date.today().isoformat(),
            "used_count": service_api.DAILY_FREE_TRANSCRIPTION_LIMIT,
            "limit": service_api.DAILY_FREE_TRANSCRIPTION_LIMIT,
        }
        service_api.QUOTA_STATE_PATH.write_text(json.dumps(state, ensure_ascii=False), encoding="utf-8")
        with self.assertRaises(service_api.ServiceApiQuotaExceededError) as ctx:
            service_api.ServiceApi.create_transcription_task("https://xhslink.com/blocked", "xiaohongshu")
        self.assertIn("今日免费转写额度已用完", str(ctx.exception))
        self.assertEqual(ctx.exception.data["quota_limit"], service_api.DAILY_FREE_TRANSCRIPTION_LIMIT)

    def test_quota_resets_on_next_day(self):
        state = {
            "date": (date.today() - timedelta(days=1)).isoformat(),
            "used_count": service_api.DAILY_FREE_TRANSCRIPTION_LIMIT,
            "limit": service_api.DAILY_FREE_TRANSCRIPTION_LIMIT,
        }
        service_api.QUOTA_STATE_PATH.write_text(json.dumps(state, ensure_ascii=False), encoding="utf-8")
        quota_state = service_api.ServiceQuotaStore.load()
        self.assertEqual(quota_state["used_count"], 0)
        self.assertEqual(quota_state["date"], date.today().isoformat())

    def test_get_quota_status_returns_remaining_count(self):
        state = {
            "date": date.today().isoformat(),
            "used_count": 7,
            "limit": service_api.DAILY_FREE_TRANSCRIPTION_LIMIT,
        }
        service_api.QUOTA_STATE_PATH.write_text(json.dumps(state, ensure_ascii=False), encoding="utf-8")
        quota_status = service_api.ServiceApi.get_quota_status()
        self.assertEqual(quota_status["quota_limit"], service_api.DAILY_FREE_TRANSCRIPTION_LIMIT)
        self.assertEqual(quota_status["quota_used"], 7)
        self.assertEqual(quota_status["quota_remaining"], service_api.DAILY_FREE_TRANSCRIPTION_LIMIT - 7)
        self.assertIn("00:00:00", quota_status["reset_at"])

    def test_summarize_prefers_request_level_api_key(self):
        transcript_payload = {"full_text": "转写文本", "segments": []}

        class _Message:
            content = "总结结果"

        class _Choice:
            message = _Message()

        class _Response:
            choices = [_Choice()]

        class _Completions:
            @staticmethod
            def create(**_kwargs):
                return _Response()

        class _Chat:
            pass

        _Chat.completions = _Completions()

        class _Client:
            pass

        _Client.chat = _Chat()

        captured = {}

        class _Provider:
            def __init__(self, **kwargs):
                captured.update(kwargs)

            @property
            def get_client(self):
                return _Client()

        service_api.OpenAICompatibleProvider = _Provider
        result = service_api.ServiceApi.summarize(
            model_name="deepseek-chat",
            api_key="sk-test",
            base_url="https://api.deepseek.com",
            transcript_payload=transcript_payload,
        )
        self.assertEqual(captured["api_key"], "sk-test")
        self.assertEqual(captured["base_url"], "https://api.deepseek.com")
        self.assertEqual(result["summary_markdown"], "总结结果")

    def test_summarize_requires_base_url_when_api_key_present(self):
        with self.assertRaises(service_api.ServiceApiError) as ctx:
            service_api.ServiceApi.summarize(
                model_name="deepseek-chat",
                api_key="sk-test",
                transcript_payload={"full_text": "转写文本", "segments": []},
            )
        self.assertIn("base_url", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
