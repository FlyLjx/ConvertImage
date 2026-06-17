import base64
import os
import shutil
import subprocess
import tempfile
import uuid
from pathlib import Path
from typing import Optional

import requests
from fastapi import FastAPI, File, Form, Header, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel


APP_TITLE = "Real-ESRGAN NCNN Vulkan Service"
APP_VERSION = "1.0.1"
API_KEY = os.getenv("API_KEY", "").strip()
DEFAULT_RUNTIME_DIR = Path(os.getenv("RUNTIME_DIR", "C:/aipi-upscale")).resolve()
OUTPUT_DIR = Path(os.getenv("OUTPUT_DIR", str(DEFAULT_RUNTIME_DIR / "outputs"))).resolve()
TMP_DIR = Path(os.getenv("TMP_DIR", str(DEFAULT_RUNTIME_DIR / "tmp"))).resolve()
NCNN_DIR = Path(os.getenv("NCNN_DIR", str(DEFAULT_RUNTIME_DIR / "realesrgan-ncnn-vulkan"))).resolve()
MODEL_NAME = os.getenv("MODEL_NAME", "realesrgan-x4plus").strip() or "realesrgan-x4plus"
UPSCALE_OUTSCALE = os.getenv("UPSCALE_OUTSCALE", "4").strip() or "4"
GPU_ID = os.getenv("GPU_ID", "0").strip() or "0"
HOST_BASE_URL = os.getenv("HOST_BASE_URL", "http://127.0.0.1:7860").rstrip("/")
MAX_IMAGE_BYTES = int(os.getenv("MAX_IMAGE_BYTES", str(8 * 1024 * 1024)))
REQUEST_TIMEOUT = int(os.getenv("REQUEST_TIMEOUT", "60"))

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
TMP_DIR.mkdir(parents=True, exist_ok=True)
WEB_DIR = Path(__file__).resolve().parent / "web"

app = FastAPI(title=APP_TITLE, version=APP_VERSION)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


class UpscaleRequest(BaseModel):
    model: Optional[str] = None
    gpu_id: Optional[str] = None
    prompt: Optional[str] = None
    image_url: Optional[str] = None
    image: Optional[str] = None
    output_format: Optional[str] = "png"


def discover_ncnn_candidates() -> list[str]:
    candidates: list[str] = []
    configured = os.getenv("NCNN_EXE", "").strip()
    if configured:
        candidates.append(str(Path(configured).resolve()))
    candidates.append(str((NCNN_DIR / "realesrgan-ncnn-vulkan.exe").resolve()))
    candidates.append(str((NCNN_DIR / "realesrgan-ncnn-vulkan").resolve()))
    for match in sorted(NCNN_DIR.rglob("realesrgan-ncnn-vulkan.exe")):
        candidates.append(str(match.resolve()))
    for match in sorted(NCNN_DIR.rglob("realesrgan-ncnn-vulkan")):
        candidates.append(str(match.resolve()))
    unique: list[str] = []
    seen = set()
    for item in candidates:
        if item not in seen:
            unique.append(item)
            seen.add(item)
    return unique


def resolve_ncnn_exe() -> Path:
    for candidate in discover_ncnn_candidates():
        path = Path(candidate)
        if path.exists():
            return path
    raise HTTPException(
        status_code=500,
        detail=f"realesrgan-ncnn-vulkan not found; version={APP_VERSION}; ncnn_dir={NCNN_DIR}; candidates={discover_ncnn_candidates()}",
    )


def resolve_public_base_url(request: Request) -> str:
    forwarded_proto = (request.headers.get("x-forwarded-proto") or "").split(",")[0].strip()
    forwarded_host = (request.headers.get("x-forwarded-host") or "").split(",")[0].strip()
    forwarded_port = (request.headers.get("x-forwarded-port") or "").split(",")[0].strip()
    host = forwarded_host or request.headers.get("host") or request.url.netloc
    scheme = forwarded_proto or request.url.scheme or "http"
    if forwarded_port and host and ":" not in host:
        default_port = "443" if scheme == "https" else "80"
        if forwarded_port != default_port:
            host = f"{host}:{forwarded_port}"
    if host:
        return f"{scheme}://{host}".rstrip("/")
    return HOST_BASE_URL


def require_api_key(authorization: Optional[str]) -> None:
    if not API_KEY:
        return
    token = (authorization or "").replace("Bearer ", "").strip()
    if token != API_KEY:
        raise HTTPException(status_code=401, detail="invalid api key")


def detect_extension(content_type: str, fallback: str = ".png") -> str:
    value = (content_type or "").lower()
    if "jpeg" in value or "jpg" in value:
        return ".jpg"
    if "webp" in value:
        return ".webp"
    if "png" in value:
        return ".png"
    return fallback


def save_remote_image(image_url: str, workdir: Path) -> Path:
    response = requests.get(image_url, timeout=REQUEST_TIMEOUT)
    response.raise_for_status()
    content = response.content
    if len(content) > MAX_IMAGE_BYTES:
        raise HTTPException(status_code=400, detail="image too large")
    extension = detect_extension(response.headers.get("content-type", ""))
    path = workdir / f"source{extension}"
    path.write_bytes(content)
    return path


def save_data_url(data_url: str, workdir: Path) -> Path:
    if not data_url.startswith("data:image/"):
        raise HTTPException(status_code=400, detail="unsupported image field")
    header, encoded = data_url.split(",", 1)
    if ";base64" not in header:
        raise HTTPException(status_code=400, detail="unsupported data url")
    mime = header.split(";")[0]
    extension = detect_extension(mime)
    content = base64.b64decode(encoded)
    if len(content) > MAX_IMAGE_BYTES:
        raise HTTPException(status_code=400, detail="image too large")
    path = workdir / f"source{extension}"
    path.write_bytes(content)
    return path


def save_upload_file(upload: UploadFile, workdir: Path) -> Path:
    extension = Path(upload.filename or "source.png").suffix or detect_extension(upload.content_type or "")
    path = workdir / f"source{extension}"
    size = 0
    with path.open("wb") as target:
        while True:
            chunk = upload.file.read(1024 * 1024)
            if not chunk:
                break
            size += len(chunk)
            if size > MAX_IMAGE_BYTES:
                raise HTTPException(status_code=400, detail="image too large")
            target.write(chunk)
    return path


def resolve_input_file(
    workdir: Path,
    image_url: Optional[str],
    image: Optional[str],
    upload: Optional[UploadFile],
) -> Path:
    if upload is not None:
        return save_upload_file(upload, workdir)
    candidate = (image_url or image or "").strip()
    if not candidate:
        raise HTTPException(status_code=400, detail="image_url or image file is required")
    if candidate.startswith("data:image/"):
        return save_data_url(candidate, workdir)
    return save_remote_image(candidate, workdir)


def realesrgan_command(input_path: Path, output_dir: Path, model_name: str, gpu_id: str) -> list[str]:
    ncnn_exe = resolve_ncnn_exe()
    return [
        str(ncnn_exe),
        "-i",
        str(input_path),
        "-o",
        str(output_dir),
        "-n",
        model_name,
        "-s",
        UPSCALE_OUTSCALE,
        "-f",
        "png",
        "-g",
        gpu_id,
    ]


def find_result_file(output_dir: Path) -> Path:
    items = [item for item in output_dir.iterdir() if item.is_file()]
    if not items:
        raise HTTPException(status_code=500, detail="upscale output not found")
    items.sort(key=lambda item: item.stat().st_mtime, reverse=True)
    return items[0]


def run_upscale(input_path: Path, model_name: str, gpu_id: str) -> Path:
    request_id = uuid.uuid4().hex
    work_output_dir = TMP_DIR / f"output-{request_id}"
    work_output_dir.mkdir(parents=True, exist_ok=True)
    work_output_file = work_output_dir / f"{input_path.stem}.png"
    command = realesrgan_command(input_path, work_output_file, model_name, gpu_id)
    ncnn_exe = resolve_ncnn_exe()
    try:
        completed = subprocess.run(
            command,
            cwd=str(ncnn_exe.parent),
            capture_output=True,
            text=True,
            timeout=60 * 30,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        raise HTTPException(status_code=504, detail="upscale timeout") from exc
    if completed.returncode != 0:
        message = (completed.stderr or completed.stdout or "upscale failed").strip()
        raise HTTPException(status_code=500, detail=message[:1200])
    result = work_output_file if work_output_file.exists() else find_result_file(work_output_dir)
    final_name = f"{request_id}{result.suffix.lower() or '.png'}"
    final_path = OUTPUT_DIR / final_name
    shutil.copyfile(result, final_path)
    return final_path


@app.get("/health")
def health(request: Request):
    ncnn_candidates = discover_ncnn_candidates()
    try:
        ncnn_exe = str(resolve_ncnn_exe())
    except HTTPException:
        ncnn_exe = ""
    return {
        "status": "ok",
        "service": APP_TITLE,
        "version": APP_VERSION,
        "model": MODEL_NAME,
        "outputDir": str(OUTPUT_DIR),
        "ncnnDir": str(NCNN_DIR),
        "ncnnExe": ncnn_exe,
        "ncnnCandidates": ncnn_candidates,
        "publicBaseUrl": resolve_public_base_url(request),
    }


@app.get("/")
def root_page():
    return FileResponse(WEB_DIR / "index.html")


@app.get("/test")
def test_page():
    return FileResponse(WEB_DIR / "index.html")


@app.get("/v1/models")
def models(authorization: Optional[str] = Header(default=None)):
    require_api_key(authorization)
    return {
        "object": "list",
        "data": [
            {
                "id": MODEL_NAME,
                "object": "model",
                "owned_by": "realesrgan-cpu",
                "metadata": {
                    "capability": "image_upscale",
                    "cost_1k": 0.01,
                    "cost_2k": 0.01,
                    "cost_4k": 0.01,
                },
            }
        ],
    }


@app.get("/outputs/{filename}")
def output_file(filename: str):
    path = OUTPUT_DIR / Path(filename).name
    if not path.exists() or not path.is_file():
        raise HTTPException(status_code=404, detail="file not found")
    return FileResponse(path)


@app.post("/v1/images/upscale")
async def upscale_image(
    request: Request,
    authorization: Optional[str] = Header(default=None),
    body: Optional[UpscaleRequest] = None,
):
    require_api_key(authorization)
    body = body or UpscaleRequest()
    model_name = (body.model or MODEL_NAME).strip() or MODEL_NAME
    gpu_id = (body.gpu_id or GPU_ID).strip() or GPU_ID
    with tempfile.TemporaryDirectory(dir=str(TMP_DIR)) as temp_dir:
        workdir = Path(temp_dir)
        input_path = resolve_input_file(workdir, body.image_url, body.image, None)
        output_path = run_upscale(input_path, model_name, gpu_id)
    public_base_url = resolve_public_base_url(request)
    return JSONResponse(
        {
            "created": int(output_path.stat().st_mtime),
            "data": [{"url": f"{public_base_url}/outputs/{output_path.name}"}],
            "model": model_name,
            "gpu_id": gpu_id,
        }
    )


@app.post("/v1/images/upscale/upload")
async def upscale_image_upload(
    request: Request,
    authorization: Optional[str] = Header(default=None),
    model: str = Form(default=MODEL_NAME),
    gpu_id: str = Form(default=GPU_ID),
    prompt: str = Form(default=""),
    image: UploadFile = File(...),
):
    require_api_key(authorization)
    _ = prompt
    model_name = (model or MODEL_NAME).strip() or MODEL_NAME
    selected_gpu_id = (gpu_id or GPU_ID).strip() or GPU_ID
    with tempfile.TemporaryDirectory(dir=str(TMP_DIR)) as temp_dir:
        workdir = Path(temp_dir)
        input_path = resolve_input_file(workdir, None, None, image)
        output_path = run_upscale(input_path, model_name, selected_gpu_id)
    public_base_url = resolve_public_base_url(request)
    return {
        "created": int(output_path.stat().st_mtime),
        "data": [{"url": f"{public_base_url}/outputs/{output_path.name}"}],
        "model": model_name,
        "gpu_id": selected_gpu_id,
    }
