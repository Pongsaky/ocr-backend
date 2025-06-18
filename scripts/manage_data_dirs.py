#!/usr/bin/env python3

"""
OCR Backend - Data Directory Management Script
Manage timestamped data directories created by launch_with_timestamp.sh
"""

import os
import sys
import shutil
import json
import argparse
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Optional
import tarfile

# Add the project root to Python path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

class DataDirectoryManager:
    """Manages timestamped data directories for OCR Backend"""
    
    def __init__(self, base_data_dir: str = "./data"):
        self.base_data_dir = Path(base_data_dir)
        self.archive_dir = self.base_data_dir / "archives"
        
    def list_directories(self) -> List[Dict]:
        """List all timestamped data directories with their info"""
        directories = []
        
        if not self.base_data_dir.exists():
            return directories
            
        for item in self.base_data_dir.iterdir():
            if item.is_dir() and item.name != "archives" and item.name != "default":
                dir_info = self._get_directory_info(item)
                directories.append(dir_info)
                
        # Sort by timestamp (newest first)
        directories.sort(key=lambda x: x['timestamp'], reverse=True)
        return directories
    
    def _get_directory_info(self, dir_path: Path) -> Dict:
        """Get information about a timestamped directory"""
        launch_info_file = dir_path / "launch_info.json"
        
        # Try to load launch info
        launch_info = {}
        if launch_info_file.exists():
            try:
                with open(launch_info_file, 'r') as f:
                    launch_info = json.load(f)
            except (json.JSONDecodeError, IOError):
                pass
        
        # Calculate directory size
        total_size = sum(f.stat().st_size for f in dir_path.rglob('*') if f.is_file())
        
        # Count files
        file_counts = {
            'uploads': len(list((dir_path / "uploads").glob('*'))) if (dir_path / "uploads").exists() else 0,
            'results': len(list((dir_path / "results").glob('*'))) if (dir_path / "results").exists() else 0,
            'logs': len(list((dir_path / "logs").glob('*'))) if (dir_path / "logs").exists() else 0,
            'tmp': len(list((dir_path / "tmp").glob('*'))) if (dir_path / "tmp").exists() else 0,
        }
        
        return {
            'name': dir_path.name,
            'path': str(dir_path),
            'timestamp': dir_path.name,
            'created_at': launch_info.get('started_at', 'Unknown'),
            'size_bytes': total_size,
            'size_human': self._format_size(total_size),
            'file_counts': file_counts,
            'total_files': sum(file_counts.values())
        }
    
    def _format_size(self, size_bytes: int) -> str:
        """Format size in human readable format"""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size_bytes < 1024.0:
                return f"{size_bytes:.1f}{unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.1f}TB"
    
    def cleanup_old_directories(self, days: int = 7, dry_run: bool = False) -> List[str]:
        """Remove directories older than specified days"""
        cutoff_date = datetime.now() - timedelta(days=days)
        removed_dirs = []
        
        directories = self.list_directories()
        
        for dir_info in directories:
            try:
                # Parse timestamp from directory name (YYYYMMDD_HHMMSS)
                timestamp_str = dir_info['timestamp']
                dir_date = datetime.strptime(timestamp_str, "%Y%m%d_%H%M%S")
                
                if dir_date < cutoff_date:
                    dir_path = Path(dir_info['path'])
                    if dry_run:
                        print(f"Would remove: {dir_path} (created: {dir_date})")
                        removed_dirs.append(str(dir_path))
                    else:
                        print(f"Removing: {dir_path} (created: {dir_date})")
                        shutil.rmtree(dir_path)
                        removed_dirs.append(str(dir_path))
                        
            except (ValueError, OSError) as e:
                print(f"Error processing {dir_info['name']}: {e}")
                
        return removed_dirs
    
    def archive_directory(self, timestamp: str, remove_original: bool = False) -> Optional[str]:
        """Archive a specific timestamped directory"""
        source_dir = self.base_data_dir / timestamp
        
        if not source_dir.exists():
            print(f"Directory not found: {source_dir}")
            return None
            
        # Create archives directory
        self.archive_dir.mkdir(exist_ok=True)
        
        # Create archive filename
        archive_name = f"ocr-backend-{timestamp}.tar.gz"
        archive_path = self.archive_dir / archive_name
        
        try:
            print(f"Creating archive: {archive_path}")
            with tarfile.open(archive_path, "w:gz") as tar:
                tar.add(source_dir, arcname=timestamp)
                
            print(f"Archive created successfully: {archive_path}")
            
            if remove_original:
                print(f"Removing original directory: {source_dir}")
                shutil.rmtree(source_dir)
                
            return str(archive_path)
            
        except (OSError, tarfile.TarError) as e:
            print(f"Error creating archive: {e}")
            return None
    
    def get_disk_usage(self) -> Dict:
        """Get disk usage summary for all data directories"""
        if not self.base_data_dir.exists():
            return {'total_size': 0, 'total_dirs': 0, 'directories': []}
            
        directories = self.list_directories()
        total_size = sum(d['size_bytes'] for d in directories)
        
        return {
            'total_size': total_size,
            'total_size_human': self._format_size(total_size),
            'total_dirs': len(directories),
            'directories': directories
        }

def main():
    parser = argparse.ArgumentParser(description='Manage OCR Backend timestamped data directories')
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # List command
    list_parser = subparsers.add_parser('list', help='List all timestamped directories')
    list_parser.add_argument('--verbose', '-v', action='store_true', help='Show detailed information')
    
    # Cleanup command
    cleanup_parser = subparsers.add_parser('cleanup', help='Remove old directories')
    cleanup_parser.add_argument('--days', '-d', type=int, default=7, help='Remove directories older than N days (default: 7)')
    cleanup_parser.add_argument('--dry-run', action='store_true', help='Show what would be removed without actually removing')
    
    # Archive command
    archive_parser = subparsers.add_parser('archive', help='Archive a specific directory')
    archive_parser.add_argument('timestamp', help='Timestamp of directory to archive (e.g., 20241201_143022)')
    archive_parser.add_argument('--remove', action='store_true', help='Remove original directory after archiving')
    
    # Usage command
    usage_parser = subparsers.add_parser('usage', help='Show disk usage summary')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
        
    manager = DataDirectoryManager()
    
    if args.command == 'list':
        directories = manager.list_directories()
        
        if not directories:
            print("No timestamped directories found.")
            return
            
        print(f"\n📁 Found {len(directories)} timestamped directories:\n")
        
        for dir_info in directories:
            print(f"🕒 {dir_info['timestamp']}")
            if args.verbose:
                print(f"   📂 Path: {dir_info['path']}")
                print(f"   📅 Created: {dir_info['created_at']}")
                print(f"   💾 Size: {dir_info['size_human']}")
                print(f"   📄 Files: {dir_info['total_files']} total")
                print(f"      ├─ Uploads: {dir_info['file_counts']['uploads']}")
                print(f"      ├─ Results: {dir_info['file_counts']['results']}")
                print(f"      ├─ Logs: {dir_info['file_counts']['logs']}")
                print(f"      └─ Temp: {dir_info['file_counts']['tmp']}")
                print()
            else:
                print(f"   💾 {dir_info['size_human']} | 📄 {dir_info['total_files']} files")
                
    elif args.command == 'cleanup':
        print(f"🧹 Cleaning up directories older than {args.days} days...")
        if args.dry_run:
            print("🔍 DRY RUN - No files will actually be removed\n")
            
        removed = manager.cleanup_old_directories(args.days, args.dry_run)
        
        if removed:
            action = "Would remove" if args.dry_run else "Removed"
            print(f"\n✅ {action} {len(removed)} directories")
        else:
            print(f"\n✅ No directories older than {args.days} days found")
            
    elif args.command == 'archive':
        archive_path = manager.archive_directory(args.timestamp, args.remove)
        if archive_path:
            print(f"✅ Successfully archived to: {archive_path}")
        else:
            print("❌ Failed to create archive")
            
    elif args.command == 'usage':
        usage_info = manager.get_disk_usage()
        
        print(f"\n💾 Disk Usage Summary:")
        print(f"   Total Size: {usage_info['total_size_human']}")
        print(f"   Total Directories: {usage_info['total_dirs']}")
        
        if usage_info['directories']:
            print(f"\n📊 Top 5 largest directories:")
            sorted_dirs = sorted(usage_info['directories'], key=lambda x: x['size_bytes'], reverse=True)
            for i, dir_info in enumerate(sorted_dirs[:5], 1):
                print(f"   {i}. {dir_info['timestamp']} - {dir_info['size_human']}")

if __name__ == "__main__":
    main() 