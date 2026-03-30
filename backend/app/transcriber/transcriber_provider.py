import os
import platform
from enum import Enum

from app.utils.logger import get_logger

logger = get_logger(__name__)

class TranscriberType(str, Enum):
    FAST_WHISPER = "fast-whisper"
    MLX_WHISPER = "mlx-whisper"
    BCUT = "bcut"
    KUAISHOU = "kuaishou"
    GROQ = "groq"

logger.info('初始化转录服务提供器')

# 转录器单例缓存
_transcribers = {
    TranscriberType.FAST_WHISPER: None,
    TranscriberType.MLX_WHISPER: None,
    TranscriberType.BCUT: None,
    TranscriberType.KUAISHOU: None,
    TranscriberType.GROQ: None,
}

# 公共实例初始化函数
def _init_transcriber(key: TranscriberType, cls, *args, **kwargs):
    if _transcribers[key] is None:
        logger.info(f'创建 {cls.__name__} 实例: {key}')
        try:
            _transcribers[key] = cls(*args, **kwargs)
            logger.info(f'{cls.__name__} 创建成功')
        except Exception as e:
            logger.error(f"{cls.__name__} 创建失败: {e}")
            raise
    return _transcribers[key]


def _load_transcriber_class(transcriber_type: TranscriberType):
    if transcriber_type == TranscriberType.GROQ:
        from app.transcriber.groq import GroqTranscriber
        return GroqTranscriber
    if transcriber_type == TranscriberType.FAST_WHISPER:
        from app.transcriber.whisper import WhisperTranscriber
        return WhisperTranscriber
    if transcriber_type == TranscriberType.BCUT:
        from app.transcriber.bcut import BcutTranscriber
        return BcutTranscriber
    if transcriber_type == TranscriberType.KUAISHOU:
        from app.transcriber.kuaishou import KuaishouTranscriber
        return KuaishouTranscriber
    if transcriber_type == TranscriberType.MLX_WHISPER:
        from app.transcriber.mlx_whisper_transcriber import MLXWhisperTranscriber
        return MLXWhisperTranscriber
    raise ValueError(f"未知转录器类型: {transcriber_type}")


def _is_mlx_whisper_available() -> bool:
    if platform.system() != "Darwin":
        return False
    try:
        _load_transcriber_class(TranscriberType.MLX_WHISPER)
        return True
    except ImportError:
        logger.warning("MLX Whisper 导入失败，可能未安装 mlx_whisper")
        return False


MLX_WHISPER_AVAILABLE = _is_mlx_whisper_available()

# 各类型获取方法
def get_groq_transcriber():
    return _init_transcriber(TranscriberType.GROQ, _load_transcriber_class(TranscriberType.GROQ))

def get_whisper_transcriber(model_size="base", device="cuda"):
    return _init_transcriber(
        TranscriberType.FAST_WHISPER,
        _load_transcriber_class(TranscriberType.FAST_WHISPER),
        model_size=model_size,
        device=device,
    )

def get_bcut_transcriber():
    return _init_transcriber(TranscriberType.BCUT, _load_transcriber_class(TranscriberType.BCUT))

def get_kuaishou_transcriber():
    return _init_transcriber(TranscriberType.KUAISHOU, _load_transcriber_class(TranscriberType.KUAISHOU))

def get_mlx_whisper_transcriber(model_size="base"):
    if not _is_mlx_whisper_available():
        logger.warning("MLX Whisper 不可用，请确保在 Apple 平台且已安装 mlx_whisper")
        raise ImportError("MLX Whisper 不可用")
    return _init_transcriber(
        TranscriberType.MLX_WHISPER,
        _load_transcriber_class(TranscriberType.MLX_WHISPER),
        model_size=model_size,
    )

# 通用入口
def get_transcriber(transcriber_type="fast-whisper", model_size="base", device="cuda"):
    """
    获取指定类型的转录器实例

    参数:
        transcriber_type: 支持 "fast-whisper", "mlx-whisper", "bcut", "kuaishou", "groq"
        model_size: 模型大小，适用于 whisper 类
        device: 设备类型（如 cuda / cpu），仅 whisper 使用

    返回:
        对应类型的转录器实例
    """
    logger.info(f'请求转录器类型: {transcriber_type}')

    try:
        transcriber_enum = TranscriberType(transcriber_type)
    except ValueError:
        logger.warning(f'未知转录器类型 "{transcriber_type}"，默认使用 fast-whisper')
        transcriber_enum = TranscriberType.FAST_WHISPER

    whisper_model_size = os.environ.get("WHISPER_MODEL_SIZE", model_size)

    if transcriber_enum == TranscriberType.FAST_WHISPER:
        return get_whisper_transcriber(whisper_model_size, device=device)

    elif transcriber_enum == TranscriberType.MLX_WHISPER:
        if not _is_mlx_whisper_available():
            raise RuntimeError(
                "MLX Whisper 不可用：需要 macOS 平台并安装 mlx_whisper 包 (pip install mlx_whisper)。"
                "请在「音频转写配置」页面切换到其他转写引擎。"
            )
        return get_mlx_whisper_transcriber(whisper_model_size)

    elif transcriber_enum == TranscriberType.BCUT:
        return get_bcut_transcriber()

    elif transcriber_enum == TranscriberType.KUAISHOU:
        return get_kuaishou_transcriber()

    elif transcriber_enum == TranscriberType.GROQ:
        return get_groq_transcriber()

    # fallback
    logger.warning(f'未识别转录器类型 "{transcriber_type}"，使用 fast-whisper 作为默认')
    return get_whisper_transcriber(whisper_model_size, device=device)
