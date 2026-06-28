# Custom-container image for Alibaba Cloud Function Compute.
FROM python:3.11-slim

WORKDIR /app

# Node is needed for npx-launched MCP servers (email, etc.)
RUN apt-get update && apt-get install -y --no-install-recommends nodejs npm \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app

# Function Compute custom containers serve HTTP on port 9000 by default.
EXPOSE 9000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "9000"]
