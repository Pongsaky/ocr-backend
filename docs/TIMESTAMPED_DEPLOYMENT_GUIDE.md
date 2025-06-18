# OCR Backend - Timestamped Deployment Guide

## Overview

The OCR Backend now supports **timestamped volume mounting** for Docker deployments, providing isolated data storage for each launch. This enables better debugging, prevents data mixing between deployments, and simplifies log management.

## 🚀 Quick Start

### Launch with Timestamped Volumes (Recommended)

```bash
# Simple launch - creates timestamped directories automatically
./scripts/launch_with_timestamp.sh

# Alternative using Python script
python scripts/start_server.py start-timestamp
```

### Traditional Launch (Development)

```bash
# Uses fixed 'default' directory
python scripts/start_server.py start
```

## 📁 Directory Structure

### Timestamped Structure
```
project-root/
├── data/
│   ├── 20241201_143022/           # Launch timestamp: YYYYMMDD_HHMMSS
│   │   ├── uploads/               # User uploaded files
│   │   ├── results/               # OCR processing results
│   │   ├── tmp/                   # Temporary processing files
│   │   ├── logs/                  # Application logs
│   │   └── launch_info.json       # Launch metadata
│   ├── 20241201_150315/           # Next launch
│   │   └── ...
│   └── archives/                  # Archived directories
│       └── ocr-backend-20241201_143022.tar.gz
```

### Launch Info Format
Each timestamped directory contains a `launch_info.json` file:
```json
{
  "timestamp": "20241201_143022",
  "data_dir": "./data/20241201_143022",
  "started_at": "2024-12-01T14:30:22+07:00"
}
```

## 🛠️ Management Commands

### Directory Management

```bash
# List all timestamped directories
python scripts/manage_data_dirs.py list

# Detailed view with file counts and sizes
python scripts/manage_data_dirs.py list --verbose

# Example output:
📁 Found 3 timestamped directories:

🕒 20241201_150315
   💾 2.3MB | 📄 15 files

🕒 20241201_143022
   💾 5.7MB | 📄 28 files

🕒 20241130_162430
   💾 1.1MB | 📄 8 files
```

### Cleanup Operations

```bash
# Remove directories older than 7 days (default)
python scripts/manage_data_dirs.py cleanup --days 7

# Dry run to preview what would be removed
python scripts/manage_data_dirs.py cleanup --days 7 --dry-run

# Clean up directories older than 3 days
python scripts/manage_data_dirs.py cleanup --days 3
```

### Archive Management

```bash
# Archive a specific directory (creates compressed tar.gz)
python scripts/manage_data_dirs.py archive 20241201_143022

# Archive and remove original directory
python scripts/manage_data_dirs.py archive 20241201_143022 --remove
```

### Disk Usage Analysis

```bash
# Show summary of all directories
python scripts/manage_data_dirs.py usage

# Example output:
💾 Disk Usage Summary:
   Total Size: 47.2MB
   Total Directories: 5

📊 Top 5 largest directories:
   1. 20241201_143022 - 15.8MB
   2. 20241201_150315 - 12.3MB
   3. 20241130_162430 - 8.9MB
   4. 20241130_140215 - 6.1MB
   5. 20241129_094530 - 4.1MB
```

## 🔧 Service Management

### Starting Services

```bash
# Start with timestamped volumes (recommended)
python scripts/start_server.py start-timestamp

# Start with default volumes (development)
python scripts/start_server.py start

# Check if services are running
python scripts/start_server.py status
```

### Stopping Services

```bash
# Stop all services
python scripts/start_server.py stop

# Check status after stopping
python scripts/start_server.py status
```

### Viewing Logs

```bash
# Live log viewing
docker-compose logs -f ocr-backend

# Log files are also available in the timestamped directory
tail -f data/20241201_143022/logs/ocr-backend.log
```

## 🐳 Docker Volume Configuration

### How It Works

The `docker-compose.yml` uses environment variable substitution:

```yaml
volumes:
  - ./data/${TIMESTAMP:-default}/uploads:/app/uploads
  - ./data/${TIMESTAMP:-default}/results:/app/results
  - ./data/${TIMESTAMP:-default}/tmp:/app/tmp
  - ./data/${TIMESTAMP:-default}/logs:/app/logs
```

- `${TIMESTAMP}` is set by the launch scripts
- Falls back to `default` if TIMESTAMP is not set
- Creates bind mounts to host filesystem for easy access

### Manual Docker Launch

```bash
# Set timestamp and create directories
export TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
mkdir -p ./data/${TIMESTAMP}/{uploads,results,tmp,logs}

# Launch with specific timestamp
docker-compose up --build -d
```

## 📊 Monitoring and Debugging

### Access Files from Specific Launch

```bash
# Navigate to specific launch data
cd data/20241201_143022

# View uploaded files
ls -la uploads/

# Check processing results
ls -la results/

# View logs
tail -f logs/ocr-backend.log
```

### Health Checks

```bash
# Check container health
docker-compose ps

# API health endpoint
curl http://localhost:8000/health

# View container logs
docker-compose logs ocr-backend
```

## 🔄 Migration from Old Setup

If you have existing data in the old structure:

```bash
# Create a timestamped directory for existing data
MIGRATION_TIMESTAMP=$(date +"%Y%m%d_%H%M%S")_migration
mkdir -p ./data/${MIGRATION_TIMESTAMP}

# Move existing directories
mv uploads ./data/${MIGRATION_TIMESTAMP}/ 2>/dev/null || true
mv results ./data/${MIGRATION_TIMESTAMP}/ 2>/dev/null || true
mv tmp ./data/${MIGRATION_TIMESTAMP}/ 2>/dev/null || true
mv logs ./data/${MIGRATION_TIMESTAMP}/ 2>/dev/null || true

# Create launch info
echo "{\"timestamp\": \"${MIGRATION_TIMESTAMP}\", \"data_dir\": \"./data/${MIGRATION_TIMESTAMP}\", \"started_at\": \"$(date -Iseconds)\", \"note\": \"Migrated from old structure\"}" > ./data/${MIGRATION_TIMESTAMP}/launch_info.json

echo "Migration completed. Data moved to: ./data/${MIGRATION_TIMESTAMP}"
```

## 🚨 Troubleshooting

### Common Issues

1. **Permission Errors**
   ```bash
   # Fix script permissions
   chmod +x scripts/launch_with_timestamp.sh
   chmod +x scripts/start_server.py
   chmod +x scripts/manage_data_dirs.py
   ```

2. **Directory Not Created**
   ```bash
   # Check if the timestamp directory was created
   ls -la data/
   
   # Manually create if needed
   mkdir -p data/$(date +"%Y%m%d_%H%M%S")/{uploads,results,tmp,logs}
   ```

3. **Docker Compose Not Found**
   ```bash
   # The script tries both commands automatically
   docker-compose --version  # Traditional
   docker compose version    # New Docker CLI
   ```

4. **TIMESTAMP Variable Not Set**
   ```bash
   # Check if variable is set
   echo $TIMESTAMP
   
   # Manually set if needed
   export TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
   ```

### Log Analysis

```bash
# View launch script logs
./scripts/launch_with_timestamp.sh

# Check Docker Compose logs
docker-compose logs ocr-backend

# Check application logs in timestamped directory
tail -f data/TIMESTAMP/logs/ocr-backend.log
```

## 🎯 Best Practices

1. **Regular Cleanup**: Set up a cron job to clean old directories
   ```bash
   # Add to crontab (daily cleanup of 7+ day old directories)
   0 2 * * * cd /path/to/ocr-backend && python scripts/manage_data_dirs.py cleanup --days 7
   ```

2. **Archive Important Runs**: Before cleanup, archive important directories
   ```bash
   python scripts/manage_data_dirs.py archive TIMESTAMP --remove
   ```

3. **Monitor Disk Usage**: Regularly check disk usage
   ```bash
   python scripts/manage_data_dirs.py usage
   ```

4. **Use Descriptive Timestamps**: The format `YYYYMMDD_HHMMSS` makes directories easy to sort and identify

5. **Backup Archives**: Consider backing up the `data/archives/` directory to external storage

## 📈 Benefits Summary

✅ **Isolation**: Each deployment has its own data space  
✅ **Debugging**: Easy to trace issues to specific launches  
✅ **Cleanup**: Automated tools for maintenance  
✅ **Archiving**: Compress and store important runs  
✅ **Monitoring**: Built-in disk usage tracking  
✅ **Flexibility**: Can still use traditional mounting when needed  
✅ **Backward Compatible**: Existing workflows still work with `TIMESTAMP=default`