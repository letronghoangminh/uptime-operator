#!/usr/bin/env python3
"""
Test runner script for comprehensive testing scenarios.
"""
import subprocess
import sys
import time
import os
from pathlib import Path


def run_command(cmd, check=True):
    """Run a shell command."""
    print(f"Running: {cmd}")
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    if check and result.returncode != 0:
        print(f"Command failed: {cmd}")
        print(f"stdout: {result.stdout}")
        print(f"stderr: {result.stderr}")
        sys.exit(1)
    return result


def main():
    """Run all test scenarios."""
    print("🧪 Running Uptime Operator Test Suite")
    
    # Set kubeconfig to minikube
    os.environ['KUBECONFIG'] = os.path.expanduser('~/.kube/config.minikube')
    
    # Check if CRD is installed
    print("\n📋 Checking CRD installation...")
    result = run_command("kubectl get crd uptimemonitors.uptime-operator.psycholog1st.dev", check=False)
    if result.returncode != 0:
        print("Installing CRD...")
        run_command("kubectl apply -f manifests/crd.yaml")
        time.sleep(2)
    else:
        print("✅ CRD already installed")
    
    # Run unit tests
    print("\n🔧 Running unit tests...")
    run_command("pytest tests/test_models.py -v")
    
    # Check if Uptime Kuma is running
    print("\n🏃 Checking Uptime Kuma availability...")
    result = run_command("curl -f http://localhost:3001 > /dev/null 2>&1", check=False)
    if result.returncode != 0:
        print("⚠️  Uptime Kuma not accessible at localhost:3001")
        print("Please ensure Uptime Kuma is running: docker-compose up -d")
        print("And complete the setup at http://localhost:3001")
    else:
        print("✅ Uptime Kuma is accessible")
    
    # Apply test scenarios
    print("\n📝 Applying test scenarios...")
    run_command("kubectl apply -f tests/test_scenarios.yaml")
    
    # Wait a bit for resources to be created
    print("⏳ Waiting for resources...")
    time.sleep(5)
    
    # Show created resources
    print("\n📊 Checking created UptimeMonitors...")
    run_command("kubectl get uptimemonitors -A")
    
    # Run integration tests (if Uptime Kuma is available)
    if result.returncode == 0:
        print("\n🔗 Running integration tests...")
        run_command("pytest tests/test_integration.py -v")
    
    print("\n🧹 Cleaning up test resources...")
    run_command("kubectl delete -f tests/test_scenarios.yaml --ignore-not-found=true")
    
    print("\n✅ Test suite completed!")
    print("\nTo run individual tests:")
    print("  pytest tests/test_models.py -v")
    print("  pytest tests/test_integration.py -v")
    print("\nTo run the operator:")
    print("  python main.py")
    print("  # or")
    print("  kopf run main.py --namespace=default")


if __name__ == "__main__":
    main()
