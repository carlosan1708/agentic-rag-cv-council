FROM python:3.11-slim

# DejaVu fonts enable Unicode PDF export
RUN apt-get update \
    && apt-get install -y --no-install-recommends fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Cloud Run injects PORT; default to 8501 for local docker use
ENV PORT=8501
EXPOSE 8501

HEALTHCHECK CMD python -c "import os, urllib.request; urllib.request.urlopen(f'http://localhost:{os.environ.get(\"PORT\", \"8501\")}/_stcore/health')"

CMD streamlit run src/app.py --server.address=0.0.0.0 --server.port=${PORT}
