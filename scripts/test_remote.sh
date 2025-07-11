#!/bin/bash

# Script for testing against remote deployed instances

set -e

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Help function
show_help() {
    echo "Usage: ./scripts/test_remote.sh [OPTIONS] [PYTEST_ARGS]"
    echo ""
    echo "Options:"
    echo "  -u, --url URL         Remote API URL (required)"
    echo "  -k, --key KEY         API key for authentication"
    echo "  -t, --timeout SECONDS Timeout for API calls (default: 30)"
    echo "  -h, --help           Show this help message"
    echo ""
    echo "Examples:"
    echo "  # Basic usage"
    echo "  ./scripts/test_remote.sh -u https://api.example.com"
    echo ""
    echo "  # With authentication"
    echo "  ./scripts/test_remote.sh -u https://api.example.com -k your-api-key"
    echo ""
    echo "  # Run specific test file"
    echo "  ./scripts/test_remote.sh -u https://api.example.com tests/test_remote_deployment.py"
    echo ""
    echo "  # With pytest options"
    echo "  ./scripts/test_remote.sh -u https://api.example.com -- -v -s"
}

# Parse arguments
REMOTE_URL=""
API_KEY=""
TIMEOUT="30"
PYTEST_ARGS=()

while [[ $# -gt 0 ]]; do
    case $1 in
        -u|--url)
            REMOTE_URL="$2"
            shift 2
            ;;
        -k|--key)
            API_KEY="$2"
            shift 2
            ;;
        -t|--timeout)
            TIMEOUT="$2"
            shift 2
            ;;
        -h|--help)
            show_help
            exit 0
            ;;
        --)
            shift
            PYTEST_ARGS=("$@")
            break
            ;;
        *)
            PYTEST_ARGS+=("$1")
            shift
            ;;
    esac
done

# Validate required arguments
if [ -z "$REMOTE_URL" ]; then
    echo -e "${RED}Error: Remote URL is required${NC}"
    echo ""
    show_help
    exit 1
fi

# Export environment variables
export REMOTE_API_URL="$REMOTE_URL"
export REMOTE_API_TIMEOUT="$TIMEOUT"

if [ -n "$API_KEY" ]; then
    export REMOTE_API_KEY="$API_KEY"
fi

# Display configuration
echo -e "${GREEN}Remote Testing Configuration:${NC}"
echo -e "  URL: ${YELLOW}$REMOTE_URL${NC}"
echo -e "  Timeout: ${YELLOW}${TIMEOUT}s${NC}"
if [ -n "$API_KEY" ]; then
    echo -e "  API Key: ${YELLOW}***${API_KEY: -4}${NC} (last 4 chars)"
fi
echo ""

# Check if remote is accessible
echo -e "${GREEN}Checking remote API health...${NC}"
if curl -s -o /dev/null -w "%{http_code}" "$REMOTE_URL/health" | grep -q "200"; then
    echo -e "${GREEN}✓ Remote API is healthy${NC}"
else
    echo -e "${YELLOW}⚠ Warning: Could not verify remote API health${NC}"
    echo "  Continuing with tests anyway..."
fi
echo ""

# Run tests
echo -e "${GREEN}Running tests against remote deployment...${NC}"
if [ ${#PYTEST_ARGS[@]} -eq 0 ]; then
    # Default: run all tests
    poetry run pytest tests/ -v
else
    # Run with custom arguments
    poetry run pytest "${PYTEST_ARGS[@]}"
fi

# Capture exit code
EXIT_CODE=$?

# Clean up environment variables
unset REMOTE_API_URL
unset REMOTE_API_KEY
unset REMOTE_API_TIMEOUT

# Summary
echo ""
if [ $EXIT_CODE -eq 0 ]; then
    echo -e "${GREEN}✓ All tests passed!${NC}"
else
    echo -e "${RED}✗ Some tests failed${NC}"
fi

exit $EXIT_CODE