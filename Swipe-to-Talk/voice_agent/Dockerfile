# Voice agent image — build from this directory:
#   docker build -t voice-agent ./voice_agent
FROM python:3.12-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg libopus0 libvpx7 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY agent.py .

ENV PYTHONUNBUFFERED=1
ENV VOICE_BOT_PORT=7860
EXPOSE 7860

CMD ["python", "agent.py"]
