FROM python:3.11-slim

# Set up working directory
WORKDIR /app

# Copy requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy all files to the container
COPY . .

# Hugging Face Spaces require running as a non-root user
RUN useradd -m -u 1000 user
USER user

# Hugging Face Spaces routes external traffic to port 7860
ENV PORT=7860

# Start the application with Gunicorn
CMD ["gunicorn", "-b", "0.0.0.0:7860", "app:app"]
