import importlib.util
import pathlib
import sys
import types
import unittest


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

    class _DouyinDownloader:
        def __init__(self):
            self.headers_config = {"Cookie": None}

        def download(self, **_kwargs):
            return None

    douyin_mod.DouyinDownloader = _DouyinDownloader

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

    class _TranscriptSegment:
        def __init__(self, start=0, end=0, text=""):
            self.start = start
            self.end = end
            self.text = text

    class _TranscriptResult:
        def __init__(self, language=None, full_text="", segments=None, raw=None):
            self.language = language
            self.full_text = full_text
            self.segments = segments or []
            self.raw = raw

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

    def test_create_transcription_task_rejects_non_douyin(self):
        with self.assertRaises(service_api.ServiceApiError):
            service_api.ServiceApi.create_transcription_task("https://example.com", "xiaohongshu")

    def test_make_downloader_uses_stored_cookie_when_request_cookie_missing(self):
        downloader = service_api.ServiceApi._make_downloader()
        self.assertEqual(downloader.headers_config["Cookie"], "stored-cookie")


if __name__ == "__main__":
    unittest.main()
