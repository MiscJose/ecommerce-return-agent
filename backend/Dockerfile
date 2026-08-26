# Base image: Python 3.12, "slim" variant strips unnecessary OS packages
# to keep the image smaller than the full python:3.12 image.
FROM python:3.12-slim

# Everything below runs from /app inside the container.
WORKDIR /app

# Copy ONLY the dependency file first. This lets Docker cache this layer -
# if your code changes but requirements.txt doesn't, Docker skips
# reinstalling everything on your next build.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Now copy the rest of your app code (this layer invalidates on any code change,
# which is fine since it's just a COPY, not a slow install step).
COPY . .

# Documents that the app listens on 8000 - doesn't actually open the port,
# that happens in docker-compose.yml or a -p flag.
EXPOSE 8000

# The actual startup command. --host 0.0.0.0 is required (not optional!) -
# without it, uvicorn only listens inside the container's own loopback
# and nothing outside the container (like Docker's port mapping) can reach it.
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]