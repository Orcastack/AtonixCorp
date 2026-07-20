# Apache2 Reverse Proxy Deployment

These two host Apache virtual hosts serve the running Docker containers without exposing their ports to the public network:

- `atonixcorp-frontend.conf`: `atonixcorp.com` and `www.atonixcorp.com` to `127.0.0.1:3000`.
- `atonixcorp-api.conf`: `api.atonixcorp.com` to `127.0.0.1:8000`.

## Compose-Managed Apache

`docker-compose.yml` now starts an `atonixcorp-apache` container automatically with the frontend and API. It publishes ports `80` and `443`, proxies to the internal `app` and `api` services, and mounts Let’s Encrypt certificates read-only from `${APACHE_CERTS_DIR:-/etc/letsencrypt}`.

When all four certificate files are present, Apache serves the TLS virtual hosts and redirects HTTP to HTTPS. If certificates are absent, the container stays available through an HTTP-only fallback and logs the condition instead of restarting. This fallback is for initial DNS/certificate setup only; do not treat it as a production HTTPS configuration.

Do not run the host Apache service and the Compose Apache container on the same ports. For the Compose-managed proxy:

```bash
sudo systemctl disable --now apache2
sudo docker compose up -d --build
sudo docker compose ps
```

The certificate directories below must exist before `atonixcorp-apache` starts. Set `APACHE_CERTS_DIR` in the shell or `.env` when certificates are stored elsewhere.

Before requesting certificates, confirm `atonixcorp.com`, `www.atonixcorp.com`, and `api.atonixcorp.com` each resolve to this server's public IP. The HTTP-01 challenge cannot succeed while DNS points at another host.

## Host Apache Alternative

Point the three DNS records at this server, then issue the certificates before enabling the HTTPS virtual hosts:

```bash
sudo certbot certonly --standalone -d atonixcorp.com -d www.atonixcorp.com
sudo certbot certonly --standalone -d api.atonixcorp.com
```

Copy the files and enable the Apache modules/sites:

```bash
sudo cp deploy/apache2/atonixcorp-frontend.conf /etc/apache2/sites-available/
sudo cp deploy/apache2/atonixcorp-api.conf /etc/apache2/sites-available/
sudo a2enmod proxy proxy_http proxy_wstunnel rewrite headers ssl
sudo a2ensite atonixcorp-frontend atonixcorp-api
sudo apache2ctl configtest
sudo systemctl reload apache2
```

Restart the Docker stack after the loopback-only port change:

```bash
sudo docker compose up -d --build
```

Confirm the public paths and internal upstreams:

```bash
curl -I https://atonixcorp.com/
curl -I https://api.atonixcorp.com/api/health/
curl -I http://127.0.0.1:3000/
curl -I http://127.0.0.1:8000/api/health/
```

Renewal uses the existing Certbot renewal timer. Reload Apache after certificate renewal with a Certbot deploy hook.