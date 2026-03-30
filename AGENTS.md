# AGENTS

## Project

- Public project name: `linkTranscriber`
- Source lineage: iterated from `BiliNote`
- Current focus: service-style backend for link transcription and LLM summaries
- Current V1 scope:
  - `douyin` only
  - `video` only
  - async transcription task
  - sync summary API

## Core APIs

- `POST /api/service/transcriptions`
- `GET /api/service/transcriptions/{task_id}`
- `POST /api/service/summaries`

## Online Deployment

- Server: `root@139.196.124.192`
- SSH key used historically: `~/.ssh/nailcare.pem`
- Parallel app dir: `/opt/linktranscriber-api`
- systemd service: `linktranscriber-api`
- internal app port: `127.0.0.1:18001`

## Current Public Entrances

Preferred stable IP entrance:

- `http://139.196.124.192/linktranscriber-api/api/sys_check`
- Base path: `http://139.196.124.192/linktranscriber-api`

Temporary HTTPS entrance:

- `https://xtf.spacebit.cn/linktranscriber-api/api/sys_check`
- Base path: `https://xtf.spacebit.cn/linktranscriber-api`

## Domain Status

- `linktranscriber.store` is not currently usable as the formal public entrance.
- Root cause is not FastAPI or Nginx. The domain is being intercepted by an ICP compliance block page.
- Do not claim `linktranscriber.store` is production-ready until the filing/domain-side issue is resolved.

## GitHub / CI-CD

- Public repo: `https://github.com/bobobo2026/linkTranscriber`
- Deployment workflow: `.github/workflows/deploy-server.yml`
- API docs workflow: `.github/workflows/deploy-api-docs.yml`
- Deploy mode: GitHub Actions rsyncs code to server, then runs `scripts/deploy-server.sh`
- Runtime bootstrap script: `scripts/configure-runtime.sh`
- Service dependency set for server: `backend/requirements-service.txt`

Expected GitHub secrets:

- `DEPLOY_HOST`
- `DEPLOY_USER`
- `DEPLOY_SSH_KEY`

## API Docs

- FastAPI runtime docs remain available at `/docs`, `/redoc`, `/openapi.json`
- Static API docs are built from `docs/openapi.json`
- Local build command: `bash scripts/build-api-docs.sh`
- GitHub Pages should publish the generated static site from workflow `deploy-api-docs.yml`

## Runtime Notes

- The server uses stored downloader config, so Douyin cookie does not need to be sent on every request.
- DeepSeek is configured server-side and has been verified with `deepseek-chat`.
- `ffmpeg` is required and has already been installed on the target server.

## Verified Online Smoke Results

Latest verified on `2026-03-30`:

- `GET /api/sys_check`: success
- `GET /api/get_provider_by_id/deepseek`: success
- Real Douyin transcription: success
- DeepSeek summary with default prompt: success
- DeepSeek summary with request-level prompt override: success

Verified task example:

- `task_id`: `5f56e32e-f439-43c2-93c0-a94bd53b103d`

## Current Behavior Expectations

- Creating a transcription task should immediately return `PENDING`
- Polling should move through `TRANSCRIBING` and then `SUCCESS` or `FAILED`
- Successful transcription returns:
  - `source`
  - `audio_meta`
  - `transcript.full_text`
  - `transcript.segments`
- Summary API accepts either:
  - `transcription_task_id`
  - direct `transcript`
- Request `prompt` fully overrides the default summary prompt

## Security Notes

- Do not print full Douyin cookies into logs.
- `backend/app/downloaders/douyin_downloader.py` was patched to mask cookie logging.
- Any API key or cookie that appeared in chat should be rotated outside the repo.
- Never commit live secrets into git.

## Recommended Next Steps

- If a true independent domain is still required, use a new domain or subdomain that is not under ICP interception.
- If continuing development locally, prefer a clean clone of `bobobo2026/linkTranscriber` instead of relying on the old `BiliNote` shallow clone history.
- If product scope expands, next natural step is a combined endpoint that returns transcription plus summary in one request.
