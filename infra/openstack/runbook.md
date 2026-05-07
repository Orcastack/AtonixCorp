# Ledgora Infrastructure Runbook

**Audience:** Platform/infra leads and DevOps engineers  
**Scope:** OpenStack infrastructure managed via Gerrit + Jenkins  
**Last updated:** 2026-03-17

---

## 1. Roles and responsibilities

| Role                     | Responsibilities                                                    |
|--------------------------|---------------------------------------------------------------------|
| Founder / Ledgora Owner | Defines non-negotiable standards; approves PROD governance changes |
| Platform / Infra Lead    | Owns `infra/openstack-ledgora`; approves STAGE + PROD infra changes    |
| Application Leads        | Own `apps/ledgora-core`; approve STAGE + PROD app changes      |
| DevOps / CI Engineers    | Own Jenkins and Gerrit integration; maintain pipeline library       |
| Developers               | Raise Gerrit changes; ensure tests and plans pass                  |

---

## 2. Standard change flow – infrastructure

1. Engineer identifies the resource change needed (new instance, security rule, etc.).
2. Clone `infra/openstack-ledgora`, create a feature branch.
3. Modify the relevant Terraform env root or module.
4. Push as a Gerrit changeset: `git push origin HEAD:refs/for/main`.
5. Jenkins runs `Jenkinsfile.infra-validate`: lint → security scan → terraform plan.
6. Terraform plan summary is posted as a Gerrit comment.
7. Infra lead reviews the plan (DEV/TEST: 1 approval; STAGE/PROD: 2 approvals including owner).
8. Change is merged → Jenkins `Jenkinsfile.infra-apply` applies to DEV automatically.
9. Infra lead triggers `Jenkinsfile.infra-promote` for TEST.
10. After TEST validation, promote to STAGE.
11. After STAGE sign-off, promote to PROD (requires manual gate + owner approval).

---

## 3. Standard change flow – application deployment

1. Developer pushes a code change to `apps/ledgora-core` as a Gerrit changeset.
2. Jenkins runs `Jenkinsfile.app-build`: unit tests → static analysis → bandit → build → push image.
3. Verified vote posted to Gerrit; peers review code.
4. Change merged → Jenkins `Jenkinsfile.app-deploy` deploys image to DEV automatically.
5. Smoke tests run; results posted to Gerrit.
6. App lead triggers deploy to TEST with the same image tag.
7. Integration tests pass → deploy to STAGE.
8. Regression and business validation → deploy to PROD (within change window).

---

## 4. How to roll back a production infrastructure change

1. **Identify the bad change**: Check the Gerrit change ID in the Jenkins build log.
2. **Raise a revert**: In Gerrit, use "Revert" on the merged change.
3. **Expedited review**: Infra lead and owner review immediately.
4. **Merge and promote**: Jenkins applies to DEV, then fast-promotion to TEST → STAGE → PROD.
5. All apply logs are archived in Jenkins for the post-incident review.

If Terraform cannot cleanly revert (e.g., stateful data resources), apply a corrective
change rather than a blind revert. Escalate to the infra lead.

---

## 5. How to roll back an application deployment

1. Identify the last stable image tag from the Jenkins build history of `Jenkinsfile.app-build`.
2. Trigger `Jenkinsfile.app-deploy` with:
   - `TARGET_ENV=prod`
   - `IMAGE_TAG=<last-stable-tag>`
   - `GERRIT_CHANGE_ID=<original-change-id>` (or a new hotfix change ID)
3. Ansible deploys the previous image with a rolling update.

---

## 6. Emergency access procedure

In a true emergency (e.g., runaway process, security incident):

1. Use the bastion host: `ssh ubuntu@<bastion-floating-ip>`.
2. Any investigative commands are permitted.
3. Any **corrective** commands must be immediately reflected in Ansible IaC as a Gerrit change.
4. Document the session (commands run, reason) in the incident report.
5. If SSH access was taken to a PROD host to make a change, raise an expedited Gerrit change
   within 2 hours to codify it.

---

## 7. How to add a new Ledgora service

1. In `infra/openstack/terraform/envs/<env>/main.tf`, add a `module "new-service"` block
   using `../../modules/compute` and `../../modules/storage`.
2. Update the relevant Ansible inventory (`inventories/<env>/hosts.yml`) to include the new host.
3. If the service needs new security group rules, update `infra/openstack/terraform/modules/security/main.tf`.
4. Raise the change via Gerrit → review → merge → Jenkins applies.
5. Run `site.yml` to apply baseline config, then `deploy-lgx-services.yml` with the image tag.

---

## 8. Tagging verification

To verify that all resources in a given environment carry correct Ledgora tags:

```bash
# Using OpenStack CLI
openstack server list --tags system=ledgora --format json | jq '.[].Name'

# Check a specific resource for change_id
openstack server show lgx-prod-ledger-01 -f json | jq '.properties'
```

Cross-reference the `change_id` tag with the Gerrit change and the Jenkins build URL.

---

## 9. Monitoring and alerting

- All instances run journald; logs are forwarded to the centralized logging stack.
- Prometheus scrapes the monitoring security group hosts on ports 9090–9100.
- Jenkins sends Slack/email notifications on pipeline failures (configure in Jenkins system settings).
- Set up OpenStack alarms for compute instance state changes in PROD.

---

## 10. Credential rotation

All OpenStack application credentials and SSH keys are stored in HashiCorp Vault.
Rotation procedure:

1. Generate new credentials in OpenStack Keystone (per environment).
2. Update the credential in Vault.
3. Update the corresponding Jenkins credential (named `openstack-<env>-appid` / `appsecret`).
4. Invalidate the old credential in OpenStack.
5. Trigger a dry-run pipeline run against the target environment to confirm connectivity.

---

## 11. Phase rollout reference

| Phase | Goal                                              | Status |
|-------|---------------------------------------------------|--------|
| 1     | Gerrit + Jenkins setup; DEV infra + bastion       | Foundation |
| 2     | TEST, STAGE, PROD environments; full network + SGs | Environment modeling |
| 3     | App build + deploy pipelines for Ledgora services | App pipelines |
| 4     | Gerrit rule enforcement; lock down OS + Jenkins access | Governance hardening |
| 5     | Policy checks, cost dashboards, pipeline observability | Continuous improvement |
