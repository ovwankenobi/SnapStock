FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY alembic.ini .
COPY alembic ./alembic
COPY app ./app
COPY docker-entrypoint.sh .

RUN useradd --create-home --uid 10001 snapstock \
    && chmod +x docker-entrypoint.sh \
    && mkdir -p uploads uploads_private \
    && chown snapstock:snapstock uploads uploads_private
USER snapstock

EXPOSE 6767

HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:6767/api/v1/health', timeout=4)"

ENTRYPOINT ["./docker-entrypoint.sh"]
