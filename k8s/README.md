# Ledgora Kubernetes Operations

This directory is the canonical kubectl-managed deployment surface for Ledgora. Apply every environment from the repo root with `kubectl apply -k k8s/overlays/<environment>`.

## Architecture

The stack is deployed as Kubernetes-native workloads:

- `postgres` StatefulSet with a persistent volume claim
- `backend` Django API Deployment exposed through `backend` ClusterIP Service
- `banking-sync` Deployment for recurring banking synchronization
- `approval-digest` Deployment for recurring approval digest delivery
- `app` React/nginx Deployment exposed through `app` ClusterIP Service
- `Ingress` routing `/api` to the backend and `/` to the web app
- `ConfigMap` and `Secret` objects for runtime configuration
- `Role` and `RoleBinding` for namespace-scoped deploy access

The background workers intentionally reuse the backend image so all Python services stay on the same dependency set and release version.

## Namespaces

Create the required namespaces once per cluster:

```sh
kubectl create namespace staging
kubectl create namespace production
```

Optional development namespace:

```sh
kubectl create namespace dev
```

## Secrets

The base manifest includes placeholder values in `k8s/base/secret.yaml`. Replace them before applying any overlay, or maintain environment-specific secret manifests outside the repo and apply them first.

At minimum, set these keys:

- `django-secret-key`
- `database-url`
- `postgres-password`
- `platform-event-token`
- `banking-token-encryption-key`
- provider credentials for Anthropic, Plaid, Yodlee, and Finicity when enabled

## Build And Push Images

Build and push the release images before applying manifests:

```sh
docker build -f api/Dockerfile.prod -t registry/project/backend:version api
docker build -f app/Dockerfile.prod -t registry/project/app:version app
docker push registry/project/backend:version
docker push registry/project/app:version
```

## Deploy

Preview the rendered manifests:

```sh
kubectl kustomize k8s/overlays/staging
kubectl diff -k k8s/overlays/staging
```

Apply an environment:

```sh
kubectl apply -k k8s/overlays/staging
kubectl rollout status statefulset/postgres -n staging
kubectl rollout status deployment/backend -n staging
kubectl rollout status deployment/banking-sync -n staging
kubectl rollout status deployment/approval-digest -n staging
kubectl rollout status deployment/app -n staging
```

Production uses the same flow:

```sh
kubectl diff -k k8s/overlays/production
kubectl apply -k k8s/overlays/production
```

## Scaling And Updates

Scale the stateless services directly with kubectl:

```sh
kubectl scale deployment backend --replicas=3 -n production
kubectl scale deployment app --replicas=3 -n production
```

Roll a new image version:

```sh
kubectl set image deployment/backend backend=registry/project/backend:v2 -n production
kubectl set image deployment/app app=registry/project/app:v2 -n production
kubectl rollout status deployment/backend -n production
kubectl rollout status deployment/app -n production
```

## Monitoring And Logs

Check workload health:

```sh
kubectl get pods -n staging
kubectl top pods -n production
kubectl describe ingress ledgora -n production
```

Read logs:

```sh
kubectl logs deployment/backend -n staging
kubectl logs deployment/banking-sync -n staging
kubectl logs deployment/approval-digest -n staging
```

## Rollback

Roll back a bad deployment revision:

```sh
kubectl rollout history deployment/backend -n production
kubectl rollout undo deployment/backend -n production
kubectl rollout undo deployment/app -n production
```

## RBAC And Context Switching

Namespace-scoped deployment rights are bound to the `ledgora-deployers` group. Switch clusters or users with kubectl contexts:

```sh
kubectl config get-contexts
kubectl config use-context your-cluster-admin-context
kubectl auth can-i update deployments --as-group=ledgora-deployers -n staging
```

## Troubleshooting

Useful kubectl-only commands:

```sh
kubectl get all -n staging
kubectl describe deployment/backend -n staging
kubectl describe statefulset/postgres -n staging
kubectl get events -n staging --sort-by=.lastTimestamp
kubectl exec -it deployment/backend -n staging -- python manage.py check --deploy
```
