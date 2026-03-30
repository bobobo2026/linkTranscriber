from typing import Optional

from fastapi import APIRouter, BackgroundTasks
from pydantic import BaseModel, Field, model_validator

from app.services.service_api import ServiceApi, ServiceApiError
from app.utils.response import ResponseWrapper as R

router = APIRouter()


class CreateTranscriptionRequest(BaseModel):
    url: str
    platform: str = "douyin"
    cookie: Optional[str] = None


class TranscriptSegmentPayload(BaseModel):
    start: float
    end: float
    text: str


class TranscriptPayload(BaseModel):
    full_text: str
    segments: list[TranscriptSegmentPayload] = Field(default_factory=list)
    language: Optional[str] = None
    raw: Optional[dict] = None


class SummaryRequest(BaseModel):
    transcription_task_id: Optional[str] = None
    transcript: Optional[TranscriptPayload] = None
    provider_id: str
    model_name: str
    prompt: Optional[str] = None

    @model_validator(mode="after")
    def validate_input(self):
        if not self.transcription_task_id and not self.transcript:
            raise ValueError("必须提供 transcription_task_id 或 transcript")
        return self


@router.post("/service/transcriptions")
def create_transcription(data: CreateTranscriptionRequest, background_tasks: BackgroundTasks):
    try:
        created = ServiceApi.create_transcription_task(
            url=data.url,
            platform=data.platform,
            cookie=data.cookie,
        )
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
            }
        )
    except ServiceApiError as exc:
        return R.error(msg=str(exc), code=400)
    except Exception as exc:
        return R.error(msg=str(exc), code=500)


@router.get("/service/transcriptions/{task_id}")
def get_transcription(task_id: str):
    try:
        task = ServiceApi.get_transcription_task(task_id)
        return R.success(data=task)
    except ServiceApiError as exc:
        return R.error(msg=str(exc), code=404)
    except Exception as exc:
        return R.error(msg=str(exc), code=500)


@router.post("/service/summaries")
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
