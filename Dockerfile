FROM python:3.13-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Startet als root, damit start.sh alte root-eigene Volumes übernimmt, dann setpriv.
RUN useradd --system --uid 1000 --user-group --no-create-home --shell /usr/sbin/nologin sgrm

RUN mkdir -p /app/config /app/data /app/templates /app/static \
    && chown sgrm:sgrm /app/config /app/data

COPY *.py /app/
COPY templates/* /app/templates/
COPY static/* /app/static/

ENV PYTHONUNBUFFERED=1

EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8080/health', timeout=4)"

COPY start.sh /app/
RUN chmod +x /app/start.sh

CMD ["/app/start.sh"]