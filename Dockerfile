   # Use official Python slim image to reduce memory usage
   FROM python:3.9-slim

   # Set working directory
   WORKDIR /app

   # Install system dependencies for dlib
   RUN apt-get update && apt-get install -y \
       build-essential \
       cmake \
       libopenblas-dev \
       liblapack-dev \
       libx11-dev \
       libgtk-3-dev \
       && rm -rf /var/lib/apt/lists/*

   # Copy application files
   COPY requirements.txt .
   COPY app.py .

   # Install Python dependencies
   RUN pip install --no-cache-dir -r requirements.txt

   # Expose port
   EXPOSE 5000

   # Run the application
   CMD ["python", "app.py"]
   