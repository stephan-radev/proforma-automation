FROM python:3.12-slim

RUN apt-get update && \
    apt-get install -y \
        build-essential \
        libffi-dev \
        libcairo2 \
        libpango-1.0-0 \
        libpangocairo-1.0-0 \
        libpangoft2-1.0-0 \
        libgdk-pixbuf2.0-0 \
        libglib2.0-0 \
        libxml2 \
        libxslt1.1 \
        libjpeg62-turbo \
        libssl-dev \
        python3-cffi \
        fonts-liberation \
        fonts-dejavu-core \
        poppler-utils \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt ./
RUN pip install --upgrade pip && pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["python", "app.py"]

