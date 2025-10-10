# Base image
FROM python:3.12-slim

# Prevents Python from writing .pyc files
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Set work directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    libpq-dev gcc \
    && rm -rf /var/lib/apt/lists/*

# Install system dependencies
# RUN apt-get update && apt-get install -y \
#     build-essential \
#     libpq-dev \
#     && rm -rf /var/lib/apt/lists/*

# Install dependencies
# COPY requirements.txt .
# Install Python dependencies
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt


# Copy Django project
# COPY . .
COPY . /app/

#  will remove
# COPY .env .env  

# Make sure the directory exists before collectstatic
RUN mkdir -p /app/staticfiles

# Collect static files (optional, uncomment if applicable)
RUN python manage.py collectstatic --noinput

# Expose port 8000
EXPOSE 8000

# Use gunicorn as production server
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "trekknbackend.wsgi:application"]
