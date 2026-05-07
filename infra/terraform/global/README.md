# Ledgora Terraform Global Conventions

This directory defines the shared conventions for the Terraform stack.

- Remote state uses an encrypted S3 backend with DynamoDB locking.
- All changes flow through CI/CD only.
- Environment roots live under `environments/dev`, `environments/staging`, and `environments/prod`.
- Reusable building blocks live under `modules/`.

Each environment root contains its own `backend.tf` and `versions.tf` so Terraform can run directly from that directory.