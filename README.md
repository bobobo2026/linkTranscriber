# linkTranscriber

<p><i>把抖音等链接转换成文本与大模型总结的服务化后端</i></p>

<p>
  <img src="https://img.shields.io/badge/license-MIT-blue.svg" />
  <img src="https://img.shields.io/badge/backend-fastapi-green" />
  <img src="https://img.shields.io/badge/transcript-douyin%20v1-orange" />
  <img src="https://img.shields.io/badge/summary-deepseek%20%7C%20openai-blue" />
  <img src="https://img.shields.io/badge/status-active-success" />
</p>

## 项目定位

`linkTranscriber` 是一个面向服务调用场景的链接转文本后端。当前最小闭环聚焦在：

- 抖音短链/长链解析
- 视频音频下载
- 语音转文本
- 基于大模型的文本总结
- API 调用时按请求覆盖提示词

这个项目不是从零重写，而是**基于 BiliNote 的既有下载、转写和模型能力做的服务化迭代**。当前版本优先保留 BiliNote 里已经稳定可用的能力，再把 GUI 场景收敛成纯 API 交付。

## 当前能力

- `POST /api/service/transcriptions`
- `GET /api/service/transcriptions/{task_id}`
- `POST /api/service/summaries`

V1 边界：

- 平台目前只支持 `douyin`
- 内容类型目前只支持 `video`
- 总结接口支持请求级 `prompt`
- 总结模型支持走已配置 provider，例如 `DeepSeek`

## 来源说明

本项目来源于 [BiliNote](https://github.com/JefferyHcool/BiliNote) 的服务化迭代版本。

保留并复用了这些核心能力：

- 抖音下载器
- 转写器配置与转写实现
- OpenAI 兼容模型 provider 体系
- 原有后端基础设施与任务执行链路

本仓库新增的重点是：

- 无 GUI 的服务 API
- 独立的转写任务持久化
- 面向服务调用的总结接口
- 默认 prompt 与请求级 prompt 覆盖机制

## 快速开始

### 1. 克隆仓库

```bash
git clone https://github.com/bobobo2026/linkTranscriber.git
cd linkTranscriber
cp .env.example .env
```

### 2. 启动后端

```bash
cd backend
pip install -r requirements.txt
python main.py
```

默认服务地址：

```text
http://127.0.0.1:8483
```

### 3. 安装依赖

项目依赖 `ffmpeg` 做音频处理与转码：

```bash
# macOS
brew install ffmpeg

# Ubuntu / Debian
sudo apt install ffmpeg
```

## 服务 API

自动生成的 API 文档建议优先看以下入口：

- 本地开发态：
  - `http://127.0.0.1:8483/docs`
  - `http://127.0.0.1:8483/redoc`
  - `http://127.0.0.1:8483/openapi.json`
- GitHub Pages：
  - 由 `.github/workflows/deploy-api-docs.yml` 自动发布
  - 首次启用后可在仓库 `Settings -> Pages` 中看到最终 URL

如果需要手动本地生成静态文档站：

```bash
bash scripts/build-api-docs.sh
```

生成结果位于 `site/index.html`。

### 创建转写任务

```bash
curl -X POST http://127.0.0.1:8483/api/service/transcriptions \
  -H 'Content-Type: application/json' \
  -d '{
    "url": "https://v.douyin.com/xxxxx/",
    "platform": "douyin",
    "cookie": "your_douyin_cookie"
  }'
```

响应示例：

```json
{
  "code": 0,
  "msg": "success",
  "data": {
    "task_id": "uuid",
    "status": "PENDING"
  }
}
```

### 查询转写结果

```bash
curl http://127.0.0.1:8483/api/service/transcriptions/<task_id>
```

成功后返回：

- 原始链接和平台信息
- 视频基础元信息
- 完整文本 `transcript.full_text`
- 分段文本 `transcript.segments`

免费额度说明：

- 服务端每天提供 `50` 次免费新转写额度
- 只有“新建转写任务”会扣减额度
- 命中历史复用 `reused=true` 不扣减
- 超额后会返回提示，要求调用方改用自有 API Key 继续做总结

### 配置 DeepSeek

```bash
curl -X POST http://127.0.0.1:8483/api/update_provider \
  -H 'Content-Type: application/json' \
  -d '{
    "id": "deepseek",
    "name": "DeepSeek",
    "api_key": "your_deepseek_api_key",
    "base_url": "https://api.deepseek.com",
    "type": "built-in",
    "enabled": 1
  }'
```

### 调用总结接口

```bash
curl -X POST http://127.0.0.1:8483/api/service/summaries \
  -H 'Content-Type: application/json' \
  -d '{
    "transcription_task_id": "uuid",
    "provider_id": "deepseek",
    "model_name": "deepseek-chat"
  }'
```

### 使用自有 API Key 调用总结接口

```bash
curl -X POST http://127.0.0.1:8483/api/service/summaries \
  -H 'Content-Type: application/json' \
  -d '{
    "transcription_task_id": "uuid",
    "api_key": "sk-xxx",
    "base_url": "https://api.deepseek.com",
    "model_name": "deepseek-chat"
  }'
```

默认情况下，这个接口会返回固定结构的结果：

```text
一句话总结：...

TodoList：
1. 事项：...
执行时间：...
提醒时间：...
说明：...
```

### 按请求覆盖 prompt

```bash
curl -X POST http://127.0.0.1:8483/api/service/summaries \
  -H 'Content-Type: application/json' \
  -d '{
    "transcription_task_id": "uuid",
    "provider_id": "deepseek",
    "model_name": "deepseek-chat",
    "prompt": "总结归纳，提取可执行的todolist（最多4点，最好可以锁定时间线）。每条必须包含：事项、执行时间、提醒时间、说明。\\n\\n{transcript}"
  }'
```

响应示例：

```json
{
  "code": 0,
  "msg": "success",
  "data": {
    "summary_markdown": "总结内容",
    "prompt_source": "default"
  }
}
```

如果免费转写额度已满，创建新任务会返回：

```json
{
  "code": 40301,
  "msg": "今日免费转写额度已用完，请明天再试，或使用自有 API Key 调用总结接口。",
  "data": {
    "quota_limit": 50,
    "quota_used": 50,
    "reset_at": "2026-04-01 00:00:00",
    "next_action": "使用自有 API Key 调用 summaries，或明天再试"
  }
}
```

## 部署到服务器

这个仓库已经内置了一套不依赖 Docker 的 GitHub Actions + systemd 发布链路，适合把 `linkTranscriber` 作为常驻后端服务部署到 Linux 服务器。

### 部署方式

- GitHub Actions 负责把代码同步到服务器
- 服务器上的 `scripts/deploy-server.sh` 负责创建虚拟环境、安装依赖、生成 systemd 服务并重启
- 服务默认以 `uvicorn` 方式运行
- 反向代理建议使用 Nginx

相关文件：

- `.github/workflows/deploy-server.yml`
- `scripts/deploy-server.sh`
- `scripts/configure-runtime.sh`
- `deploy/systemd/linktranscriber-api.service.template`
- `deploy/nginx/linktranscriber-api.location.conf`
- `backend/requirements-service.txt`

### GitHub Secrets

如果你要启用自动部署，需要在 GitHub 仓库里配置这些 secrets：

- `DEPLOY_HOST`
- `DEPLOY_USER`
- `DEPLOY_SSH_KEY`

### 服务器约定

默认脚本按下面这组约定部署：

- 应用目录：`/opt/linktranscriber-api`
- systemd 服务名：`linktranscriber-api`
- 服务端口：`18001`
- Python：`/opt/miniconda3/bin/python`

如果你的服务器路径不同，可以在 workflow 的 SSH 命令里改环境变量：

```bash
APP_DIR=/opt/linktranscriber-api \
SERVICE_NAME=linktranscriber-api \
PORT=18001 \
PYTHON_BIN=/opt/miniconda3/bin/python \
bash /opt/linktranscriber-api/scripts/deploy-server.sh
```

### 运行时配置

服务器首次部署时会自动生成 `.env.production`，并补齐最小必需项。

常用运行时配置包括：

- `BACKEND_HOST`
- `BACKEND_PORT`
- `TRANSCRIBER_TYPE`
- `WHISPER_MODEL_SIZE`
- `DEEPSEEK_API_KEY`

抖音 Cookie 不建议直接写进 shell `source` 的 `.env.production`，更稳妥的做法是通过接口写入下载器配置，或者单独写入 `config/downloader.json`。

### 首次部署后建议

部署成功后建议立刻做这三步验证：

1. 检查你实际部署环境中的健康接口：`GET /api/sys_check`
2. 提交一个真实抖音链接到 `POST /api/service/transcriptions`
3. 用 `POST /api/service/summaries` 验证 DeepSeek 总结链路

## 本地开发建议

这个仓库最初来自 `BiliNote`，如果你已经有老的本地浅克隆，建议重新 clone 一份当前公开仓库作为后续主开发目录，避免混用两套不同历史：

```bash
git clone https://github.com/bobobo2026/linkTranscriber.git
cd linkTranscriber
```

这样后续的提交、拉取和自动部署会更干净。

## 后续规划

- 支持小红书链接
- 支持图文内容抽取
- 支持一个接口同时完成“转写 + 总结”的组合编排
- 支持把 prompt 管理独立出来

## License

MIT
