FROM python:3.12-slim

# uv installs Python packages like pip does, only much faster. We copy its single binary
# from the official uv image (pinned to one version, so every build is the same).
COPY --from=ghcr.io/astral-sh/uv:0.8.14 /uv /bin/uv

WORKDIR /app

# Install the dependencies first, so Docker can reuse this layer when only the code changes.
COPY requirements.txt .
RUN uv pip install --system --no-cache -r requirements.txt

COPY *.py ./
COPY static/ static/

# Don't run the app as root inside the container.
RUN useradd --create-home appuser
USER appuser

# Print logs straight away, so they show up in Cloud Run's logs without delay.
ENV PYTHONUNBUFFERED=1
EXPOSE 8080

# gunicorn is the production web server (Flask's own server is for development only).
# Cloud Run sends requests to port 8080 by default.
CMD ["gunicorn", "--bind", "0.0.0.0:8080", "--workers", "2", "--threads", "8", "--timeout", "30", "main:app"]
