FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
COPY pyproject.toml ./
COPY constraints.txt ./
COPY src ./src
RUN pip install --no-cache-dir -c constraints.txt '.[ui]'
COPY app ./app
COPY data/manifests ./data/manifests
COPY data/evaluation ./data/evaluation
RUN useradd --create-home audit && mkdir -p data/raw && chown -R audit:audit /app
USER audit
EXPOSE 8000 8501
CMD ["uvicorn", "peru_audit.api:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000"]
