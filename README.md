# Real-ESRGAN GPU 超分服务

这是一个独立于 `AI生图-AIπ` 的超分服务，基于 `Real-ESRGAN-ncnn-vulkan`。

接口：

- `GET /health`
- `GET /v1/models`
- `POST /v1/images/upscale`
- `POST /v1/images/upscale/upload`
- `GET /test`

## Docker

```bash
docker compose up -d --build
```

## 测试页

打开：

```text
http://127.0.0.1:7860/test
```

## GitHub Actions

仓库内已配置 `.github/workflows/docker.yml`，推送到 `main` 会自动做 Docker build 检查。

## 说明

- Windows 仍可用 `start.ps1` 测试
- GPU 默认走 `GPU_ID=0`
- 需要切核显/独显时，改测试页里的 `GPU ID`
