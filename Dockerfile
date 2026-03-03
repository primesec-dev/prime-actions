FROM python:3.13-slim

LABEL maintainer="prime-actions"
LABEL description="PR Password Scanner GitHub Action"

COPY pyproject.toml /action/
COPY src/ /action/src/
COPY entrypoint.py /action/

RUN pip install --no-cache-dir /action/

ENTRYPOINT ["python", "/action/entrypoint.py"]
