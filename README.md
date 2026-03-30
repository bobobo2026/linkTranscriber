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

### 按请求覆盖 prompt

```bash
curl -X POST http://127.0.0.1:8483/api/service/summaries \
  -H 'Content-Type: application/json' \
  -d '{
    "transcription_task_id": "uuid",
    "provider_id": "deepseek",
    "model_name": "deepseek-chat",
    "prompt": "请基于下方文本只输出一句话总结，不要标题。\\n\\n{transcript}"
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

## 后续规划

- 支持小红书链接
- 支持图文内容抽取
- 支持一个接口同时完成“转写 + 总结”的组合编排
- 支持把 prompt 管理独立出来

## License

MIT
