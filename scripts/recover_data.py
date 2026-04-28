"""
Data Recovery Script
Run this to recover your old data
"""
import os
from pathlib import Path
from database.migration import migrate_from_old_database
from utils.backup_manager import BackupManager

def main():
    print("🔄 Smart Attendance System - Data Recovery")
    print("=" * 50)
    
    # Look for old database file
    possible_old_db_paths = [
        "attendance.db",
        "data/attendance.db", 
        "../attendance.db",
        "attendance_backup.db"
    ]
    
    old_db_path = None
    for path in possible_old_db_paths:
        if Path(path).exists():
            old_db_path = path
            print(f"✅ Found old database: {path}")
            break
    
    if not old_db_path:
        print("❌ No old database file found.")
        print("Please copy your old attendance.db file to this directory.")
        return
    
    # Show current data status
    current_db = Path("data/attendance.db")
    if current_db.exists():
        print(f"📊 Current database size: {current_db.stat().st_size} bytes")
    
    # Ask for confirmation
    response = input("\n🔄 Do you want to migrate data from old database? (y/N): ")
    
    if response.lower() in ['y', 'yes']:
        print("🚀 Starting migration...")
        
        # Migrate data
        success = migrate_from_old_database(old_db_path)
        
        if success:
            print("✅ Migration completed successfully!")
            print("🎉 Your old data has been restored.")
        else:
            print("❌ Migration failed. Check logs for details.")
            
    else:
        print("❌ Migration cancelled.")

if __name__ == "__main__":
    main()
