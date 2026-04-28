# Smart Face Attendance — Streamlit + DeepFace + optional YOLO-World (mask check)
FROM python:3.9-slim

# OpenCV headless + TF/DeepFace commonly need these on Debian slim
ENV TF_USE_LEGACY_KERAS=1 \
    PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    libgl1 \
    libglib2.0-0 \
    libgomp1 \
    libsm6 \
    libxext6 \
    libxrender1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8501

# Bind to all interfaces so the port is reachable from the host
CMD ["streamlit", "run", "main.py", "--server.address=0.0.0.0", "--server.port=8501"]
