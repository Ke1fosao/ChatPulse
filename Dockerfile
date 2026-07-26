FROM node:22-slim AS miniapp-builder

WORKDIR /build/miniapp
COPY miniapp/package.json miniapp/package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY miniapp ./
RUN npm run build

FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    MINIAPP_DIST_DIR=/app/miniapp_dist

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml README.md VERSION alembic.ini requirements.lock ./
COPY migrations ./migrations
COPY app ./app
COPY --from=miniapp-builder /build/miniapp/dist ./miniapp_dist

RUN pip install --upgrade pip \
    && pip install --constraint requirements.lock . \
    && useradd --create-home --uid 10001 chatpulse \
    && chown -R chatpulse:chatpulse /app

USER chatpulse
EXPOSE 8080
CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:create_app --factory --host 0.0.0.0 --port ${PORT:-8080}"]
