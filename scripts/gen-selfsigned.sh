#!/bin/bash
# ── Generate self-signed TLS certificate for local development ─────
# Run this once before `docker compose up` if you're running nginx
# without Let's Encrypt.
#
# Usage: bash scripts/gen-selfsigned.sh
# ───────────────────────────────────────────────────────────────────

set -euo pipefail

SSL_DIR="$(cd "$(dirname "$0")/.." && pwd)/nginx/ssl"
mkdir -p "$SSL_DIR"

CERT_FILE="$SSL_DIR/cert.pem"
KEY_FILE="$SSL_DIR/key.pem"

if [ -f "$CERT_FILE" ] && [ -f "$KEY_FILE" ]; then
    echo "✓ Self-signed certificate already exists at $SSL_DIR"
    echo "  To regenerate, delete the files and re-run this script."
    exit 0
fi

echo "Generating self-signed TLS certificate..."
openssl req -x509 \
    -nodes \
    -days 365 \
    -newkey rsa:2048 \
    -keyout "$KEY_FILE" \
    -out "$CERT_FILE" \
    -subj "/C=IN/ST=State/L=City/O=BB-IMS/CN=localhost" \
    -addext "subjectAltName=DNS:localhost,DNS:ims.binarybrain.edu.in"

echo "✓ Self-signed certificate generated:"
echo "  Certificate: $CERT_FILE"
echo "  Key:         $KEY_FILE"
echo ""
echo "These are self-signed and suitable ONLY for local development."
echo "For production, set USE_LETSENCRYPT=true in .env and run certbot."
