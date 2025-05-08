FROM python:3.9-slim
WORKDIR /app

# Install system dependencies for OpenCV
RUN apt-get update && apt-get install -y \
    libgl1-mesa-glx \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application code
COPY . .

# Create subdirectories for tool-specific results
RUN mkdir -p results

# Expose the port the app runs on
EXPOSE 8083

# Command to run the application
CMD ["python", "-m", "app"] 