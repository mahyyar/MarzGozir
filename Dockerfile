FROM python:3.10-slim
WORKDIR /app

# Install MySQL client
RUN apt-get update && \
    apt-get install -y default-libmysqlclient-dev default-mysql-client && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["python", "main.py"]
