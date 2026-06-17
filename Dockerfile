FROM python:3.11-slim

ARG http_proxy
ARG https_proxy
ARG HTTP_PROXY
ARG HTTPS_PROXY

ENV DEBIAN_FRONTEND=noninteractive \
    PIP_NO_CACHE_DIR=1 \
    PYTHONUNBUFFERED=1 \
    RUNTIME_DIR=/runtime \
    NCNN_DIR=/opt/realesrgan \
    OUTPUT_DIR=/runtime/outputs \
    TMP_DIR=/runtime/tmp \
    HOST_BASE_URL=http://127.0.0.1:7860 \
    MODEL_NAME=realesrgan-x4plus \
    UPSCALE_OUTSCALE=4 \
    GPU_ID=0 \
    http_proxy=${http_proxy} \
    https_proxy=${https_proxy} \
    HTTP_PROXY=${HTTP_PROXY} \
    HTTPS_PROXY=${HTTPS_PROXY}

WORKDIR /srv

RUN sed -i 's|http://deb.debian.org|https://deb.debian.org|g' /etc/apt/sources.list.d/debian.sources \
  && apt-get update \
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

RUN mkdir -p /runtime /tmp/realesrgan-extract ${NCNN_DIR} \
  && curl -L https://github.com/xinntao/Real-ESRGAN/releases/download/v0.2.5.0/realesrgan-ncnn-vulkan-20220424-ubuntu.zip -o /tmp/realesrgan-ncnn-vulkan.zip \
  && unzip /tmp/realesrgan-ncnn-vulkan.zip -d /tmp/realesrgan-extract \
  && cp "$(find /tmp/realesrgan-extract -name 'realesrgan-ncnn-vulkan' -type f | head -n 1)" "${NCNN_DIR}/realesrgan-ncnn-vulkan" \
  && chmod +x "${NCNN_DIR}/realesrgan-ncnn-vulkan" \
  && cp -r "$(find /tmp/realesrgan-extract -type d -name 'models' | head -n 1)/." "${NCNN_DIR}/models" \
  && rm -rf /tmp/realesrgan-ncnn-vulkan.zip /tmp/realesrgan-extract \
  && mkdir -p ${OUTPUT_DIR} ${TMP_DIR}

COPY app.py /srv/app.py
COPY web /srv/web

EXPOSE 7860

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "7860"]
