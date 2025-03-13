FROM cgr.dev/ky-rafaels.example.com/python:3.11-dev AS builder

WORKDIR /app

USER root
# Install Crane
RUN apk add --no-cache crane
RUN pip3 install --no-cache-dir kubernetes --target=/app/deps

# Copy application code
COPY os-detector.py .

# Stage 2: Runtime Stage using distroless
FROM cgr.dev/ky-rafaels.example.com/python:3.11

WORKDIR /app

# Copy Python dependencies
COPY --from=builder /app/deps /app/deps

# Copy Crane binary
COPY --from=builder /usr/bin/crane /usr/bin/crane

# Copy application code
COPY --from=builder /app/os-detector.py /app/os-detector.py

# Set Python path
ENV PYTHONPATH=/app/deps

USER nonroot

ENTRYPOINT ["python"]
CMD ["/app/os-detector.py"]