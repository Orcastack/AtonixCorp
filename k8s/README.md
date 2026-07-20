# AtonixCorp Kubernetes Operations

This directory is the canonical kubectl-managed deployment surface for AtonixCorp. Apply every environment from the repo root with `kubectl apply -k k8s/overlays/<environment>`.

## Architecture

The stack is deployed as Kubernetes-native workloads:

- `postgres` StatefulSet with a persistent volume claim
- `backend` Django API Deployment exposed through `backend` ClusterIP Service
- `banking-sync` Deployment for recurring banking synchronization
- `approval-digest` Deployment for recurring approval digest delivery
- `app` React/nginx Deployment exposed through `app` ClusterIP Service
- `Ingress` routing the public web origin to the app and the API origin to Django
- `ConfigMap` and `Secret` objects for runtime configuration
- `Role` and `RoleBinding` for namespace-scoped deploy access

The background workers can either reuse the backend image or run as separately tagged images when you want local image parity.

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

### Local Images

If you want Kubernetes to use the images you already built locally, use `k8s/overlays/local`.

Expected images:

- `atonixdev/legdora-api:latest`
- `atonixdev/legdora-app:latest`
- `atonixdev/legdora-banking-sync:latest`
- `atonixdev/legdora-approval-digest:latest`

Create the namespace:

```sh
kubectl create namespace atonixcorp-local
```

If your cluster does not share the host Docker daemon, load the images first.

For `kind`:

```sh
kind load docker-image atonixdev/legdora-api:latest
kind load docker-image atonixdev/legdora-app:latest
kind load docker-image atonixdev/legdora-banking-sync:latest
kind load docker-image atonixdev/legdora-approval-digest:latest
```

For `minikube`:

```sh
minikube image load atonixdev/legdora-api:latest
minikube image load atonixdev/legdora-app:latest
minikube image load atonixdev/legdora-banking-sync:latest
minikube image load atonixdev/legdora-approval-digest:latest
```

Deploy locally:

```sh
kubectl apply -k k8s/overlays/local
kubectl rollout status statefulset/postgres -n atonixcorp-local
kubectl rollout status deployment/backend -n atonixcorp-local
kubectl rollout status deployment/banking-sync -n atonixcorp-local
kubectl rollout status deployment/approval-digest -n atonixcorp-local
kubectl rollout status deployment/app -n atonixcorp-local
```

If you do not have an ingress controller locally, use port-forwarding:

```sh
kubectl port-forward service/app 3000:80 -n atonixcorp-local
kubectl port-forward service/backend 8000:8000 -n atonixcorp-local
```

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

## Production Domains And TLS

The production overlay serves `https://atonixcorp.com` as the canonical web origin and `https://api.atonixcorp.com` as the API origin. `https://www.atonixcorp.com` permanently redirects to the canonical web origin. The NGINX Ingress `ssl-redirect` annotation redirects all plain HTTP requests to HTTPS; HTTP is not an application origin and must not be added to CORS or CSRF allowlists.

Before applying the production overlay, point these DNS records at the NGINX Ingress load balancer:

- `atonixcorp.com`
- `www.atonixcorp.com`
- `api.atonixcorp.com`

Provision `atonixcorp-production-tls` in the `production` namespace with a certificate containing all three names. The manifests reference this secret but do not issue certificates because the cluster's certificate authority and issuer are infrastructure-owned.

The frontend production build reads `app/.env.production`, which compiles `https://api.atonixcorp.com/api` into the React bundle. Build and publish the frontend image after domain changes.

Set the Brevo SMTP key in the deployment secret before enabling email delivery. The backend reads the non-secret relay settings from the ConfigMap and `EMAIL_HOST_PASSWORD` from `atonixcorp-app-secrets` key `brevo-smtp-key`.

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
kubectl describe ingress atonixcorp -n production
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

Namespace-scoped deployment rights are bound to the `atonixcorp-deployers` group. Switch clusters or users with kubectl contexts:

```sh
kubectl config get-contexts
kubectl config use-context your-cluster-admin-context
kubectl auth can-i update deployments --as-group=atonixcorp-deployers -n staging
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
