#!/usr/bin/env python3
"""
Setup and verification script for the restructured Uptime Operator.
"""
import os
import subprocess
import sys
from pathlib import Path


def run_command(cmd, check=True):
    """Run a shell command."""
    print(f"Running: {cmd}")
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    if check and result.returncode != 0:
        print(f"Command failed: {cmd}")
        print(f"Error: {result.stderr}")
        return False
    return True


def main():
    """Main setup function."""
    print("🚀 Setting up Uptime Operator with new structure")
    
    # Check current directory
    if not Path("uptime_operator").exists():
        print("❌ Error: uptime_operator/ directory not found. Are you in the correct directory?")
        sys.exit(1)
    
    print("✅ Project structure verified")
    
    # Check if .env exists
    if not Path(".env").exists():
        if Path("env.example").exists():
            print("📁 Creating .env from env.example...")
            run_command("cp env.example .env")
            print("⚠️  Please edit .env file with your configuration")
        else:
            print("⚠️  No .env file found. Please create one based on the documentation")
    else:
        print("✅ .env file exists")
    
    # Install dependencies
    print("📦 Installing dependencies...")
    if not run_command("uv sync"):
        print("❌ Failed to install dependencies")
        sys.exit(1)
    
    print("✅ Dependencies installed")
    
    # Check if Docker Compose is available
    if run_command("docker --version", check=False):
        print("🐳 Docker is available")
        print("To start Uptime Kuma: docker-compose up -d")
    else:
        print("⚠️  Docker not found. You'll need to run Uptime Kuma separately")
    
    # Check Kubernetes access
    if run_command("kubectl version --client", check=False):
        print("☸️  kubectl is available")
        
        # Check if CRD should be installed
        print("📋 To install CRD: kubectl apply -f manifests/crd.yaml")
    else:
        print("⚠️  kubectl not found. Install kubectl to deploy to Kubernetes")
    
    print("\n🎉 Setup complete!")
    print("\nNext steps:")
    print("1. Edit .env file with your configuration")
    print("2. Start Uptime Kuma: docker-compose up -d")
    print("3. Install CRD: kubectl apply -f manifests/crd.yaml")
    print("4. Run operator: kopf run main.py")
    print("5. Apply example: kubectl apply -f examples/simple-monitor.yaml")
    print("\nRun tests: ./tests/run_tests.py")


if __name__ == "__main__":
    main()
