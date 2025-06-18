#!/bin/bash

# OCR Backend - Timestamped Launch Script
# This script creates unique data directories for each launch using timestamps

set -e

# Generate timestamp in format YYYYMMDD_HHMMSS
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")

# Base data directory
DATA_DIR="./data/${TIMESTAMP}"

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${BLUE}🚀 OCR Backend - Timestamped Launch${NC}"
echo -e "${BLUE}Timestamp: ${TIMESTAMP}${NC}"
echo -e "${BLUE}Data directory: ${DATA_DIR}${NC}"

# Create timestamped directories
echo -e "${YELLOW}📁 Creating data directories...${NC}"
mkdir -p "${DATA_DIR}/uploads"
mkdir -p "${DATA_DIR}/results"
mkdir -p "${DATA_DIR}/tmp"
mkdir -p "${DATA_DIR}/logs"

# Set proper permissions
chmod 755 "${DATA_DIR}"
chmod 755 "${DATA_DIR}/uploads"
chmod 755 "${DATA_DIR}/results"
chmod 755 "${DATA_DIR}/tmp"
chmod 755 "${DATA_DIR}/logs"

echo -e "${GREEN}✅ Directories created successfully${NC}"

# Export timestamp for docker-compose
export TIMESTAMP

# Check if docker-compose is available
if ! command -v docker-compose &> /dev/null && ! command -v docker &> /dev/null; then
    echo -e "${RED}❌ Docker or docker-compose not found${NC}"
    exit 1
fi

# Determine compose command
COMPOSE_CMD="docker-compose"
if command -v docker &> /dev/null && docker compose version &> /dev/null; then
    COMPOSE_CMD="docker compose"
fi

# Launch the stack
echo -e "${YELLOW}🐳 Starting Docker Compose with timestamp: ${TIMESTAMP}${NC}"
echo -e "${BLUE}Data will be stored in: ${DATA_DIR}${NC}"

# Build and start the services
echo -e "${YELLOW}Building and starting services...${NC}"
$COMPOSE_CMD up --build -d

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ OCR Backend started successfully!${NC}"
    echo -e "${BLUE}📊 Container info:${NC}"
    $COMPOSE_CMD ps
    echo ""
    echo -e "${BLUE}📁 Data directories:${NC}"
    echo -e "  Uploads: ${DATA_DIR}/uploads"
    echo -e "  Results: ${DATA_DIR}/results"
    echo -e "  Temp:    ${DATA_DIR}/tmp"
    echo -e "  Logs:    ${DATA_DIR}/logs"
    echo ""
    echo -e "${BLUE}🔍 View logs with:${NC}"
    echo -e "  $COMPOSE_CMD logs -f ocr-backend"
    echo ""
    echo -e "${BLUE}🛑 Stop services with:${NC}"
    echo -e "  $COMPOSE_CMD down"
    echo ""
    echo -e "${BLUE}🌐 API available at:${NC}"
    echo -e "  http://localhost:8000"
    echo -e "  http://localhost:8000/docs (Swagger UI)"
else
    echo -e "${RED}❌ Failed to start OCR Backend${NC}"
    echo -e "${YELLOW}Check logs with: $COMPOSE_CMD logs${NC}"
    exit 1
fi

# Save launch info
echo "{\"timestamp\": \"${TIMESTAMP}\", \"data_dir\": \"${DATA_DIR}\", \"started_at\": \"$(date -Iseconds)\"}" > "${DATA_DIR}/launch_info.json" 