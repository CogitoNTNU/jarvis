FROM python:3.12-slim
# For pyaudio
RUN apt-get update && apt-get install -y \
    gcc \
    make \
    libffi-dev \
    portaudio19-dev \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY dependencies.txt dependencies.txt
RUN pip install --no-cache-dir -r dependencies.txt

# Includes python 3.12, nvidia cuda, torch and redis python dependencies