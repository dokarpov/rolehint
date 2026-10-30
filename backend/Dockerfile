FROM python:3.12-slim
WORKDIR /app
COPY backend/requirements.txt ./requirements.txt
RUN apt-get update && apt-get install -y --no-install-recommends \
    libcairo2 libpango-1.0-0 libharfbuzz0b fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*
RUN pip install --no-cache-dir -r requirements.txt
COPY backend/app ./app
COPY selfhost_setup ./selfhost_setup
COPY telegram_miniapp ./telegram_miniapp
COPY webapp ./webapp
COPY telegram_bot ./telegram_bot
COPY backend/start_railway.sh ./start_railway.sh
ENV CFA_DATA_DIR=/app/data
CMD ["uvicorn","app.main:app","--host","0.0.0.0","--port","8000"]
