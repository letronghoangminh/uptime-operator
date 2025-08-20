#!/usr/bin/env python3
"""
Real integration test runner for Uptime Operator.
Uses environment variables for configuration:
- KUBECONFIG: Path to kubernetes config file
- UPTIME_KUMA_URL: Uptime Kuma instance URL (default: http://localhost:3001)
"""
import subprocess
import sys
import time
import os


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
    """Run real integration tests."""
    print("🧪 Running Uptime Operator Real Integration Tests")
    
    # Check environment variables
    kubeconfig = os.environ.get('KUBECONFIG')
    uptime_kuma_url = os.environ.get('UPTIME_KUMA_URL', 'http://localhost:3001')
    
    print(f"📋 Configuration:")
    print(f"   KUBECONFIG: {kubeconfig or 'default'}")
    print(f"   UPTIME_KUMA_URL: {uptime_kuma_url}")
    
    # Check if CRD is installed
    print("\n📋 Checking CRD installation...")
    result = run_command("kubectl get crd uptimemonitors.uptime-operator.dev", check=False)
    if result.returncode != 0:
        print("Installing CRD...")
        run_command("kubectl apply -f manifests/crd.yaml")
        time.sleep(2)
    else:
        print("✅ CRD already installed")
    
    # Check if Uptime Kuma is accessible
    print("\n🏃 Checking Uptime Kuma availability...")
    result = run_command(f"curl -f {uptime_kuma_url} > /dev/null 2>&1", check=False)
    if result.returncode != 0:
        print(f"⚠️  Uptime Kuma not accessible at {uptime_kuma_url}")
        print("Please ensure Uptime Kuma is running and accessible")
        print("For local testing: docker-compose up -d")
    else:
        print("✅ Uptime Kuma is accessible")
    
    # Run real integration tests
    print("\n🔗 Running real integration tests...")
    run_command("pytest tests/test_real_integration.py -v")
    
    print("\n✅ Integration tests completed!")
    print("\nTo run the operator:")
    print("  python main.py")
    print("  # or")
    print("  kopf run main.py --namespace=default")


if __name__ == "__main__":
    main()
