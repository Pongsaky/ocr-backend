#!/bin/bash

# OCR Backend - Build and Push Docker Image Script
# This script builds the Docker image and optionally pushes to a registry

set -e

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Default values
DEFAULT_IMAGE_NAME="ocr-backend"
DEFAULT_TAG="latest"
REGISTRY=""
PUSH_TO_REGISTRY=false
BUILD_ARGS=""

# Help function
show_help() {
    echo -e "${BLUE}OCR Backend - Build and Push Script${NC}"
    echo ""
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  -h, --help                Show this help message"
    echo "  -i, --image-name NAME     Docker image name (default: ${DEFAULT_IMAGE_NAME})"
    echo "  -t, --tag TAG             Docker image tag (default: ${DEFAULT_TAG})"
    echo "  -r, --registry REGISTRY   Docker registry URL (e.g., your-registry.com)"
    echo "  -p, --push               Push image to registry after building"
    echo "  --build-arg ARG          Pass build argument to Docker (can be used multiple times)"
    echo ""
    echo "Examples:"
    echo "  $0                                              # Build locally as ocr-backend:latest"
    echo "  $0 -t v1.0.0                                   # Build as ocr-backend:v1.0.0"
    echo "  $0 -r your-registry.com -t v1.0.0 -p          # Build and push to registry"
    echo "  $0 --build-arg ENVIRONMENT=production -p       # Build with custom args and push"
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -h|--help)
            show_help
            exit 0
            ;;
        -i|--image-name)
            IMAGE_NAME="$2"
            shift 2
            ;;
        -t|--tag)
            TAG="$2"
            shift 2
            ;;
        -r|--registry)
            REGISTRY="$2"
            shift 2
            ;;
        -p|--push)
            PUSH_TO_REGISTRY=true
            shift
            ;;
        --build-arg)
            BUILD_ARGS="$BUILD_ARGS --build-arg $2"
            shift 2
            ;;
        *)
            echo -e "${RED}Unknown option: $1${NC}"
            show_help
            exit 1
            ;;
    esac
done

# Set defaults if not provided
IMAGE_NAME=${IMAGE_NAME:-$DEFAULT_IMAGE_NAME}
TAG=${TAG:-$DEFAULT_TAG}

# Construct full image name
if [[ -n "$REGISTRY" ]]; then
    FULL_IMAGE_NAME="${REGISTRY}/${IMAGE_NAME}:${TAG}"
else
    FULL_IMAGE_NAME="${IMAGE_NAME}:${TAG}"
fi

echo -e "${BLUE}🐳 OCR Backend - Docker Build and Push${NC}"
echo -e "${BLUE}Image: ${FULL_IMAGE_NAME}${NC}"
echo -e "${BLUE}Registry: ${REGISTRY:-"Local only"}${NC}"
echo -e "${BLUE}Push to registry: ${PUSH_TO_REGISTRY}${NC}"

# Check if Docker is running
if ! docker info >/dev/null 2>&1; then
    echo -e "${RED}❌ Docker is not running or not accessible${NC}"
    exit 1
fi

# Build the Docker image
echo -e "${YELLOW}🔨 Building Docker image...${NC}"
BUILD_COMMAND="docker build -t ${FULL_IMAGE_NAME} ${BUILD_ARGS} ."

echo -e "${BLUE}Running: ${BUILD_COMMAND}${NC}"
eval $BUILD_COMMAND

if [[ $? -eq 0 ]]; then
    echo -e "${GREEN}✅ Docker image built successfully: ${FULL_IMAGE_NAME}${NC}"
else
    echo -e "${RED}❌ Failed to build Docker image${NC}"
    exit 1
fi

# Tag with additional tags if needed
if [[ "$TAG" != "latest" && -n "$REGISTRY" ]]; then
    LATEST_TAG="${REGISTRY}/${IMAGE_NAME}:latest"
    echo -e "${YELLOW}🏷️  Tagging as latest: ${LATEST_TAG}${NC}"
    docker tag "$FULL_IMAGE_NAME" "$LATEST_TAG"
fi

# Push to registry if requested
if [[ "$PUSH_TO_REGISTRY" == true ]]; then
    if [[ -z "$REGISTRY" ]]; then
        echo -e "${RED}❌ Cannot push: No registry specified${NC}"
        exit 1
    fi
    
    echo -e "${YELLOW}📤 Pushing to registry...${NC}"
    
    # Push main tag
    docker push "$FULL_IMAGE_NAME"
    
    if [[ $? -eq 0 ]]; then
        echo -e "${GREEN}✅ Successfully pushed: ${FULL_IMAGE_NAME}${NC}"
        
        # Push latest tag if it exists
        if [[ "$TAG" != "latest" ]]; then
            LATEST_TAG="${REGISTRY}/${IMAGE_NAME}:latest"
            docker push "$LATEST_TAG"
            if [[ $? -eq 0 ]]; then
                echo -e "${GREEN}✅ Successfully pushed: ${LATEST_TAG}${NC}"
            fi
        fi
    else
        echo -e "${RED}❌ Failed to push to registry${NC}"
        exit 1
    fi
fi

# Show image info
echo -e "${BLUE}📋 Image Information:${NC}"
docker images | grep "$IMAGE_NAME" | head -5

echo -e "${GREEN}🎉 Build process completed successfully!${NC}"

# Show next steps
echo -e "${BLUE}📝 Next Steps:${NC}"
if [[ "$PUSH_TO_REGISTRY" == true ]]; then
    echo "  1. Copy production.env.example to your production server"
    echo "  2. Customize the environment variables in .env.production"
    echo "  3. Create required directories on production server:"
    echo "     sudo mkdir -p /opt/ocr-backend/data/{uploads,results,tmp}"
    echo "     sudo mkdir -p /var/log/ocr-backend"
    echo "  4. Deploy using: docker-compose -f docker-compose.prod.yml up -d"
else
    echo "  1. Test the image locally: docker run -p 8000:8000 ${FULL_IMAGE_NAME}"
    echo "  2. Push to registry: $0 -r your-registry.com -p"
    echo "  3. Deploy to production with docker-compose.prod.yml"
fi 