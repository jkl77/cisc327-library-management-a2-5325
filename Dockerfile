# Use a Python base image
FROM python:3.11-slim

# Set the working directory inside the container
WORKDIR /app

# Copy the requirements file
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code
COPY . .

# Expose port 5000 so we can access the app from the browser
EXPOSE 5000

# Command to run the application
CMD ["flask", "run", "--host=0.0.0.0"]