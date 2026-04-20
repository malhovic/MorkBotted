FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DATA_DIR=/app/data \
    DB_PATH=/app/data/morkbotted.db

WORKDIR /app

RUN groupadd --system morkbotted \
    && useradd --system --gid morkbotted --home-dir /app --shell /usr/sbin/nologin morkbotted

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY bot.py ./bot.py
COPY morkbotted ./morkbotted

RUN mkdir -p /app/data \
    && chown -R morkbotted:morkbotted /app

USER morkbotted

VOLUME ["/app/data"]

CMD ["python", "bot.py"]
