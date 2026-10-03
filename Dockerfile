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

# Default port is 7860 (Hugging Face Spaces). Platforms like Railway/Render
# inject their own PORT variable, which overrides this default.
ENV PORT=7860
EXPOSE 7860

# Start the application with Gunicorn (shell form so $PORT is expanded).
# --timeout 120: the first request loads the dataset and vectors into memory.
CMD gunicorn -b 0.0.0.0:${PORT} --workers 1 --threads 4 --timeout 120 app:app
