FROM python:3.9

# Sets the working directory in the container
WORKDIR /app

# Copies the application files into the container
COPY . .

# Then we install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Expose port 5000 for the Flask app
EXPOSE 5000

# Define environment variable
ENV FLASK_APP=app.py

# Run the Flask application
CMD ["python3", "app.py"]
