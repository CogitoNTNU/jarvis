# Use an official Python runtime as a parent image
FROM python:3.10-bookworm

# Set the working directory in the container
WORKDIR /app

# Copy only requrirements to keep cache.
COPY requirements.txt requirements.txt

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy the current directory contents into the container at /app
COPY . .

# Run app.py when the container launches
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "3000", "--reload", "--log-level", "trace"]
#CMD ["gunicorn", "--worker-class", "eventlet", "-w", "1", "-b", "0.0.0.0:8000", "app:app"]