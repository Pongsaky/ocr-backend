#!/bin/bash

# Comprehensive deployment testing script
# Tests the deployed OCR API with various test suites

set -e

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

# Default values
REMOTE_URL=""
API_KEY=""
TIMEOUT="60"
TEST_SUITES="all"
VERBOSE=false

show_help() {
    echo "Usage: ./scripts/run_deployment_tests.sh [OPTIONS]"
    echo ""
    echo "Comprehensive testing for deployed OCR API"
    echo ""
    echo "Options:"
    echo "  -u, --url URL         Remote API URL (required)"
    echo "  -k, --key KEY         API key for authentication"
    echo "  -t, --timeout SECONDS Timeout for API calls (default: 60)"
    echo "  -s, --suite SUITE     Test suite to run (default: all)"
    echo "  -v, --verbose         Verbose output"
    echo "  -h, --help           Show this help"
    echo ""
    echo "Test Suites:"
    echo "  health       - Basic health check"
    echo "  basic        - Simple functionality tests"
    echo "  real-api     - Real API execution with completion verification"
    echo "  workflows    - Complete user journey workflows"
    echo "  streaming    - Real-time streaming validation"
    echo "  quality      - Data quality and accuracy testing"
    echo "  performance  - Performance and load testing"
    echo "  all          - Run all test suites (default)"
    echo ""
    echo "Examples:"
    echo "  # Basic health check"
    echo "  ./scripts/run_deployment_tests.sh -u https://api.example.com -s health"
    echo ""
    echo "  # Full test suite"
    echo "  ./scripts/run_deployment_tests.sh -u https://api.example.com"
    echo ""
    echo "  # With authentication"
    echo "  ./scripts/run_deployment_tests.sh -u https://api.example.com -k your-key"
}

# Parse arguments
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
        -s|--suite)
            TEST_SUITES="$2"
            shift 2
            ;;
        -v|--verbose)
            VERBOSE=true
            shift
            ;;
        -h|--help)
            show_help
            exit 0
            ;;
        *)
            echo -e "${RED}Unknown option: $1${NC}"
            show_help
            exit 1
            ;;
    esac
done

# Validate required arguments
if [ -z "$REMOTE_URL" ]; then
    echo -e "${RED}Error: Remote URL is required${NC}"
    show_help
    exit 1
fi

# Set environment variables
export REMOTE_API_URL="$REMOTE_URL"
export REMOTE_API_TIMEOUT="$TIMEOUT"

if [ -n "$API_KEY" ]; then
    export REMOTE_API_KEY="$API_KEY"
fi

# Display configuration
echo -e "${BLUE}🚀 OCR API Deployment Testing${NC}"
echo -e "${BLUE}================================${NC}"
echo -e "URL: ${YELLOW}$REMOTE_URL${NC}"
echo -e "Timeout: ${YELLOW}${TIMEOUT}s${NC}"
echo -e "Test Suite: ${YELLOW}$TEST_SUITES${NC}"
if [ -n "$API_KEY" ]; then
    echo -e "API Key: ${YELLOW}***${API_KEY: -4}${NC}"
fi
echo ""

# Test results tracking
TOTAL_SUITES=0
PASSED_SUITES=0
FAILED_SUITES=0

run_test_suite() {
    local suite_name="$1"
    local test_file="$2"
    local description="$3"
    
    echo -e "${BLUE}📋 Running $description${NC}"
    echo -e "${BLUE}$('=' | tr '=' '=' | head -c 50)${NC}"
    
    TOTAL_SUITES=$((TOTAL_SUITES + 1))
    
    if [ "$VERBOSE" = true ]; then
        PYTEST_ARGS="-v -s"
    else
        PYTEST_ARGS="-v"
    fi
    
    if poetry run pytest "$test_file" $PYTEST_ARGS; then
        echo -e "${GREEN}✅ $suite_name PASSED${NC}"
        PASSED_SUITES=$((PASSED_SUITES + 1))
        return 0
    else
        echo -e "${RED}❌ $suite_name FAILED${NC}"
        FAILED_SUITES=$((FAILED_SUITES + 1))
        return 1
    fi
}

# Health check first
echo -e "${YELLOW}🏥 Checking API health...${NC}"
if poetry run python -c "
import sys
sys.path.insert(0, '.')
from tests.remote_client import RemoteTestClient
client = RemoteTestClient()
try:
    response = client.get('/health')
    if response.status_code == 200:
        data = response.json()
        print(f'✅ API is healthy: {data.get(\"status\", \"unknown\")}')
        print(f'   Service: {data.get(\"service\", \"unknown\")}')
        print(f'   Version: {data.get(\"version\", \"unknown\")}')
        exit(0)
    else:
        print(f'❌ Health check failed: {response.status_code}')
        exit(1)
except Exception as e:
    print(f'❌ Cannot connect to API: {e}')
    exit(1)
"; then
    echo ""
else
    echo -e "${RED}❌ API health check failed. Stopping tests.${NC}"
    exit 1
fi

# Run test suites based on selection
case "$TEST_SUITES" in
    "health")
        echo -e "${GREEN}Health check completed successfully!${NC}"
        ;;
    
    "basic")
        run_test_suite "Basic Tests" "tests/test_remote_simple.py" "Basic API Functionality"
        ;;
    
    "real-api")
        run_test_suite "Real API Execution" "tests/test_real_api_execution.py" "Real API Execution with Completion Verification"
        ;;
    
    "workflows")
        run_test_suite "User Workflows" "tests/test_workflow_journeys.py" "Complete User Journey Workflows"
        ;;
    
    "streaming")
        run_test_suite "Streaming Validation" "tests/test_streaming_validation.py" "Real-time Streaming Validation"
        ;;
    
    "quality")
        run_test_suite "Data Quality" "tests/test_data_quality.py" "Data Quality and OCR Accuracy Testing"
        ;;
    
    "performance")
        echo -e "${BLUE}🔄 Running Real End-to-End Performance Tests...${NC}"
        run_test_suite "Real Performance Testing" "tests/test_real_performance.py" "Real End-to-End OCR Performance with Completion Tracking"
        
        echo ""
        echo -e "${BLUE}🔄 Running Load Testing with Reporting...${NC}"
        run_test_suite "Performance with Reporting" "tests/test_performance_with_reporting.py" "Performance and Load Testing with Detailed Reports"
        ;;
    
    "all")
        echo -e "${YELLOW}🔄 Running complete test suite...${NC}"
        echo ""
        
        # Run all test suites
        run_test_suite "Basic Tests" "tests/test_remote_simple.py" "Basic API Functionality"
        echo ""
        
        run_test_suite "Real API Execution" "tests/test_real_api_execution.py" "Real API Execution with Completion Verification"
        echo ""
        
        run_test_suite "User Workflows" "tests/test_workflow_journeys.py" "Complete User Journey Workflows"
        echo ""
        
        run_test_suite "Streaming Validation" "tests/test_streaming_validation.py" "Real-time Streaming Validation"
        echo ""
        
        run_test_suite "Data Quality" "tests/test_data_quality.py" "Data Quality and OCR Accuracy Testing"
        echo ""
        
        echo -e "${BLUE}🔄 Running Real End-to-End Performance Tests...${NC}"
        run_test_suite "Real Performance Testing" "tests/test_real_performance.py" "Real End-to-End OCR Performance with Completion Tracking"
        ;;
    
    *)
        echo -e "${RED}Unknown test suite: $TEST_SUITES${NC}"
        show_help
        exit 1
        ;;
esac

# Final summary
echo ""
echo -e "${BLUE}📊 Test Summary${NC}"
echo -e "${BLUE}===============${NC}"
echo -e "Total suites: $TOTAL_SUITES"
echo -e "Passed: ${GREEN}$PASSED_SUITES${NC}"
echo -e "Failed: ${RED}$FAILED_SUITES${NC}"

if [ $FAILED_SUITES -eq 0 ]; then
    echo -e "${GREEN}🎉 All tests PASSED!${NC}"
    echo ""
    echo -e "${GREEN}Your deployment at $REMOTE_URL is working correctly!${NC}"
    exit 0
else
    echo -e "${RED}⚠️  Some tests FAILED${NC}"
    echo ""
    echo -e "${YELLOW}Check the test output above for details.${NC}"
    exit 1
fi