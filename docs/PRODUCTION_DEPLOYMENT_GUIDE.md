# OCR Backend - Production Deployment Guide

## 🎯 Overview

This guide covers **production deployment** of the OCR Backend using Docker images without requiring source code on the production server.

## 🚀 Two Deployment Workflows

### **Development Workflow** (Current)
```
git clone → Build inside host machine → Service run
```
- ✅ Good for development and testing
- ❌ Requires source code on production

### **Production Workflow** (New)
```
Pull Docker image → Configure host paths → Start service
```
- ✅ **No source code needed** on production
- ✅ **Configurable storage paths** 
- ✅ **True containerized deployment**

## 📋 Production Deployment Steps

### **Step 1: Build and Push Image (CI/CD)**

On your **build server**:

```bash
# Build and push to registry
./scripts/build_and_push.sh -r your-registry.com -t v1.0.0 -p
```

### **Step 2: Prepare Production Server**

On your **production server** (no source code needed):

```bash
# 1. Download required files
curl -O https://raw.githubusercontent.com/your-repo/ocr-backend/main/docker-compose.prod.yml
curl -O https://raw.githubusercontent.com/your-repo/ocr-backend/main/production.env.example
curl -O https://raw.githubusercontent.com/your-repo/ocr-backend/main/scripts/deploy_production.sh

# 2. Setup production environment
chmod +x deploy_production.sh
./deploy_production.sh setup
```

### **Step 3: Configure Environment**

```bash
# Edit production configuration
nano .env.production
```

**Example configuration:**
```bash
# Host machine paths (customize for your server)
HOST_DATA_DIR=/opt/ocr-backend/data
HOST_LOGS_DIR=/var/log/ocr-backend

# Docker image (from your registry)
OCR_IMAGE_NAME=your-registry.com/ocr-backend:v1.0.0

# Service configuration
OCR_PORT=8000
LOG_LEVEL=INFO
```

### **Step 4: Deploy Service**

**Option A: Fixed Directories (Traditional)**
```bash
# Deploy with fixed directories (single shared storage)
./deploy_production.sh deploy -e .env.production

# Check status
./deploy_production.sh status
```

**Option B: Timestamped Directories (Recommended)**
```bash
# Deploy with timestamped directories (isolation per deployment)
./deploy_production.sh deploy --timestamp -e .env.production

# Check status
./deploy_production.sh status
```

## 🗂️ Host Machine Directory Structure

### **Fixed Directories Mode**
```
# Data directory (configurable via HOST_DATA_DIR)
/opt/ocr-backend/data/
├── default/
│   ├── uploads/          # Incoming files
│   ├── results/          # OCR processing results  
│   ├── tmp/              # Temporary processing files
│   └── logs/             # Application logs
└── archives/             # Optional: archived data

# Logs directory (configurable via HOST_LOGS_DIR)
/var/log/ocr-backend/
└── default/              # Application logs
```

### **Timestamped Directories Mode** (Recommended)
```
# Data directory (configurable via HOST_DATA_DIR)
/opt/ocr-backend/data/
├── 20241218_140000/      # Deployment at 2024-12-18 14:00:00
│   ├── uploads/          # Incoming files
│   ├── results/          # OCR processing results  
│   ├── tmp/              # Temporary processing files
│   └── deploy_info.json  # Deployment metadata
├── 20241218_150000/      # Next deployment at 2024-12-18 15:00:00
│   ├── uploads/
│   ├── results/
│   └── ...
└── archives/             # Optional: archived deployments

# Logs directory (configurable via HOST_LOGS_DIR)
/var/log/ocr-backend/
├── 20241218_140000/      # Logs for first deployment
├── 20241218_150000/      # Logs for second deployment
└── ...
```

## 🔧 Production Management Commands

### **Deployment Commands**
```bash
# Deploy with fixed directories
./deploy_production.sh deploy -e .env.production

# Deploy with timestamped directories (recommended)
./deploy_production.sh deploy --timestamp -e .env.production

# Stop service
./deploy_production.sh stop

# Restart service  
./deploy_production.sh restart

# Check status
./deploy_production.sh status

# View real-time logs
./deploy_production.sh logs

# Cleanup old containers/images
./deploy_production.sh cleanup
```

### **Timestamped Data Management**
```bash
# List all timestamped deployments
./scripts/manage_production_data.sh list

# Show deployment information
./scripts/manage_production_data.sh info 20241218_140000

# Clean up deployments older than 7 days
./scripts/manage_production_data.sh cleanup --days 7

# Preview cleanup (dry run)
./scripts/manage_production_data.sh cleanup --days 7 --dry-run

# Show disk usage
./scripts/manage_production_data.sh usage
```

## 🔐 Security Configuration

```bash
# In .env.production
API_KEY=your-secure-api-key-here
CORS_ORIGINS=https://yourdomain.com
LOG_LEVEL=INFO  # Don't use DEBUG in production

# Ensure proper ownership
sudo chown -R 1000:1000 /opt/ocr-backend/data
sudo chown -R 1000:1000 /var/log/ocr-backend
```

## 📊 Monitoring and Health Checks

```bash
# Built-in health endpoint
curl http://your-server:8000/health

# Docker health status
docker ps --filter "name=ocr-backend-prod"

# View application logs
tail -f /var/log/ocr-backend/ocr-backend.log
```

## ✅ Production Checklist

- [ ] Built and pushed Docker image to registry
- [ ] Created production server directories
- [ ] Configured `.env.production` with correct paths
- [ ] Tested image pull from registry
- [ ] Deployed service successfully
- [ ] Verified health check endpoint
- [ ] Configured log rotation
- [ ] Set up monitoring/alerting 