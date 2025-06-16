#!/usr/bin/env python3
"""
Test runner script for OCR Backend API.
"""

import sys
import subprocess
import argparse
from pathlib import Path


def run_command(command: list, description: str) -> bool:
    """Run a command and return success status."""
    print(f"\n{'='*60}")
    print(f"Running: {description}")
    print(f"Command: {' '.join(command)}")
    print(f"{'='*60}")
    
    try:
        result = subprocess.run(command, check=True, capture_output=False)
        print(f"✅ {description} completed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ {description} failed with exit code {e.returncode}")
        return False


def main():
    """Main test runner function."""
    parser = argparse.ArgumentParser(description="Run tests for OCR Backend API")
    parser.add_argument(
        "--unit", 
        action="store_true", 
        help="Run only unit tests"
    )
    parser.add_argument(
        "--integration", 
        action="store_true", 
        help="Run only integration tests"
    )
    parser.add_argument(
        "--coverage", 
        action="store_true", 
        help="Run tests with coverage report"
    )
    parser.add_argument(
        "--verbose", 
        action="store_true", 
        help="Run tests in verbose mode"
    )
    parser.add_argument(
        "--fast", 
        action="store_true", 
        help="Run tests without coverage (faster)"
    )
    parser.add_argument(
        "--specific", 
        type=str, 
        help="Run specific test file or test function"
    )
    
    args = parser.parse_args()
    
    # Base pytest command
    base_cmd = ["poetry", "run", "pytest"]
    
    # Determine test path
    if args.unit:
        test_path = "tests/unit"
    elif args.integration:
        test_path = "tests/integration"
    elif args.specific:
        test_path = args.specific
    else:
        test_path = "tests"
    
    # Build command
    cmd = base_cmd + [test_path]
    
    # Add options
    if args.verbose:
        cmd.append("-v")
    
    if args.coverage and not args.fast:
        cmd.extend(["--cov=app", "--cov-report=term-missing", "--cov-report=html"])
    elif not args.fast:
        cmd.extend(["--cov=app"])
    
    if args.fast:
        cmd.append("--no-cov")
    
    # Run tests
    success = run_command(cmd, f"Tests ({test_path})")
    
    if success:
        print(f"\n🎉 All tests passed!")
        
        if args.coverage and not args.fast:
            print("\n📊 Coverage report generated:")
            print("  - Terminal: See above")
            print("  - HTML: htmlcov/index.html")
    else:
        print(f"\n💥 Some tests failed!")
        sys.exit(1)


if __name__ == "__main__":
    main() 