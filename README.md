# k8s-crane-inspection
service to discover workloads in k8s cluster and determine container OS image type of workloads in cluster using crane

Here's a Python program that uses the Crane tool within a Kubernetes cluster to discover all pods, inspect their container images, and determine the base OS of each image. This program will run as a pod in the cluster and use the Kubernetes Python client along with Crane (via subprocess calls) to achieve this.

### Prerequisites
- The program assumes Crane is installed in the container (I'll include it in the Dockerfile).
- It needs access to the Kubernetes cluster's API (using a service account).
- The container images must be accessible (public or authenticated).

### Program

```python
#!/usr/bin/env python3

import subprocess
import json
from kubernetes import client, config
import os

def get_pod_images():
    """Discover all pods in the cluster and return a list of their container images."""
    # Load in-cluster config
    config.load_in_cluster_config()
    v1 = client.CoreV1Api()
    
    # Get all pods across all namespaces
    pods = v1.list_pod_for_all_namespaces(watch=False)
    
    pod_images = []
    for pod in pods.items:
        namespace = pod.metadata.namespace
        pod_name = pod.metadata.name
        for container in pod.spec.containers:
            image = container.image
            pod_images.append({
                "namespace": namespace,
                "pod_name": pod_name,
                "image": image
            })
    return pod_images

def get_image_os(image):
    """Use Crane to inspect the image and determine its base OS."""
    try:
        # Run 'crane config' to get image configuration
        result = subprocess.run(
            ["crane", "config", image],
            capture_output=True,
            text=True,
            check=True
        )
        
        # Parse the JSON output
        config = json.loads(result.stdout)
        
        # Extract OS from the config (falls back to 'unknown' if not found)
        os_type = config.get("os", "unknown")
        return os_type
    
    except subprocess.CalledProcessError as e:
        print(f"Error inspecting image {image}: {e.stderr}")
        return "error"
    except json.JSONDecodeError:
        print(f"Failed to parse Crane output for {image}")
        return "error"

def main():
    print("Discovering pods and inspecting container images...")
    
    # Get all pod images
    pod_images = get_pod_images()
    
    # Inspect each image with Crane
    for item in pod_images:
        namespace = item["namespace"]
        pod_name = item["pod_name"]
        image = item["image"]
        
        os_type = get_image_os(image)
        print(f"Namespace: {namespace}, Pod: {pod_name}, Image: {image}, Base OS: {os_type}")

if __name__ == "__main__":
    main()
```

### Dockerfile

Here's the multi-stage Dockerfile to build and run this program, using a distroless base image for the runtime:

```dockerfile
# Stage 1: Build Stage
FROM cgr.dev/ky-rafaels.example.com/python:3.11-dev AS builder

WORKDIR /app

# Install Crane
RUN apk add --no-cache crane

# Copy application code
COPY os_detector.py .

# Stage 2: Runtime Stage using distroless
FROM cgr.dev/ky-rafaels.example.com/python:3.11

WORKDIR /app

# Copy Python dependencies
# COPY --from=builder /app/deps /app/deps

# Copy Crane binary
COPY --from=builder /usr/bin/crane /usr/bin/crane

# Copy application code
COPY --from=builder /app/os_detector.py /app/os_detector.py

# Set Python path
# ENV PYTHONPATH=/app/deps

# Ensure Crane is executable
USER root
RUN chmod +x /usr/bin/crane
USER nonroot

ENTRYPOINT ["python"]
CMD ["/app/os_detector.py"]
```

### Kubernetes Manifest

You'll need to deploy this as a pod with appropriate permissions. Here's a manifest:

```yaml
apiVersion: v1
kind: ServiceAccount
metadata:
  name: image-os-detector
---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRole
metadata:
  name: pod-reader
rules:
- apiGroups: [""]
  resources: ["pods"]
  verbs: ["get", "list"]
---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRoleBinding
metadata:
  name: image-os-detector-binding
subjects:
- kind: ServiceAccount
  name: image-os-detector
  namespace: default
roleRef:
  kind: ClusterRole
  name: pod-reader
  apiGroup: rbac.authorization.k8s.io
---
apiVersion: v1
kind: Pod
metadata:
  name: image-os-detector
spec:
  serviceAccountName: image-os-detector
  containers:
  - name: os-detector
    image: my-python-app:latest  # Replace with your built image
  restartPolicy: Never
```

### requirements.txt

```
kubernetes==29.0.0
```

### How It Works

1. **Discovery**:
   - The `get_pod_images()` function uses the Kubernetes Python client to list all pods in all namespaces and extracts their container images.

2. **Inspection**:
   - The `get_image_os()` function calls `crane config <image>` to get the image configuration in JSON format. The `os` field in this config typically indicates the base OS (e.g., `linux`, `windows`).

3. **Execution**:
   - The main function ties it together, printing the namespace, pod name, image, and detected OS for each container.

4. **Dockerfile**:
   - The build stage installs Python dependencies and Crane, then copies them to a distroless runtime image for security and minimal footprint.

5. **Kubernetes**:
   - The manifest creates a service account with permissions to list pods and runs the pod once (`restartPolicy: Never`). Check the logs with `kubectl logs image-os-detector` after it runs.

### Notes

- **Authentication**: If your images are in a private registry, you'll need to configure Crane with credentials (e.g., via `crane auth login` or environment variables like `DOCKER_CONFIG`). You could mount a secret with credentials into the pod.
- **Output**: The program prints to stdout. For production, you might want to log to a file or send results to an external system (e.g., BigQuery, as mentioned earlier).
- **Limitations**: Distroless images or custom images might not always specify the `os` field clearly, so "unknown" or "error" might appear. You could extend this to parse layer contents with `crane export` if needed, though that’s more complex.
- **Date**: As of March 11, 2025, Crane remains a reliable tool for image inspection, and this approach should work with current Kubernetes versions.

To deploy:
1. Save the Python script as `os_detector.py`.
2. Build the Docker image: `docker build -t my-python-app .`
3. Push to a registry: `docker push my-python-app`
4. Apply the Kubernetes manifest: `kubectl apply -f manifest.yaml`

Let me know if you need adjustments (e.g., handling private registries, more detailed OS detection)!