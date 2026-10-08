FROM ghcr.io/astral-sh/uv:python3.13-bookworm-slim@sha256:531f855bda2c73cd6ef67d56b733b357cea384185b3022bd09f05e002cd144ca
COPY titvo-agent-aws/pyproject.toml titvo-agent-aws/uv.lock titvo-agent-aws/README.md /agent/
WORKDIR /agent
RUN uv sync --frozen --no-dev
COPY titvo-agent-aws/src /agent/src
COPY titvo-agent-aws/tests /agent/tests
COPY titvo-dev/tools/cli /cli
RUN uv pip install --python /agent/.venv/bin/python /cli
ENV PATH="/agent/.venv/bin:${PATH}" PYTHONPATH="/agent/src" PYTHONUNBUFFERED=1
ENTRYPOINT ["python", "-m", "titvo_cli.worker"]
