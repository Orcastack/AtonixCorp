FROM python:3.10-slim

# Set work directory
WORKDIR /app

# Install Python dependencies
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy project code
COPY . .

# Environment variables
ENV PYTHONUNBUFFERED=1 \
    DJANGO_SETTINGS_MODULE=atonixcorp_api.settings \
    PORT=8000

# Expose port
EXPOSE 8000

# Run Django development server (suitable for local dev; use gunicorn for prod)
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
