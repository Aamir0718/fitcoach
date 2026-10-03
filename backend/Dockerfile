FROM python:3.11-slim

# libgl1/libglib2.0-0 aren't in the slim base image, but ultralytics pulls in
# opencv internally — without these, `from ultralytics import YOLO` (food
# photo detection) crashes with "libGL.so.1: cannot open shared object file"
# the first time it's imported.
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

RUN useradd -m -u 1000 fitcoach

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN mkdir -p uploads && chown fitcoach:fitcoach uploads

USER fitcoach

EXPOSE 8000

# 1 worker: free-tier hosts give ~512MB RAM, and each worker loads its own
# copy of torch (via the lazy-loaded food-detection path) — 4 workers would
# multiply that 4x and OOM. Bump this once on a host with more memory.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
