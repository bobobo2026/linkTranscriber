from enum import Enum
from typing import Any, Optional

from fastapi import APIRouter, BackgroundTasks
from pydantic import BaseModel, Field, model_validator

from app.services.service_api import ServiceApi, ServiceApiError
from app.utils.response import ResponseWrapper as R

router = APIRouter(tags=["Service API"])


class PlatformEnum(str, Enum):
    douyin = "douyin"
    xiaohongshu = "xiaohongshu"


class TaskStatusEnum(str, Enum):
    PENDING = "PENDING"
    PARSING = "PARSING"
    DOWNLOADING = "DOWNLOADING"
    TRANSCRIBING = "TRANSCRIBING"
    SUMMARIZING = "SUMMARIZING"
    FORMATTING = "FORMATTING"
    SAVING = "SAVING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"


class ContentTypeEnum(str, Enum):
    video = "video"
    article = "article"


class CreateTranscriptionRequest(BaseModel):
    url: str = Field(
        ...,
        description="待处理的公开视频短链或长链。",
        examples=["https://v.douyin.com/WfuC4_jO6R8/", "http://xhslink.com/o/23s4jTem6em"],
    )
    platform: PlatformEnum = Field(default=PlatformEnum.douyin, description="内容来源平台。")
    cookie: Optional[str] = Field(
        default=None,
        description="可选的平台 Cookie。未传时优先读取服务端已保存配置。",
        examples=["sessionid=xxx; sid_tt=xxx"],
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "url": "https://v.douyin.com/WfuC4_jO6R8/",
                "platform": "douyin",
            }
        }
    }


class TranscriptSegmentPayload(BaseModel):
    start: float = Field(..., description="片段开始时间，单位秒。", examples=[0.0])
    end: float = Field(..., description="片段结束时间，单位秒。", examples=[3.2])
    text: str = Field(..., description="该时间片段对应的转写文本。", examples=["想发财先戒色"])


class TranscriptPayload(BaseModel):
    full_text: str = Field(..., description="完整转写文本或图文归一化正文。")
    segments: list[TranscriptSegmentPayload] = Field(
        default_factory=list,
        description="按时间分段的转写结果。图文内容为空数组。",
    )
    language: Optional[str] = Field(default=None, description="转写识别出的语言。", examples=["zh"])
    raw: Optional[dict[str, Any]] = Field(default=None, description="底层平台或转写器的原始响应。")


class SourcePayload(BaseModel):
    platform: PlatformEnum = Field(..., description="来源平台。")
    url: str = Field(..., description="提交时的原始链接。")
    resolved_url: Optional[str] = Field(default=None, description="短链解析后的真实链接。")


class AudioMetaPayload(BaseModel):
    file_path: str = Field(..., description="服务端落地的本地音频路径。")
    title: str = Field(..., description="内容标题。")
    duration: float = Field(..., description="音频或视频时长，单位秒。")
    cover_url: Optional[str] = Field(default=None, description="封面图链接。")
    platform: str = Field(..., description="音频来源平台。")
    video_id: str = Field(..., description="平台内的唯一内容 ID。")
    raw_info: dict[str, Any] = Field(..., description="下载器返回的原始元信息。")
    video_path: Optional[str] = Field(default=None, description="可选的视频本地路径。")


class ContentPayload(BaseModel):
    title: Optional[str] = Field(default=None, description="内容标题。")
    body: Optional[str] = Field(default=None, description="正文文本。")
    images: list[str] = Field(default_factory=list, description="图文图片链接列表。")
    author: Optional[str] = Field(default=None, description="作者昵称。")
    note_id: Optional[str] = Field(default=None, description="平台内容 ID。")
    tags: list[str] = Field(default_factory=list, description="内容标签。")
    resolved_url: Optional[str] = Field(default=None, description="小红书解析后的内容链接。")


class CreateTranscriptionResponseData(BaseModel):
    task_id: str = Field(..., description="异步转写任务 ID。")
    status: TaskStatusEnum = Field(..., description="当前任务状态。")
    reused: bool = Field(..., description="是否复用了已有成功任务。")


class SummaryResponseData(BaseModel):
    summary_markdown: str = Field(..., description="总结结果，默认输出固定结构的一句话总结加 TodoList。")
    prompt_source: str = Field(..., description="提示词来源，default 或 request。")


class TranscriptionTaskPayload(BaseModel):
    task_id: str = Field(..., description="转写任务 ID。")
    status: TaskStatusEnum = Field(..., description="当前任务状态。")
    platform: PlatformEnum = Field(..., description="来源平台。")
    content_type: Optional[ContentTypeEnum] = Field(
        default=None,
        description="内容类型。视频为 video，图文为 article，未完成任务可能为空。",
    )
    source: SourcePayload = Field(..., description="原始链接与解析信息。")
    audio_meta: Optional[AudioMetaPayload] = Field(default=None, description="音频下载元数据。")
    transcript: Optional[TranscriptPayload] = Field(default=None, description="转写结果。")
    content: Optional[ContentPayload] = Field(default=None, description="结构化内容抽取结果。")
    error_message: Optional[str] = Field(default=None, description="失败时的错误信息。")


class ApiSuccessEnvelope(BaseModel):
    code: int = Field(default=0, description="业务状态码，0 表示成功。")
    msg: str = Field(default="success", description="业务提示信息。")
    data: Any = Field(default=None, description="响应数据。")


class ApiErrorEnvelope(BaseModel):
    code: int = Field(..., description="业务错误码。")
    msg: str = Field(..., description="错误信息。")
    data: Any = Field(default=None, description="附加错误数据。")


class SummaryRequest(BaseModel):
    transcription_task_id: Optional[str] = Field(
        default=None,
        description="已完成转写任务的 task_id。与 transcript 二选一。",
    )
    transcript: Optional[TranscriptPayload] = Field(
        default=None,
        description="直接传入转写结果进行总结。与 transcription_task_id 二选一。",
    )
    provider_id: str = Field(..., description="模型供应商 ID。", examples=["deepseek"])
    model_name: str = Field(..., description="模型名称。", examples=["deepseek-chat"])
    prompt: Optional[str] = Field(
        default=None,
        description="请求级自定义提示词。传入后会覆盖默认总结提示词；默认会返回固定结构的 TodoList。",
    )

    @model_validator(mode="after")
    def validate_input(self):
        if not self.transcription_task_id and not self.transcript:
            raise ValueError("必须提供 transcription_task_id 或 transcript")
        return self

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "transcription_task_id": "8664a91d-c882-43e9-8030-b0633a9ba8b3",
                    "provider_id": "deepseek",
                    "model_name": "deepseek-chat",
                },
                {
                    "transcript": {
                        "full_text": "想发财先戒色",
                        "segments": [{"start": 0.0, "end": 3.2, "text": "想发财先戒色"}],
                        "language": "zh",
                    },
                    "provider_id": "deepseek",
                    "model_name": "deepseek-chat",
                    "prompt": "总结归纳，提取可执行的todolist（最多4点，最好可以锁定时间线）。每条必须包含：事项、执行时间、提醒时间、说明。",
                },
            ]
        }
    }


class CreateTranscriptionSuccessEnvelope(ApiSuccessEnvelope):
    data: CreateTranscriptionResponseData


class GetTranscriptionSuccessEnvelope(ApiSuccessEnvelope):
    data: TranscriptionTaskPayload


class SummarySuccessEnvelope(ApiSuccessEnvelope):
    data: SummaryResponseData


CREATE_TRANSCRIPTION_RESPONSES = {
    400: {"model": ApiErrorEnvelope, "description": "平台不支持、Cookie 缺失或请求参数无效。"},
    500: {"model": ApiErrorEnvelope, "description": "服务内部错误。"},
}

GET_TRANSCRIPTION_RESPONSES = {
    404: {"model": ApiErrorEnvelope, "description": "任务不存在。"},
    500: {"model": ApiErrorEnvelope, "description": "服务内部错误。"},
}

SUMMARY_RESPONSES = {
    400: {"model": ApiErrorEnvelope, "description": "模型参数无效、任务未完成或转写内容为空。"},
    500: {"model": ApiErrorEnvelope, "description": "服务内部错误。"},
}

@router.post(
    "/service/transcriptions",
    summary="创建转写任务",
    description=(
        "提交抖音或小红书链接并创建异步转写任务。"
        "如果命中同平台同链接的历史成功任务，会直接复用已有结果。"
    ),
    response_model=CreateTranscriptionSuccessEnvelope,
    responses=CREATE_TRANSCRIPTION_RESPONSES,
)
def create_transcription(data: CreateTranscriptionRequest, background_tasks: BackgroundTasks):
    try:
        created = ServiceApi.create_transcription_task(
            url=data.url,
            platform=data.platform,
            cookie=data.cookie,
        )
        if not created.get("reused"):
            background_tasks.add_task(
                ServiceApi.run_transcription_task,
                created["task_id"],
                data.url,
                data.platform,
                data.cookie,
            )
        return R.success(
            data={
                "task_id": created["task_id"],
                "status": created["status"],
                "reused": bool(created.get("reused")),
            }
        )
    except ServiceApiError as exc:
        return R.error(msg=str(exc), code=400)
    except Exception as exc:
        return R.error(msg=str(exc), code=500)


@router.get(
    "/service/transcriptions/{task_id}",
    summary="查询转写任务",
    description="轮询指定 task_id 的状态与结果。成功时会返回元信息、转写文本和内容抽取结果。",
    response_model=GetTranscriptionSuccessEnvelope,
    responses=GET_TRANSCRIPTION_RESPONSES,
)
def get_transcription(task_id: str):
    try:
        task = ServiceApi.get_transcription_task(task_id)
        return R.success(data=task)
    except ServiceApiError as exc:
        return R.error(msg=str(exc), code=404)
    except Exception as exc:
        return R.error(msg=str(exc), code=500)


@router.post(
    "/service/summaries",
    summary="生成内容总结",
    description=(
        "基于已完成的转写任务，或直接传入 transcript 内容，调用指定大模型生成总结。"
        "默认提示词会输出固定结构的一句话总结与 TodoList；请求中的 prompt 会完整覆盖默认总结提示词。"
    ),
    response_model=SummarySuccessEnvelope,
    responses=SUMMARY_RESPONSES,
)
def create_summary(data: SummaryRequest):
    try:
        result = ServiceApi.summarize(
            provider_id=data.provider_id,
            model_name=data.model_name,
            prompt=data.prompt,
            transcription_task_id=data.transcription_task_id,
            transcript_payload=data.transcript.model_dump() if data.transcript else None,
        )
        return R.success(data=result)
    except ServiceApiError as exc:
        return R.error(msg=str(exc), code=400)
    except Exception as exc:
        return R.error(msg=str(exc), code=500)
