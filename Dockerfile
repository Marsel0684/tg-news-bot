FROM python:3.12-slim 

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# /app/data — подключи Railway Volume вручную через Settings → Volumes
# Mount path: /app/data
ENV DB_PATH=/app/data/news.db

CMD ["python", "main.py"]
