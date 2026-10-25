# Conformance example app (Flask). Build with the package folder as the context:
#   docker build -f example/Dockerfile .
FROM python:3.13-slim
ENV PIP_DISABLE_PIP_VERSION_CHECK=1 PIP_ROOT_USER_ACTION=ignore PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
COPY example/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
# The package from this repo's own source, not from PyPI.
COPY pyproject.toml README.md LICENSE CHANGELOG.md /pkg/
COPY src/ /pkg/src/
RUN pip install --no-cache-dir /pkg
COPY example/ .
EXPOSE 8080
CMD ["sh", "-c", "exec gunicorn --bind 0.0.0.0:${PORT:-8080} --workers 2 --worker-class gthread --threads 4 --access-logfile - app:application"]
