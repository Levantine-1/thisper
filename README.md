# THISPER
Telephone + Whisper = Thisper

Thisper started as a Python-flask bridge for triggering and monitoring Jenkins jobs from GitHub Actions, without exposing Jenkins itself to the internet. Jenkins has since been decommissioned — CI/CD now goes through a self-hosted GitHub Actions runner talking directly to Semaphore inside the homelab network, and that bridge code has been removed.

**Thisper is still needed, just for a different reason now.** It's the public-facing proxy in front of DataGateway's `/analytics` endpoint: `portfolio`'s pages call `https://thisper.levantine.io/analytics` directly from visitors' browsers on every page load and tracked link click. DataGateway itself only has an internal NodePort endpoint and needs a server-side API key to write to — neither of which a browser can talk to directly — so thisper is what makes that path public and keeps the key off the client.

## Functionality

- `POST /analytics` — forwards analytics events (page path, user agent, IP) from public browsers to DataGateway's `/analytics`, injecting the server-side API key.
- `GET /.well-known/acme-challenge/<token>` — ACME HTTP-01 challenge responder for TLS cert issuance.
- `GET /` — liveness/documentation response.

## Deployment

The application is deployed using GitHub Actions, as defined in the `.github/workflows/deploy.yml` file. The deployment process involves applying Terraform templates, building and pushing a Docker container to Amazon ECR, and triggering the deploy via Semaphore.

## Development

The application is developed in Python and uses pip for package management. It can be run locally using the command `python thisper.py`, and it will be available at `http://0.0.0.0:5000`.

