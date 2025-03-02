# Use the official Python 13.3 image based on Alpine as a base image
FROM python:3.13-alpine

# Install the required packages
RUN apk update && apk add --no-cache postgresql-dev gcc python3-dev musl-dev

# Copy the requirements file into the container
COPY requirements.txt .

# Install the required Python packages
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code into the container, including subfolders
COPY . .

# Make app.py executable 
RUN chmod +x /Flask_app/app.py

# Set the command to run the Flask app
CMD ["python", "/Flask_app/app.py"]
