FROM python:3.9-buster

# Install system dependencies needed for numpy, pandas, lightgbm
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip setuptools wheel \
    && pip install --no-cache-dir --default-timeout=100 -r requirements.txt

COPY . .

RUN chmod +x start.sh

EXPOSE 8501

CMD ["./start.sh"]
