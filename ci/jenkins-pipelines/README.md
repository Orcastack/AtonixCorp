# Ledgora Jenkins Pipeline Library

## Repository layout

```
ci/jenkins-pipelines/
├── Jenkinsfile.infra-validate   # Triggered by Gerrit patchset-created (infra/openstack-ledgora)
├── Jenkinsfile.infra-apply      # Triggered by Gerrit change-merged → applies to DEV
├── Jenkinsfile.infra-promote    # Manual dispatch → promotes infra to TEST / STAGE / PROD
├── Jenkinsfile.app-build        # Triggered by Gerrit patchset-created (apps/ledgora-core)
├── Jenkinsfile.app-deploy       # Manual dispatch or change-merged → deploys app to any env
├── vars/
│   ├── gerrit.groovy            # Shared: post Verified votes and comments to Gerrit
│   └── openstack.groovy         # Shared: terraform wrapper with credential injection
└── README.md
```

## Required Jenkins credentials

| Credential ID                       | Type                | Description                                    |
|-------------------------------------|---------------------|------------------------------------------------|
| `gerrit-ssh-key`                    | SSH private key     | Used to clone Gerrit repos                     |
| `gerrit-http-creds`                 | Username/password   | Jenkins service account for Gerrit REST API    |
| `openstack-auth-url`                | Secret text         | Keystone auth URL                              |
| `openstack-plan-appid`              | Secret text         | App credential ID for plan-only sandbox        |
| `openstack-plan-appsecret`          | Secret text         | App credential secret for plan-only sandbox    |
| `openstack-dev-appid`               | Secret text         | App credential ID for lgx-dev project          |
| `openstack-dev-appsecret`           | Secret text         | App credential secret for lgx-dev project      |
| `openstack-test-appid`              | Secret text         | App credential ID for lgx-test project         |
| `openstack-test-appsecret`          | Secret text         | App credential secret for lgx-test project     |
| `openstack-stage-appid`             | Secret text         | App credential ID for lgx-stage project        |
| `openstack-stage-appsecret`         | Secret text         | App credential secret for lgx-stage project    |
| `openstack-prod-appid`              | Secret text         | App credential ID for lgx-prod project         |
| `openstack-prod-appsecret`          | Secret text         | App credential secret for lgx-prod project     |
| `lgx-dev-ssh-pubkey`                | Secret text         | SSH public key injected as TF variable         |
| `lgx-test-ssh-pubkey`               | Secret text         | SSH public key for TEST instances              |
| `lgx-stage-ssh-pubkey`              | Secret text         | SSH public key for STAGE instances             |
| `lgx-prod-ssh-pubkey`               | Secret text         | SSH public key for PROD instances              |
| `lgx-dev-deploy-key`                | SSH private key     | Ansible deploy key for DEV bastion             |
| `lgx-test-deploy-key`               | SSH private key     | Ansible deploy key for TEST bastion            |
| `lgx-stage-deploy-key`              | SSH private key     | Ansible deploy key for STAGE bastion           |
| `lgx-prod-deploy-key`               | SSH private key     | Ansible deploy key for PROD bastion            |
| `container-registry-url`            | Secret text         | Private container registry URL                 |
| `container-registry-creds`          | Username/password   | Registry push credentials                      |
| `vault-token`                       | Secret text         | HashiCorp Vault token for Ansible              |

## Required Jenkins node labels

| Label             | Description                                              |
|-------------------|----------------------------------------------------------|
| `terraform`       | Node with terraform, tflint, and tfsec installed         |
| `docker-builder`  | Node with Docker daemon socket accessible                |
| `ansible`         | Node with Ansible and OpenStack SDK installed            |

## Gerrit trigger configuration

In each Jenkins job's configuration:

**Infra validate** (`Jenkinsfile.infra-validate`):
- Trigger: Patchset Created
- Gerrit project: `infra/openstack-ledgora` pattern `plain`
- Branch: `**` (all branches)

**Infra apply** (`Jenkinsfile.infra-apply`):
- Trigger: Change Merged
- Gerrit project: `infra/openstack-ledgora`
- Branch: `main`

**App build** (`Jenkinsfile.app-build`):
- Trigger: Patchset Created
- Gerrit project: `apps/ledgora-core`
- Branch: `**`

**App deploy / Infra promote**: Manual dispatch (parametrized build). Optionally also triggered by specific Gerrit labels such as `Ready-For-Test +1`.

## Adding this library to Jenkins

1. In Jenkins → **Manage Jenkins** → **Configure System** → **Global Pipeline Libraries**.
2. Add library named `lgx-pipeline-library`, pointing to this repository.
3. Use `@Library('lgx-pipeline-library') _` at the top of each Jenkinsfile.
