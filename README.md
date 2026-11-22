# Inventory Management System (FastAPI + Docker + Kubernetes)

Services: `auth` (JWT login, roles), `products` (CRUD), `stock` (in/out, levels, low-stock),
`frontend` (Nginx + static page), PostgreSQL, plus a CronJob for a daily low-stock report.
Default login: **admin / admin123** (admin can add products and users; staff can move stock).

## 1. Run with Docker Compose
    docker compose up --build
    # open http://localhost:8080

## 2. Build and push images (replace YOUR_DOCKERHUB_USER)
    export U=YOUR_DOCKERHUB_USER
    for s in auth products stock; do docker build -t $U/inventory-$s:1.0 services/$s; docker push $U/inventory-$s:1.0; done
    docker build -t $U/inventory-frontend:1.0 frontend && docker push $U/inventory-frontend:1.0
    sed -i "s/YOUR_DOCKERHUB_USER/$U/g" k8s/*.yaml

## 3. Deploy to Minikube
    minikube start
    minikube addons enable ingress
    minikube addons enable metrics-server      # needed for the HPA
    kubectl apply -f k8s/namespace.yaml
    kubectl apply -f k8s/
    kubectl get pods -n inventory -w

    # Ingress: add "$(minikube ip) inventory.local" to /etc/hosts, then open http://inventory.local
    # Or simply:  minikube service frontend -n inventory --url

Using local images without Docker Hub: run `eval $(minikube docker-env)` and build the images in that shell
(`imagePullPolicy: IfNotPresent` is already set).

## 4. Demo commands
    kubectl scale deployment stock -n inventory --replicas=4        # scaling
    kubectl delete pod -n inventory -l app=products                 # self-healing
    kubectl set image deployment/stock stock=$U/inventory-stock:1.1 -n inventory   # rolling update
    kubectl rollout status deployment/stock -n inventory
    kubectl rollout undo deployment/stock -n inventory              # rollback
    kubectl create job --from=cronjob/low-stock-report manual-report -n inventory
    kubectl logs job/manual-report -n inventory                     # see the report
    kubectl get hpa -n inventory -w                                 # autoscaling

## Notes
- All services share one Postgres database but use separate tables (simple; mention as a trade-off in your report).
- Secrets in `k8s/secret.yaml` are demo values. Change them for anything real.
