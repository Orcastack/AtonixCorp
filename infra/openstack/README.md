# Ledgora – OpenStack Infrastructure

This directory contains all Infrastructure as Code (IaC) and pipeline definitions
for operating Ledgora on OpenStack using Gerrit change control and Jenkins pipelines.

**No manual changes are permitted in any Ledgora environment beyond temporary DEV experiments.**

---

## Directory layout

```
infra/openstack/
├── terraform/
│   ├── modules/
│   │   ├── network/       Neutron networks, subnets, router (per env)
│   │   ├── security/      Security groups – deny-all default, minimal port opens
│   │   ├── compute/       Nova instances with LGX traceability metadata
│   │   └── storage/       Cinder volumes with auto-attach
│   └── envs/
│       ├── dev/           lgx-dev project  (auto-applied on merge to main)
│       ├── test/          lgx-test project (promotion pipeline)
│       ├── stage/         lgx-stage project (promotion pipeline, 2 approvals)
│       └── prod/          lgx-prod project (promotion pipeline, PROD gate + 2 approvals)
├── ansible/
│   ├── ansible.cfg
│   ├── inventories/       Per-environment static host inventories
│   ├── playbooks/
│   │   ├── site.yml                Baseline hardening for all hosts
│   │   └── deploy-lgx-services.yml Rolling deploy of the LGX API container
│   └── roles/
│       ├── lgx-common/    OS hardening, Docker, audit logging
│       ├── lgx-api/       Container lifecycle for ledger/accounts/risk/reporting
│       └── lgx-db/        PostgreSQL container on db hosts
infra/gerrit/
├── projects/
│   ├── infra-openstack-ledgora.config  Access rules for infra/openstack-ledgora
│   ├── apps-ledgora-core.config Access rules for apps/ledgora-core
│   └── ci-jenkins-pipelines.config Access rules for ci/jenkins-pipelines
├── groups                          Gerrit group UUID registry
└── setup-instructions.md           Step-by-step Gerrit bootstrap guide
ci/jenkins-pipelines/
├── Jenkinsfile.infra-validate     Lint + security + plan on patchset-created
├── Jenkinsfile.infra-apply        Apply infra to DEV on change-merged
├── Jenkinsfile.infra-promote      Promote infra to TEST / STAGE / PROD
├── Jenkinsfile.app-build          Build, test, scan, push container image
├── Jenkinsfile.app-deploy         Deploy container to target environment
├── vars/
│   ├── gerrit.groovy              Shared: Gerrit vote/comment steps
│   └── openstack.groovy           Shared: Terraform wrapper with cred injection
└── README.md                      Credential table and configuration guide
```

---

## Environment model

| Environment | OpenStack project | CIDR (main) | CIDR (backend) | Auto-deploy?       |
|-------------|-------------------|-------------|----------------|--------------------|
| DEV         | lgx-dev           | 10.10.0.0/24| 10.10.1.0/24   | Yes (on merge)     |
| TEST        | lgx-test          | 10.20.0.0/24| 10.20.1.0/24   | Manual promotion   |
| STAGE       | lgx-stage         | 10.30.0.0/24| 10.30.1.0/24   | Manual, 2 approvals|
| PROD        | lgx-prod          | 10.40.0.0/24| 10.40.1.0/24   | Manual gate + PROD approval |

---

## Change flow

```
Engineer → Gerrit change → Jenkins validate (lint + plan) → peer review
       → merge to main → Jenkins auto-applies to DEV
       → manual promotion to TEST → integration tests
       → manual promotion to STAGE → regression + business validation
       → manual promotion to PROD (within change window, with approval gate)
```

Every resource created by Terraform carries these tags:

```
system=ledgora
env=<dev|test|stage|prod>
service=<ledger|accounts|risk|reporting|shared>
change_id=<GerritChangeID>
commit=<shortSHA>
```

---

## Quick-start

### Prerequisites

- Terraform ≥ 1.6
- tflint and tfsec
- Ansible ≥ 2.14 with collections: `community.docker`, `community.postgresql`, `community.general`
- Access to an OpenStack project with application credentials

### First-time bootstrap (DEV)

```bash
# 1. Export credentials (normally injected by Jenkins; manual only for bootstrapping DEV)
export TF_VAR_os_application_credential_id=<from-openstack-ui>
export TF_VAR_os_application_credential_secret=<from-openstack-ui>
export TF_VAR_ssh_public_key="$(cat ~/.ssh/id_ed25519.pub)"
export TF_VAR_change_id="manual-bootstrap"
export TF_VAR_commit="$(git rev-parse --short HEAD)"

# 2. Init and apply DEV infra
cd infra/openstack/terraform/envs/dev
terraform init
terraform plan
terraform apply

# 3. Apply baseline Ansible config
cd infra/openstack/ansible
ansible-playbook playbooks/site.yml --inventory inventories/dev/hosts.yml
```

> After bootstrapping, all subsequent changes **must** go through Gerrit → Jenkins.

---

## Non-negotiables

1. No manual provisioning in the OpenStack UI for TEST, STAGE, or PROD.
2. No direct SSH changes to PROD instances unless reflected in Ansible IaC.
3. No production deployment outside Jenkins pipelines.
4. Every resource must be traceable to a Gerrit change ID and a Jenkins build.
5. Any change that weakens security posture requires explicit infra lead + owner approval.

---

## Rollback procedure

1. Identify the last known-good commit in `infra/openstack-ledgora`.
2. Raise a Gerrit change reverting the problematic commits.
3. Fast-track review (expedited, but still two approvers for PROD).
4. Jenkins applies the revert.
5. Document in the post-incident review.

See [runbook.md](runbook.md) for the full incident response procedure.
