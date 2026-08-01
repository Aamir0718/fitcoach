FROM python:3.11-slim

RUN useradd -m -u 1000 fitcoach

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN mkdir -p uploads && chown fitcoach:fitcoach uploads

USER fitcoach

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
