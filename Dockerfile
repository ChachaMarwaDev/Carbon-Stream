FROM python:3.13.10-slim

# Copy uv binary
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/

WORKDIR /workspace

# Add venv to PATH
ENV PATH="/workspace/.venv/bin:$PATH"

# Copy dependency files
COPY pyproject.toml uv.lock .python-version ./

# Install dependencies
RUN uv sync --locked

# Copy ENTIRE extraction directory
COPY extraction/ ./extraction/

# Or if you want to keep the name 'extraction' in the path
# COPY extraction/ ./extraction/

# Set entry point (adjust path as needed)
ENTRYPOINT ["uv", "run", "python"]