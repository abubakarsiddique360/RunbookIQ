---
id: certificate-rotation
title: Expiring TLS certificate
system: tls
summary: Verify expiry, replace the certificate, and confirm the new chain is served.
tags: [tls, certificate, expiry, https, rotation]
---

## Step 1 - Inspect the served certificate

Record issuer, subject and expiry before changing anything, so you can prove the
rotation worked.

```bash
openssl s_client -connect SERVICE_HOST:443 -servername SERVICE_HOST
```

## Step 2 - Check the certificate file on disk

Compare the file expiry with what the service actually serves; a mismatch means a
cached or unread chain.

```bash
openssl x509 -in /etc/tls/server.crt -noout -dates
```

## Step 3 - Verify the DNS name is covered

The SAN list must contain the exact hostname clients use.

```bash
openssl x509 -in /etc/tls/server.crt -noout -text
```

## Step 4 - Reload the service that terminates TLS

Reload (not restart) where the server supports it, to avoid dropping connections.

```bash
systemctl reload nginx
```

## Step 5 - Confirm clients see the new expiry

Repeat the first check and compare the Not After date with the one you recorded.

```bash
openssl s_client -connect SERVICE_HOST:443 -servername SERVICE_HOST
```
