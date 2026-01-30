# syntax=docker/dockerfile:1

# BookBagOfHolding Docker Image with Calibre Support
# Based on linuxserver.io patterns
#
# Layer ordering optimized for fast rebuilds:
# 1. Base image + binaries from other stages (rarely changes)
# 2. System packages (rarely changes)
# 3. Python venv + pip packages (occasionally changes)
# 4. S6-overlay config (occasionally changes)
# 5. Application source code (frequently changes)

# -----------------------------------------------------------------------------
# Stage 1: Get unrar binary
# -----------------------------------------------------------------------------
FROM ghcr.io/linuxserver/unrar:latest AS unrar

# -----------------------------------------------------------------------------
# Stage 2: Download Calibre binaries
# -----------------------------------------------------------------------------
FROM ghcr.io/linuxserver/baseimage-ubuntu:noble AS calibre-builder

ARG TARGETPLATFORM

RUN \
  echo "**** install build dependencies ****" && \
  apt-get update && \
  apt-get install -y --no-install-recommends \
    curl \
    jq \
    xz-utils && \
  echo "**** download calibre ****" && \
  CALIBRE_VERSION=$(curl -sL "https://api.github.com/repos/kovidgoyal/calibre/releases/latest" | jq -r '.tag_name' | sed 's/^v//') && \
  echo "Downloading Calibre version: ${CALIBRE_VERSION}" && \
  if [ "${TARGETPLATFORM}" = "linux/amd64" ]; then \
    CALIBRE_ARCH="x86_64"; \
  elif [ "${TARGETPLATFORM}" = "linux/arm64" ]; then \
    CALIBRE_ARCH="arm64"; \
  else \
    CALIBRE_ARCH="x86_64"; \
  fi && \
  echo "Architecture: ${CALIBRE_ARCH}" && \
  curl -fL "https://download.calibre-ebook.com/${CALIBRE_VERSION}/calibre-${CALIBRE_VERSION}-${CALIBRE_ARCH}.txz" -o /tmp/calibre.txz && \
  mkdir -p /calibre && \
  tar xJf /tmp/calibre.txz -C /calibre && \
  rm /tmp/calibre.txz

# -----------------------------------------------------------------------------
# Stage 3: Main image
# -----------------------------------------------------------------------------
FROM ghcr.io/linuxserver/baseimage-ubuntu:noble

# Build arguments
ARG BUILD_DATE
ARG VERSION

# Labels following OCI spec
LABEL build_version="BookBagOfHolding version: ${VERSION} Build-date: ${BUILD_DATE}"
LABEL maintainer="BookBagOfHolding"
LABEL org.opencontainers.image.title="BookBagOfHolding"
LABEL org.opencontainers.image.description="BookBagOfHolding with built-in Calibre support"
LABEL org.opencontainers.image.url="https://github.com/sd0408/BookBagOfHolding"
LABEL org.opencontainers.image.source="https://github.com/sd0408/BookBagOfHolding"
LABEL org.opencontainers.image.licenses="GPL-3.0"

# -----------------------------------------------------------------------------
# Layer 1: Copy binaries from build stages (cached unless base images change)
# -----------------------------------------------------------------------------
COPY --from=unrar /usr/bin/unrar-ubuntu /usr/bin/unrar
COPY --from=calibre-builder /calibre /opt/calibre

# Add Calibre to PATH
ENV PATH="/opt/calibre:${PATH}"

# -----------------------------------------------------------------------------
# Layer 2: Install system packages (cached unless package list changes)
# -----------------------------------------------------------------------------
RUN \
  echo "**** install runtime packages ****" && \
  apt-get update && \
  apt-get install -y --no-install-recommends \
    # BookBagOfHolding dependencies
    ghostscript \
    libjpeg-turbo8 \
    libmagic1 \
    libunrar5 \
    python3-venv \
    zlib1g \
    # Calibre runtime dependencies
    libgl1 \
    libnss3 \
    libxcomposite1 \
    libxdamage1 \
    libxrandr2 \
    libxtst6 \
    libxkbcommon0 \
    libegl1 \
    libxkbcommon-x11-0 \
    libxcb-cursor0 \
    libxcb-icccm4 \
    libxcb-image0 \
    libxcb-keysyms1 \
    libxcb-randr0 \
    libxcb-render-util0 \
    libxcb-shape0 \
    xdg-utils \
    # Networking for healthcheck
    curl \
    netcat-openbsd && \
  echo "**** cleanup apt ****" && \
  apt-get clean && \
  rm -rf /var/lib/apt/lists/* /var/tmp/*

# -----------------------------------------------------------------------------
# Layer 3: Python virtual environment (cached unless requirements change)
# -----------------------------------------------------------------------------
RUN \
  echo "**** create python virtual environment ****" && \
  python3 -m venv /lsiopy && \
  /lsiopy/bin/pip install --no-cache-dir -U pip wheel && \
  echo "**** install python packages ****" && \
  /lsiopy/bin/pip install --no-cache-dir \
    cherrypy \
    mako \
    requests \
    httplib2 \
    beautifulsoup4 \
    feedparser \
    fuzzywuzzy \
    python-Levenshtein \
    'bencode.py' \
    urllib3 \
    pyopenssl

# -----------------------------------------------------------------------------
# Layer 4: S6-overlay service configuration (cached unless config changes)
# -----------------------------------------------------------------------------
COPY docker/root/ /

# -----------------------------------------------------------------------------
# Layer 5: Application source code (rebuilt on every code change)
# -----------------------------------------------------------------------------
COPY --chown=abc:abc bookbagofholding/ /app/bookbagofholding/bookbagofholding/
COPY --chown=abc:abc vendor/ /app/bookbagofholding/vendor/
COPY --chown=abc:abc Bookbag of Holding.py /app/bookbagofholding/
COPY --chown=abc:abc data/ /app/bookbagofholding/data/
COPY --chown=abc:abc init/ /app/bookbagofholding/init/
COPY --chown=abc:abc examples/ /app/bookbagofholding/examples/

# Exposed port
EXPOSE 5299

# Volume for configuration
VOLUME /config

# Healthcheck
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
  CMD curl -f http://localhost:5299/ || exit 1
