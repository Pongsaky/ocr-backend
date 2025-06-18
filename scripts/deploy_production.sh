#!/bin/bash

# OCR Backend - Production Deployment Script
# Deploy OCR Backend on production servers with configurable paths

set -e

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Default values
DEFAULT_ENV_FILE="production.env.example"
DEFAULT_COMPOSE_FILE="docker-compose.prod.yml"
ACTION=""
ENV_FILE=""
COMPOSE_FILE=""
TIMESTAMP_MODE=false
DEPLOYMENT_TIMESTAMP=""

# Help function
show_help() {
    echo -e "${BLUE}OCR Backend - Production Deployment Script${NC}"
    echo ""
    echo "Usage: $0 [ACTION] [OPTIONS]"
    echo ""
    echo "Actions:"
    echo "  setup        Setup production environment (create directories, copy configs)"
    echo "  deploy       Deploy the OCR backend service"
    echo "  stop         Stop the OCR backend service"
    echo "  restart      Restart the OCR backend service"
    echo "  status       Show service status"
    echo "  logs         Show service logs"
    echo "  cleanup      Clean up old containers and images"
    echo ""
    echo "Options:"
    echo "  -h, --help                Show this help message"
    echo "  -e, --env-file FILE       Environment file (default: ${DEFAULT_ENV_FILE})"
    echo "  -f, --compose-file FILE   Docker compose file (default: ${DEFAULT_COMPOSE_FILE})"
    echo "  --timestamp               Deploy with timestamped directories (isolation per deployment)"
    echo "  --fixed                   Deploy with fixed directories (default, single shared storage)"
    echo ""
    echo "Examples:"
    echo "  $0 setup                              # Setup production environment"
    echo "  $0 deploy -e .env.production         # Deploy with fixed directories"
    echo "  $0 deploy --timestamp                # Deploy with timestamped directories"
    echo "  $0 deploy --timestamp -e .env.prod   # Deploy with timestamps and custom env"
    echo "  $0 status                            # Check service status"
    echo "  $0 logs                              # View service logs"
}

# Parse command line arguments
if [[ $# -eq 0 ]]; then
    show_help
    exit 1
fi

ACTION=$1
shift

while [[ $# -gt 0 ]]; do
    case $1 in
        -h|--help)
            show_help
            exit 0
            ;;
        -e|--env-file)
            ENV_FILE="$2"
            shift 2
            ;;
        -f|--compose-file)
            COMPOSE_FILE="$2"
            shift 2
            ;;
        --timestamp)
            TIMESTAMP_MODE=true
            shift
            ;;
        --fixed)
            TIMESTAMP_MODE=false
            shift
            ;;
        *)
            echo -e "${RED}Unknown option: $1${NC}"
            show_help
            exit 1
            ;;
    esac
done

# Set defaults
ENV_FILE=${ENV_FILE:-$DEFAULT_ENV_FILE}
COMPOSE_FILE=${COMPOSE_FILE:-$DEFAULT_COMPOSE_FILE}

# Function to check if Docker is running
check_docker() {
    if ! docker info >/dev/null 2>&1; then
        echo -e "${RED}❌ Docker is not running or not accessible${NC}"
        exit 1
    fi
}

# Function to generate timestamp
generate_timestamp() {
    date +"%Y%m%d_%H%M%S"
}

# Function to setup timestamp for deployment
setup_deployment_timestamp() {
    if [[ "$TIMESTAMP_MODE" == true ]]; then
        DEPLOYMENT_TIMESTAMP=$(generate_timestamp)
        echo -e "${BLUE}🕒 Generated timestamp: ${DEPLOYMENT_TIMESTAMP}${NC}"
        export TIMESTAMP="$DEPLOYMENT_TIMESTAMP"
    else
        export TIMESTAMP="default"
        echo -e "${BLUE}📁 Using fixed directories: default${NC}"
    fi
}

# Function to load environment variables
load_env() {
    if [[ -f "$ENV_FILE" ]]; then
        echo -e "${BLUE}📝 Loading environment from: $ENV_FILE${NC}"
        set -a
        source "$ENV_FILE"
        set +a
        
        # Override timestamp based on mode
        setup_deployment_timestamp
    else
        echo -e "${YELLOW}⚠️  Environment file not found: $ENV_FILE${NC}"
        if [[ "$ACTION" != "setup" ]]; then
            echo -e "${RED}❌ Environment file required for $ACTION action${NC}"
            exit 1
        fi
    fi
}

# Function to setup production environment
setup_production() {
    echo -e "${BLUE}🔧 Setting up production environment...${NC}"
    
    # Copy example env file if it doesn't exist
    if [[ ! -f ".env.production" && -f "production.env.example" ]]; then
        echo -e "${YELLOW}📋 Copying production.env.example to .env.production${NC}"
        cp production.env.example .env.production
        echo -e "${YELLOW}⚠️  Please edit .env.production with your configuration${NC}"
    fi
    
    # Load environment to get directory paths
    if [[ -f ".env.production" ]]; then
        set -a
        source .env.production
        set +a
        
        # Create required directories
        echo -e "${YELLOW}📁 Creating required directories...${NC}"
        
        if [[ -n "$HOST_DATA_DIR" ]]; then
            echo "Creating data directories in: $HOST_DATA_DIR"
            # Create both default and sample timestamp directories
            sudo mkdir -p "$HOST_DATA_DIR"/default/{uploads,results,tmp,archives}
            sudo mkdir -p "$HOST_DATA_DIR"/sample_timestamp_{uploads,results,tmp,archives}
            sudo chown -R 1000:1000 "$HOST_DATA_DIR"
            sudo chmod -R 755 "$HOST_DATA_DIR"
        fi
        
        if [[ -n "$HOST_LOGS_DIR" ]]; then
            echo "Creating logs directory: $HOST_LOGS_DIR"
            # Create both default and sample timestamp log directories  
            sudo mkdir -p "$HOST_LOGS_DIR"/default
            sudo mkdir -p "$HOST_LOGS_DIR"/sample_timestamp
            sudo chown -R 1000:1000 "$HOST_LOGS_DIR"
            sudo chmod -R 755 "$HOST_LOGS_DIR"
        fi
        
        echo -e "${GREEN}✅ Production environment setup completed${NC}"
        echo -e "${BLUE}📝 Next steps:${NC}"
        echo "  1. Edit .env.production with your specific configuration"
        echo "  2. Pull the Docker image: docker pull \$OCR_IMAGE_NAME"
        echo "  3. Deploy with fixed directories: $0 deploy -e .env.production"
        echo "  4. Or deploy with timestamps: $0 deploy --timestamp -e .env.production"
    else
        echo -e "${RED}❌ Please create .env.production file first${NC}"
        exit 1
    fi
}

# Function to create directories for timestamp deployment
create_timestamp_directories() {
    if [[ "$TIMESTAMP_MODE" == true && -n "$DEPLOYMENT_TIMESTAMP" ]]; then
        echo -e "${YELLOW}📁 Creating timestamped directories...${NC}"
        
        # Load environment to get paths
        if [[ -f "$ENV_FILE" ]]; then
            set -a
            source "$ENV_FILE"
            set +a
        fi
        
        if [[ -n "$HOST_DATA_DIR" ]]; then
            sudo mkdir -p "$HOST_DATA_DIR/${DEPLOYMENT_TIMESTAMP}"/{uploads,results,tmp,archives}
            sudo chown -R 1000:1000 "$HOST_DATA_DIR/${DEPLOYMENT_TIMESTAMP}"
            sudo chmod -R 755 "$HOST_DATA_DIR/${DEPLOYMENT_TIMESTAMP}"
            echo "  Created: $HOST_DATA_DIR/${DEPLOYMENT_TIMESTAMP}/"
        fi
        
        if [[ -n "$HOST_LOGS_DIR" ]]; then
            sudo mkdir -p "$HOST_LOGS_DIR/${DEPLOYMENT_TIMESTAMP}"
            sudo chown -R 1000:1000 "$HOST_LOGS_DIR/${DEPLOYMENT_TIMESTAMP}"
            sudo chmod -R 755 "$HOST_LOGS_DIR/${DEPLOYMENT_TIMESTAMP}"
            echo "  Created: $HOST_LOGS_DIR/${DEPLOYMENT_TIMESTAMP}/"
        fi
        
        # Create deployment info file
        if [[ -n "$HOST_DATA_DIR" ]]; then
            cat > "/tmp/deploy_info_${DEPLOYMENT_TIMESTAMP}.json" << EOF
{
    "timestamp": "$DEPLOYMENT_TIMESTAMP",
    "deployment_time": "$(date -Iseconds)",
    "deployment_mode": "timestamped",
    "host_data_dir": "$HOST_DATA_DIR",
    "host_logs_dir": "${HOST_LOGS_DIR:-$HOST_DATA_DIR}",
    "image_name": "${OCR_IMAGE_NAME:-ocr-backend:latest}"
}
EOF
            sudo mv "/tmp/deploy_info_${DEPLOYMENT_TIMESTAMP}.json" "$HOST_DATA_DIR/${DEPLOYMENT_TIMESTAMP}/deploy_info.json"
            sudo chown 1000:1000 "$HOST_DATA_DIR/${DEPLOYMENT_TIMESTAMP}/deploy_info.json"
        fi
    fi
}

# Function to deploy service
deploy_service() {
    echo -e "${BLUE}🚀 Deploying OCR Backend...${NC}"
    check_docker
    load_env
    
    if [[ ! -f "$COMPOSE_FILE" ]]; then
        echo -e "${RED}❌ Compose file not found: $COMPOSE_FILE${NC}"
        exit 1
    fi
    
    # Create timestamped directories if needed
    create_timestamp_directories
    
    echo -e "${YELLOW}📥 Pulling latest images...${NC}"
    TIMESTAMP="$TIMESTAMP" docker-compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" pull
    
    echo -e "${YELLOW}🔄 Starting services...${NC}"
    TIMESTAMP="$TIMESTAMP" docker-compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" up -d
    
    echo -e "${GREEN}✅ Deployment completed${NC}"
    
    if [[ "$TIMESTAMP_MODE" == true ]]; then
        echo -e "${BLUE}📁 Timestamped deployment: ${DEPLOYMENT_TIMESTAMP}${NC}"
        echo -e "${BLUE}📂 Data directory: ${HOST_DATA_DIR}/${DEPLOYMENT_TIMESTAMP}${NC}"
    fi
    
    # Wait a moment and check status
    sleep 5
    echo -e "${BLUE}📊 Service Status:${NC}"
    TIMESTAMP="$TIMESTAMP" docker-compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" ps
}

# Function to stop service
stop_service() {
    echo -e "${BLUE}🛑 Stopping OCR Backend...${NC}"
    check_docker
    load_env
    
    TIMESTAMP="$TIMESTAMP" docker-compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" down
    echo -e "${GREEN}✅ Service stopped${NC}"
}

# Function to restart service
restart_service() {
    echo -e "${BLUE}🔄 Restarting OCR Backend...${NC}"
    stop_service
    deploy_service
}

# Function to show status
show_status() {
    echo -e "${BLUE}📊 OCR Backend Status${NC}"
    check_docker
    load_env
    
    echo -e "${BLUE}Container Status:${NC}"
    TIMESTAMP="$TIMESTAMP" docker-compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" ps
    
    echo -e "${BLUE}Resource Usage:${NC}"
    docker stats --no-stream --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}" | grep ocr || echo "No containers running"
    
    if [[ "$TIMESTAMP_MODE" == true ]]; then
        echo -e "${BLUE}📁 Current Deployment: ${DEPLOYMENT_TIMESTAMP}${NC}"
        echo -e "${BLUE}📂 Data Directory: ${HOST_DATA_DIR}/${DEPLOYMENT_TIMESTAMP}${NC}"
    else
        echo -e "${BLUE}📁 Deployment Mode: Fixed directories${NC}"
        echo -e "${BLUE}📂 Data Directory: ${HOST_DATA_DIR}/default${NC}"
    fi
}

# Function to show logs
show_logs() {
    echo -e "${BLUE}📋 OCR Backend Logs${NC}"
    check_docker
    load_env
    
    if [[ "$TIMESTAMP_MODE" == true ]]; then
        echo -e "${BLUE}📁 Showing logs for timestamped deployment: ${DEPLOYMENT_TIMESTAMP}${NC}"
    fi
    
    TIMESTAMP="$TIMESTAMP" docker-compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" logs -f
}

# Function to cleanup
cleanup_service() {
    echo -e "${BLUE}🧹 Cleaning up OCR Backend...${NC}"
    check_docker
    
    echo -e "${YELLOW}Removing stopped containers...${NC}"
    docker container prune -f
    
    echo -e "${YELLOW}Removing unused images...${NC}"
    docker image prune -f
    
    echo -e "${YELLOW}Removing unused volumes...${NC}"
    docker volume prune -f
    
    echo -e "${GREEN}✅ Cleanup completed${NC}"
}

# Execute action based on input
case $ACTION in
    setup)
        setup_production
        ;;
    deploy)
        deploy_service
        ;;
    stop)
        stop_service
        ;;
    restart)
        restart_service
        ;;
    status)
        show_status
        ;;
    logs)
        show_logs
        ;;
    cleanup)
        cleanup_service
        ;;
    *)
        echo -e "${RED}Unknown action: $ACTION${NC}"
        show_help
        exit 1
        ;;
esac 