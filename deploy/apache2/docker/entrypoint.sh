#!/bin/sh
set -eu

CERT_ROOT=/usr/local/apache2/conf/letsencrypt/live
FRONTEND_CERT="$CERT_ROOT/atonixcorp.com/fullchain.pem"
FRONTEND_KEY="$CERT_ROOT/atonixcorp.com/privkey.pem"
API_CERT="$CERT_ROOT/api.atonixcorp.com/fullchain.pem"
API_KEY="$CERT_ROOT/api.atonixcorp.com/privkey.pem"

if [ -s "$FRONTEND_CERT" ] && [ -s "$FRONTEND_KEY" ] && [ -s "$API_CERT" ] && [ -s "$API_KEY" ]; then
    cp /usr/local/apache2/conf/extra/atonixcorp-vhosts-tls.conf /usr/local/apache2/conf/extra/active-vhosts.conf
    echo "AtonixCorp Apache: TLS certificates found; serving HTTPS."
else
    cp /usr/local/apache2/conf/extra/atonixcorp-vhosts-http.conf /usr/local/apache2/conf/extra/active-vhosts.conf
    echo "AtonixCorp Apache: TLS certificates unavailable; serving temporary HTTP-only fallback." >&2
fi

exec httpd-foreground
