FROM python:3.12-slim

WORKDIR /app

# Системные зависимости для lxml
RUN apt-get update && apt-get install -y \
    libxml2-dev libxslt1-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Создаём volume для базы данных
VOLUME ["/app/data"]
ENV DB_PATH=/app/data/news.db

CMD ["python", "main.py"]
