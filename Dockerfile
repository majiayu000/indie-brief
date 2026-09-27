FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim

WORKDIR /app
COPY pyproject.toml uv.lock README.md LICENSE ./
COPY src ./src
RUN uv sync --frozen --no-dev
COPY plugin ./plugin
COPY template ./template

EXPOSE 8787
ENV INDIE_BRIEF_DATA_DIR=/data
ENV INDIE_BRIEF_HOST=0.0.0.0
CMD ["uv", "run", "--no-dev", "indie-brief", "serve", "--host", "0.0.0.0", "--port", "8787"]
