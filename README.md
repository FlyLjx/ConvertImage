# Real-ESRGAN GPU 超分服务

这是一个独立于 `AI生图-AIπ` 的超分服务，基于 `Real-ESRGAN-ncnn-vulkan`。

接口：

- `GET /health`
- `GET /v1/models`
- `POST /v1/images/upscale`
- `POST /v1/images/upscale/upload`
- `GET /test`

## 本地 Windows 测试

```powershell
cd E:\Users\Administrator\Desktop\代码\超分服务
powershell -ExecutionPolicy Bypass -File .\install.ps1
powershell -ExecutionPolicy Bypass -File .\start.ps1
```

## GitHub Actions

推送到 `main` 后会自动构建并推送镜像到：

```text
ghcr.io/flyljx/convertimage-realesrgan:latest
```

## 服务器部署

```bash
docker compose pull
docker compose up -d
```

## 测试页

```text
http://127.0.0.1:7860/test
```

## 说明

- 默认模型：`realesrgan-x4plus`
- 默认 GPU：`GPU_ID=0`
- 如果机器有核显和独显，可在测试页切换 `GPU ID`
