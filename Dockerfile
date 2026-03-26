FROM python:3.11-slim

# Create a non-root user (Hugging Face requirement)
RUN useradd -m -u 1000 user
USER user
ENV PATH="/home/user/.local/bin:$PATH"

WORKDIR /app

# Copy requirements and install
COPY --chown=user ./requirements.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy all files to the container with correct permissions
COPY --chown=user . /app

# Hugging Face Spaces routes external traffic to port 7860
ENV PORT=7860

# Start the application with Gunicorn
CMD ["gunicorn", "-b", "0.0.0.0:7860", "app:app"]
