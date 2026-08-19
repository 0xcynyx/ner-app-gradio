# Stage one builds the React bundle so the runtime image needs no Node.
FROM node:22-alpine AS web
WORKDIR /web
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

FROM python:3.12-slim AS runtime
ENV PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1
WORKDIR /app

# CPU wheels keep the image far smaller than the default CUDA build.
COPY backend/requirements.txt backend/requirements-model.txt ./
RUN pip install --no-cache-dir -r requirements.txt \
    && pip install --no-cache-dir --index-url https://download.pytorch.org/whl/cpu -r requirements-model.txt

COPY backend/app ./app
COPY --from=web /web/dist ./static

# Spaces routes to 7860, override with PORT anywhere else.
ENV NER_FRONTEND_DIR=static \
    HF_HOME=/tmp/huggingface \
    PORT=7860
EXPOSE 7860

# Model weights land in a writable cache so the container can run as a non root user.
RUN mkdir -p /tmp/huggingface && chmod 777 /tmp/huggingface

CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT}"]
