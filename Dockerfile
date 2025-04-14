FROM python:3.9-slim

WORKDIR /app

# 设置pip镜像源为阿里云
RUN pip config set global.index-url https://mirrors.aliyun.com/pypi/simple/ \
    && pip config set install.trusted-host mirrors.aliyun.com

# Install dependencies
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install gunicorn

# Copy application code
COPY backend /app/backend

# Create necessary directories
RUN mkdir -p /app/backend/dictionaries
RUN mkdir -p /app/backend/uploads

# Set permissions
RUN chmod -R 755 /app/backend

EXPOSE 5002

CMD ["gunicorn", "--workers", "4", "--bind", "0.0.0.0:5002", "backend.wsgi:app"]