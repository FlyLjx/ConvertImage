FROM python:3.11-slim

ENV DEBIAN_FRONTEND=noninteractive \
    PIP_NO_CACHE_DIR=1 \
    PYTHONUNBUFFERED=1 \
    RUNTIME_DIR=/runtime \
    NCNN_DIR=/runtime/realesrgan-ncnn-vulkan \
    OUTPUT_DIR=/runtime/outputs \
    TMP_DIR=/runtime/tmp \
    HOST_BASE_URL=http://127.0.0.1:7860 \
    MODEL_NAME=realesrgan-x4plus \
    UPSCALE_OUTSCALE=4 \
    GPU_ID=0

WORKDIR /srv

RUN apt-get update \
  && apt-get install -y --no-install-recommends \
    curl \
    unzip \
    libvulkan1 \
    mesa-vulkan-drivers \
    vulkan-tools \
  && rm -rf /var/lib/apt/lists/*

COPY requirements.txt /srv/requirements.txt
RUN pip install --upgrade pip \
  && pip install -r /srv/requirements.txt

RUN mkdir -p /runtime \
  && curl -L https://github.com/xinntao/Real-ESRGAN/releases/download/v0.2.5.0/realesrgan-ncnn-vulkan-20220424-ubuntu.zip -o /tmp/realesrgan-ncnn-vulkan.zip \
  && unzip /tmp/realesrgan-ncnn-vulkan.zip -d /runtime/realesrgan-ncnn-vulkan \
  && rm -f /tmp/realesrgan-ncnn-vulkan.zip \
  && mkdir -p ${OUTPUT_DIR} ${TMP_DIR}

COPY app.py /srv/app.py
COPY web /srv/web

EXPOSE 7860

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "7860"]
