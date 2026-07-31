# Dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Erstelle Verzeichnisse
RUN mkdir -p /app/config /app/data /app/templates /app/static

# Kopiere Anwendungsdateien
COPY *.py /app/
COPY templates/* /app/templates/
COPY static/* /app/static/

# Setze Umgebungsvariablen
ENV PYTHONUNBUFFERED=1

# Öffne Ports
EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8080/health', timeout=4)"

# Start-Skript
COPY start.sh /app/
RUN chmod +x /app/start.sh

CMD ["/app/start.sh"]