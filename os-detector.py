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