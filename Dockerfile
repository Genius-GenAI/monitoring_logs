FROM python:3.13.3-slim-bookworm

# Install Docker CLI
RUN apt-get update && apt-get install -y docker.io && apt-get clean

WORKDIR /app
COPY . .

RUN pip install --upgrade pip && pip install -r requirements.txt

CMD ["python", "log_monitor_advanced.py"]