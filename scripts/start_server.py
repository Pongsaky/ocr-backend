#!/usr/bin/env python3

"""
OCR Backend - Server Startup Script
Provides options for starting the server with regular or timestamped volumes
"""

import os
import sys
import subprocess
import argparse
from datetime import datetime
from pathlib import Path

def run_command(command, shell=True):
    """Run a command and return the result"""
    try:
        result = subprocess.run(command, shell=shell, capture_output=True, text=True)
        return result.returncode == 0, result.stdout, result.stderr
    except Exception as e:
        return False, "", str(e)

def start_with_timestamp():
    """Start server with timestamped volumes using the bash script"""
    script_path = Path(__file__).parent / "launch_with_timestamp.sh"
    
    if not script_path.exists():
        print("❌ launch_with_timestamp.sh not found!")
        return False
        
    print("🚀 Starting OCR Backend with timestamped volumes...")
    
    # Make sure script is executable
    os.chmod(script_path, 0o755)
    
    # Run the bash script
    success, stdout, stderr = run_command(str(script_path))
    
    if stdout:
        print(stdout)
    if stderr:
        print(stderr)
        
    return success

def start_regular():
    """Start server with regular volume mounting (fallback to default)"""
    print("🚀 Starting OCR Backend with default volumes...")
    
    # Set TIMESTAMP to 'default' to use default directory
    env = os.environ.copy()
    env['TIMESTAMP'] = 'default'
    
    # Create default directories
    default_dirs = ['./data/default/uploads', './data/default/results', './data/default/tmp', './data/default/logs']
    for dir_path in default_dirs:
        Path(dir_path).mkdir(parents=True, exist_ok=True)
        
    # Determine compose command
    compose_cmd = "docker-compose"
    if subprocess.run(['docker', 'compose', 'version'], capture_output=True).returncode == 0:
        compose_cmd = "docker compose"
    
    # Start the services
    cmd = f"{compose_cmd} up --build -d"
    success, stdout, stderr = run_command(cmd)
    
    if stdout:
        print(stdout)
    if stderr and "WARNING" not in stderr.upper():
        print(stderr)
        
    if success:
        print("✅ OCR Backend started successfully!")
        print("🌐 API available at:")
        print("  http://localhost:8000")
        print("  http://localhost:8000/docs (Swagger UI)")
        print(f"\n🔍 View logs with: {compose_cmd} logs -f ocr-backend")
        print(f"🛑 Stop services with: {compose_cmd} down")
    else:
        print("❌ Failed to start OCR Backend")
        
    return success

def stop_services():
    """Stop running services"""
    print("🛑 Stopping OCR Backend services...")
    
    # Determine compose command
    compose_cmd = "docker-compose"
    if subprocess.run(['docker', 'compose', 'version'], capture_output=True).returncode == 0:
        compose_cmd = "docker compose"
    
    success, stdout, stderr = run_command(f"{compose_cmd} down")
    
    if stdout:
        print(stdout)
    if stderr and "WARNING" not in stderr.upper():
        print(stderr)
        
    if success:
        print("✅ Services stopped successfully!")
    else:
        print("❌ Failed to stop services")
        
    return success

def show_status():
    """Show status of running services"""
    # Determine compose command
    compose_cmd = "docker-compose"
    if subprocess.run(['docker', 'compose', 'version'], capture_output=True).returncode == 0:
        compose_cmd = "docker compose"
    
    print("📊 Service Status:")
    success, stdout, stderr = run_command(f"{compose_cmd} ps")
    
    if stdout:
        print(stdout)
    if stderr and "WARNING" not in stderr.upper():
        print(stderr)

def main():
    parser = argparse.ArgumentParser(description='OCR Backend Server Startup Script')
    parser.add_argument('action', choices=['start', 'start-timestamp', 'stop', 'status'], 
                      help='Action to perform')
    parser.add_argument('--verbose', '-v', action='store_true', help='Verbose output')
    
    args = parser.parse_args()
    
    print("🔧 OCR Backend Server Manager")
    print("=" * 40)
    
    if args.action == 'start':
        success = start_regular()
    elif args.action == 'start-timestamp':
        success = start_with_timestamp()
    elif args.action == 'stop':
        success = stop_services()
    elif args.action == 'status':
        show_status()
        success = True
    else:
        parser.print_help()
        success = False
        
    if not success and args.action in ['start', 'start-timestamp', 'stop']:
        sys.exit(1)

if __name__ == "__main__":
    main() 