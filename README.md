# Inventory Management System — DevOps Project

A microservices-based Inventory Management System built using **FastAPI, PostgreSQL, Docker, Kubernetes, Minikube, NGINX, and GitHub Actions**.

The project demonstrates containerization, microservices communication, CI automation, Kubernetes orchestration, persistent storage, auto-scaling, self-healing, rolling updates, rollback, Ingress routing, and scheduled reporting.

## 1. Technology Stack

| Layer | Technology |
|---|---|
| Frontend | HTML, CSS, JavaScript, NGINX |
| Backend | Python, FastAPI |
| Authentication | JWT, role-based access |
| Database | PostgreSQL 16 |
| Containerization | Docker, Docker Compose |
| Orchestration | Kubernetes, Minikube |
| Networking | Kubernetes Services, NGINX Ingress |
| Auto-scaling | Horizontal Pod Autoscaler |
| Monitoring | Kubernetes Metrics Server |
| Scheduled Tasks | Kubernetes CronJob |
| CI | GitHub Actions, pytest |
| Version Control | Git, GitHub |
| Development Environment | Windows 11, Docker Desktop |

## 2. System Architecture

```text
                 Web Browser
                      |
                NGINX Ingress
                      |
                Frontend Service
                      |
                Frontend (NGINX)
                      |
          +-----------+-----------+
          |           |           |
       Auth API   Products API  Stock API
          |           |           |
          +-----------+-----------+
                      |
                 PostgreSQL
                      |
              Persistent Volume

      Kubernetes HPA --> Stock Deployment

      Kubernetes CronJob
              |
       Low Stock Report
              |
         Auth + Stock APIs
```

The three backend microservices share a PostgreSQL database but maintain separate application tables. This simplifies the learning project, although independently managed databases would provide stronger service isolation in a larger production system.

## 3. Application Features

- JWT-based user authentication
- Administrator and staff roles
- Product creation, viewing, updating, and deletion through APIs
- Stock-in and stock-out operations
- Current inventory levels
- Low-stock identification
- Stock transaction history
- Automated daily low-stock reporting

## 4. Project Structure

```text
inventory-system/
├── .github/
│   └── workflows/
│       └── ci.yml
├── frontend/
│   ├── Dockerfile
│   ├── index.html
│   └── nginx.conf
├── services/
│   ├── auth/
│   ├── products/
│   └── stock/
│       └── report.py
├── k8s/
│   ├── namespace.yaml
│   ├── configmap.yaml
│   ├── auth.yaml
│   ├── products.yaml
│   ├── stock.yaml
│   ├── frontend.yaml
│   ├── postgres.yaml
│   ├── hpa.yaml
│   ├── ingress.yaml
│   └── cronjob-report.yaml
├── tests/
│   └── test_health.py
├── docker-compose.yml
└── README.md
```

The local `k8s/secret.yaml` is intentionally excluded from Git to protect credentials.

## 5. Running with Docker Compose

**Prerequisites:** Docker Desktop with the Docker engine running.

From the project directory:

```cmd
docker compose up --build -d
```

Open:

http://localhost:8080

Check the containers:

```cmd
docker compose ps
```

Stop the application:

```cmd
docker compose down
```

Configure the administrator credentials through your private development configuration. Do not commit passwords, tokens, or production secrets.

## 6. Kubernetes Deployment

**Prerequisites:**
- Docker Desktop
- Minikube
- kubectl
- A configured Kubernetes Secret
- Locally built container images

Start Minikube:

```cmd
minikube start --driver=docker
```

Enable the required addons:

```cmd
minikube addons enable metrics-server
minikube addons enable ingress
```

Build the images if they are not already available:

```cmd
docker compose build
```

Load the images into Minikube:

```cmd
minikube image load inventory-system-auth:latest
minikube image load inventory-system-products:latest
minikube image load inventory-system-stock:latest
minikube image load inventory-system-frontend:latest
```

For the demonstrated Products `v2` deployment, the `v2` tag must also exist in Minikube. For the current demonstration, it references the same application contents as `latest`:

```cmd
docker tag inventory-system-products:latest inventory-system-products:v2
minikube image load inventory-system-products:v2
```

Create the namespace:

```cmd
kubectl apply -f k8s/namespace.yaml
```

Configure `k8s/secret.yaml` locally using your own development credentials, then apply the Secret:

```cmd
kubectl apply -f k8s/secret.yaml
```

Deploy the remaining Kubernetes resources:

```cmd
kubectl apply -f k8s/configmap.yaml
kubectl apply -f k8s/postgres.yaml
kubectl apply -f k8s/auth.yaml
kubectl apply -f k8s/products.yaml
kubectl apply -f k8s/stock.yaml
kubectl apply -f k8s/frontend.yaml
kubectl apply -f k8s/hpa.yaml
kubectl apply -f k8s/ingress.yaml
kubectl apply -f k8s/cronjob-report.yaml
```

Check the deployment:

```cmd
kubectl get pods -n inventory
kubectl get deployments -n inventory
kubectl get services -n inventory
```

These commands and image tags describe the local Minikube setup used for this project, not a production deployment.

## 7. Accessing the Application Through Ingress

The Ingress routes requests for `inventory.local` to the frontend Service.

On Windows, start the Minikube tunnel in a separate terminal:

```cmd
minikube tunnel
```

Configure the Windows hosts file:

```text
C:\Windows\System32\drivers\etc\hosts
```

Add:

```text
127.0.0.1 inventory.local
```

Open:

http://inventory.local

Verify HTTP routing:

```cmd
curl.exe -I http://inventory.local/
```

The Ingress test returned `HTTP/1.1 200 OK`.

## 8. Horizontal Pod Autoscaling

The Stock microservice uses an HPA configured with:

- Minimum replicas: 2
- Maximum replicas: 6
- CPU utilization target: 60%

Monitor the autoscaler:

```cmd
kubectl get hpa -n inventory
kubectl top pods -n inventory
```

**Demonstration result:**

```text
Initial:       2 Pods
High CPU load: 6 Pods
Low CPU load:  2 Pods
```

This verified automatic scale-up and scale-down.

## 9. Rolling Updates and Rollback

The Products Deployment uses the RollingUpdate strategy.

Verify deployment status:

```cmd
kubectl rollout status deployment/products -n inventory
```

Inspect revision history:

```cmd
kubectl rollout history deployment/products -n inventory
```

Roll back to a previous revision:

```cmd
kubectl rollout undo deployment/products -n inventory
```

The project successfully demonstrated rolling updates, rollback, and restoration of the desired deployment version.

## 10. Kubernetes Self-Healing

Kubernetes Deployments maintain the desired number of Pods.

During testing, a Products Pod was manually deleted. Kubernetes automatically created a replacement Pod, restoring the desired replica count.

Check Pods:

```cmd
kubectl get pods -n inventory -l app=products
```

This demonstrated Kubernetes self-healing.

## 11. Persistent Database Storage

PostgreSQL is deployed as a StatefulSet with persistent storage.

The Kubernetes PersistentVolumeClaim is configured with:

```text
Storage:       1 GiB
StorageClass:  standard
Status:        Bound
```

The inventory data was verified to persist across a Minikube restart.

Check storage:

```cmd
kubectl get pvc -n inventory
```

## 12. Scheduled Low-Stock Reports

Kubernetes CronJob name:

`low-stock-report`

Schedule:

```text
0 8 * * *
```

Timezone:

`Asia/Kolkata`

This schedules report generation daily at 8:00 AM IST while the cluster and CronJob controller are running.

Manually trigger a test:

```cmd
kubectl create job --from=cronjob/low-stock-report low-stock-test -n inventory
```

View the results:

```cmd
kubectl logs job/low-stock-test -n inventory
```

**Verified test result:**

```text
[LOW] 1 Coke qty=7 threshold=10 supplier=co
```

The manually triggered Job completed successfully.

## 13. GitHub Actions Continuous Integration

The repository includes a CI workflow at:

```text
.github/workflows/ci.yml
```

The workflow runs on pushes and pull requests targeting the `main` branch and supports manual execution.

The pipeline performs:

1. Source-code checkout
2. Python environment setup
3. Dependency installation
4. Automated FastAPI health-check tests
5. Docker image builds for Auth, Products, Stock, and Frontend

**Verified results:**

- 3 Python tests passed
- Auth Docker build passed
- Products Docker build passed
- Stock Docker build passed
- Frontend Docker build passed

The current workflow performs continuous integration. It does not yet automatically publish Docker images or deploy to Kubernetes.

## 14. Automated Testing

Run the health-check tests locally:

```cmd
python -m pytest tests\test_health.py -v
```

The tests verify:

```text
Auth:      GET /health
Products:  GET /health
Stock:     GET /health
```

Result:

```text
3 passed
```

These are lightweight API health checks. Comprehensive business-logic and database integration testing would require additional tests.

## 15. Security Considerations

- JWT authentication for protected API endpoints
- Role-based access control
- Kubernetes Secrets for sensitive configuration
- `.gitignore` prevents local Kubernetes credentials from being committed
- Non-root application container configuration for Stock
- Environment-based configuration for application services

Development credentials must be replaced before any public or production deployment.

The Docker Compose and Kubernetes configurations are designed for learning and local demonstrations rather than production security.

## 16. Verified DevOps Features

| Feature | Result |
|---|---|
| Containerization | Completed |
| Docker Compose | Tested |
| Kubernetes Deployments | Tested |
| Kubernetes Services | Tested |
| PostgreSQL StatefulSet | Tested |
| PersistentVolumeClaim | Tested |
| Self-healing | Tested |
| Manual scaling | Tested |
| Rolling updates | Tested |
| Rollback | Tested |
| HPA scale-up | Tested |
| HPA scale-down | Tested |
| NGINX Ingress HTTP routing | Tested |
| Kubernetes CronJob | Manual test passed |
| GitHub Actions CI | Passed |
| Automated health tests | 3 passed |
| Docker image builds in CI | 4 passed |

## 17. Future Improvements

- Automated Docker image publishing
- Continuous Deployment to a Kubernetes environment
- Comprehensive unit and integration tests
- Prometheus and Grafana monitoring
- Centralized logging and alerting
- HTTPS/TLS for Ingress
- Production-grade secrets management
- Independent databases for each microservice

## Repository

https://github.com/abin-pH/inventory-management-system

## Conclusion

This project demonstrates how an application built using FastAPI microservices and PostgreSQL can be containerized with Docker, deployed on Kubernetes, scaled automatically, monitored, updated, rolled back, and tested through a GitHub Actions CI pipeline.

It provides practical experience with essential DevOps concepts across development, containerization, orchestration, automation, and application operations.