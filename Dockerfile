# Use the official Python 13.3 image based on Ubuntu as a base image
FROM python:3.13.3-ubuntu

# Set the working directory
WORKDIR /app

# Copy the requirements file into the container
COPY requirements.txt .

# Install the required Python packages
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code into the container, including subfolders
COPY . .

# Set the command to run the Flask app
CMD ["python", "/Flask_app/app.py"]
