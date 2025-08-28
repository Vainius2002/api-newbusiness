# Use an official Python runtime as a parent image
FROM python:3.12-slim

# Set the working directory
WORKDIR /app

# Copy project files into the container
COPY . /app

# Install dependencies if you have a requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Expose the port your app will run on
EXPOSE 5001

# Command to run your app
CMD ["python", "run.py"]
