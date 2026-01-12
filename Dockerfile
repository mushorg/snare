FROM python:3.9-alpine3.19

# ===============================
# System dependencies
# ===============================
RUN apk add --no-cache \
    git \
    build-base \
    libffi-dev \
    openssl-dev \
    curl \
    && rm -rf /root/* /tmp/* /var/tmp/* /var/cache/apk/*

# ===============================
# Python tooling
# ===============================
RUN pip install --no-cache-dir -U pip setuptools wheel

# ===============================
# Python dependencies
# ===============================
ADD requirements.txt /opt/snare/
WORKDIR /opt/snare
RUN pip install --no-cache-dir -r requirements.txt

# ===============================
# Snare source
# ===============================
ADD . /opt/snare
RUN python setup.py install

# ===============================
# Runtime user & directories
# ===============================
RUN addgroup -S snare && \
    adduser -S snare -G snare && \
    mkdir -p /opt/snare/pages /var/log/tanner && \
    chown -R snare:snare /opt/snare /var/log/tanner

# ===============================
# Copy ENTERPRISE LANDING PAGE
# ===============================
COPY pages/index.html /opt/snare/pages/index.html
RUN chown snare:snare /opt/snare/pages/index.html

USER snare

# ===============================
# Runtime environment
# ===============================
ENV PORT=80
ENV TANNER=tanner

# ===============================
# 🔑 GENERATE META + HASH (IMPORTANT)
# ===============================
# This step converts index.html → hash + meta.json
RUN snare \
    --page-dir /opt/snare/pages \
    --host-ip 127.0.0.1 \
    --port 9999 \
    --once || true

# ===============================
# Start Snare (REAL MODE)
# ===============================
CMD snare \
  --no-dorks true \
  --auto-update false \
  --host-ip 0.0.0.0 \
  --port ${PORT} \
  --page-dir /opt/snare/pages \
  --tanner ${TANNER}

