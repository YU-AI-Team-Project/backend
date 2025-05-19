

FROM python:3.9-slim

WORKDIR /app

# Copy requirements files
COPY aibackend/requirements.txt ./requirements-backend.txt

# Install all dependencies
RUN pip install --no-cache-dir -r requirements-backend.txt
RUN pip install --no-cache-dir openai python-dotenv

# Copy application code
COPY aibackend ./aibackend

# Set environment variables
ENV PYTHONPATH=/app

# Expose port for the FastAPI application
EXPOSE 8080

# Cloud Run에서는 PORT 환경 변수를 사용합니다
CMD ["uvicorn", "aibackend.app.main:app", "--host", "0.0.0.0", "--port", "8080"]
 