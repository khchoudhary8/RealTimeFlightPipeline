#!/bin/bash
# 🛸 Flight Pipeline - EC2 Auto-Deployer
# This script automates the installation of Docker, cloning code, and launching the stack.

set -e

PROJECT_DIR="/home/ec2-user/flight_pipeline"

echo "🛠️  Phase 1: System Preparation..."
sudo dnf update -y
sudo dnf install -y docker git
sudo systemctl enable docker --now
sudo usermod -aG docker ec2-user

# Install Docker Compose V2 if not present
if ! docker compose version &> /dev/null; then
    echo "📦 Installing Docker Compose..."
    sudo dnf install -y docker-compose-plugin
fi

echo "📂 Phase 2: Repository Setup..."
# Replace the URL below with your private/public fork if needed
# For now, we assume the code is being pushed/cloned here
if [ ! -d "$PROJECT_DIR" ]; then
    echo "⚠️  Repo not found. Please clone your repo to $PROJECT_DIR or run this script inside the repo."
    # git clone https://github.com/YOUR_USERNAME/flight_pipeline.git "$PROJECT_DIR"
    # exit 1
else
    cd "$PROJECT_DIR"
    echo "🔄 Pulling latest changes..."
    # git pull
fi

echo "💾 Phase 3: Infrastructure Persistence..."
# Ensure Dagster has a home
mkdir -p "$PROJECT_DIR/.dagster_home"
chmod 777 "$PROJECT_DIR/.dagster_home"

echo "🔐 Phase 4: Environment Check..."
if [ ! -f "$PROJECT_DIR/.env" ]; then
    echo "❌ ERROR: .env file missing at $PROJECT_DIR/.env"
    echo "Please upload your .env file containing AWS, Snowflake, and OpenSky credentials."
    exit 1
fi

echo "🚀 Phase 5: Launching Stack..."
docker compose -f "$PROJECT_DIR/docker-compose.yaml" up -d --build

echo "✅ Deployment Complete!"
echo "📡 Dashboard: http://$(curl -s ifconfig.me):8080"
echo "📊 Monitoring: http://$(curl -s ifconfig.me):3001"
