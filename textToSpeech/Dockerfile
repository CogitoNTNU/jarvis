FROM williammrs/cuda-python3.12
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY app /app
CMD ["python", "/app/app.py"]