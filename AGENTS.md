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

## Deployment Privacy

- Do not publish real production IPs, hostnames, or direct public access paths into the public repository.
- Keep public docs limited to local development examples and generic deployment guidance.
- Treat concrete server login info, public entrypoints, and infrastructure coordinates as private operational data.

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

## Verified Smoke Results

Latest verified locally and during deployment:

- `GET /api/sys_check`: success
- `GET /api/get_provider_by_id/deepseek`: success
- Real transcription: success
- DeepSeek summary with default prompt: success
- DeepSeek summary with request-level prompt override: success

## Current Behavior Expectations

- Creating a transcription task should immediately return `PENDING`
- The service offers `50` free new transcription tasks per day globally
- Only brand-new transcription tasks consume quota; reused tasks do not
- After the free quota is exhausted, new transcription creation should return a quota warning response
- Polling should move through `TRANSCRIBING` and then `SUCCESS` or `FAILED`
- Successful transcription returns:
  - `source`
  - `audio_meta`
  - `transcript.full_text`
  - `transcript.segments`
- Summary API accepts either:
  - `transcription_task_id`
  - direct `transcript`
- Summary API also accepts request-level `api_key + base_url + model_name`
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
