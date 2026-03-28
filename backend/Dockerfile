FROM python:3.11-slim

WORKDIR /app

# System libs required by OpenCV headless
RUN apt-get update && apt-get install -y --no-install-recommends \
    libglib2.0-0 libgl1 libgomp1 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

# Remove any conflicting opencv builds before installing
RUN pip uninstall -y opencv-python opencv-python-headless 2>/dev/null || true \
    && pip install --no-cache-dir -r requirements.txt

COPY . .

# Pre-download U2-Net ONNX model (~170 MB) at build time.
# Cached in ~/.u2net/ so startup is instant and the first request never times out.
RUN python -c "from rembg import new_session; new_session('u2net'); print('U2-Net ready')"

EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
