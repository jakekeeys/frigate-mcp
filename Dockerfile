FROM python:3.13-slim

WORKDIR /app

COPY pyproject.toml .
COPY src/ src/

RUN pip install --no-cache-dir .

ENTRYPOINT ["frigate-mcp-web"]
