# Use an official Python runtime as a parent image
FROM python:3.9-slim-buster

# Set the working directory to /app
WORKDIR /app

# Copy the requirements file to the working directory
COPY requirements.txt .

# Install the dependencies
RUN pip install --no-cache-dir -r requirements.txt

# 2023-11-26 Pending Deprecation if PF Sense DNS resolver works
# RUN echo "192.168.1.20 jenkins.levantine.io" >> /etc/hosts

# Copy the current directory contents into the container at /app
COPY . .

# Expose port 5000
EXPOSE 5000

# Run the command to start the app
# CMD ["python", "thisper.py"]
CMD ["gunicorn", "thisper:app", "-b", "0.0.0.0:5000"]