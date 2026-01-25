# Deployment (Docker + Kubernetes)

This document shows how to run TaskFlow with Docker Compose and Kubernetes.

## Docker Compose

Files:
- `Dockerfile`
- `docker-compose.yml`

Start:
```bash
docker compose up --build
```

Services:
- `db`: Postgres 15
- `api`: FastAPI on port 8000
- `worker`: background worker (queue=default)

## Kubernetes (manifests)

Manifests in `k8s/`:
- `namespace.yaml`
- `configmap.yaml`
- `secret.yaml`
- `postgres.yaml`
- `api.yaml`
- `worker.yaml`

Apply:
```bash
kubectl apply -f k8s/namespace.yaml
kubectl apply -f k8s/configmap.yaml
kubectl apply -f k8s/secret.yaml
kubectl apply -f k8s/postgres.yaml
kubectl apply -f k8s/api.yaml
kubectl apply -f k8s/worker.yaml
```

Verify:
```bash
kubectl -n taskflow get pods
kubectl -n taskflow get svc
```

Notes:
- The image is `taskflow:latest`. Build and push to your registry before deploying:
  `docker build -t taskflow:latest .`
- Update `TASKFLOW_DATABASE_URL` in `k8s/secret.yaml` for your environment.
- For production, use a managed Postgres and replace `postgres.yaml`.
