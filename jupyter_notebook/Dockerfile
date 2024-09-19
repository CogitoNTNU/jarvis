# Use an official Python image as the base
FROM python:3.11
# Set the working directory in the container
WORKDIR /workspace
# Install system dependencies
RUN apt-get update && apt-get install -y \
    git \
    && rm -rf /var/lib/apt/lists/*
# Install Python dependencies
COPY requirements.txt .
RUN pip install --upgrade pip
RUN pip install -r requirements.txt
# Install Jupyter Notebook
RUN pip install jupyterlab
# Expose the Jupyter notebook port
EXPOSE 8888