FROM python:3.12-slim

LABEL maintainer="Aryan Uppuganti"
LABEL description="Network Performance Analyzer & HTTP Load Testing Framework"

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpcap-dev \
    tcpdump \
    bash \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .

RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

COPY . .

RUN chmod +x run_demo.sh

EXPOSE 5000

ENTRYPOINT ["./run_demo.sh"]