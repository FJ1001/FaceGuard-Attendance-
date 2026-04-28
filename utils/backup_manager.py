"""
Database backup and recovery utilities
"""
import sqlite3
import shutil
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any
import logging

logger = logging.getLogger(__name__)

class BackupManager:
    """Handle database backup and recovery operations"""
    
    def __init__(self, db_path: str, backup_dir: str = "data/backups"):
        self.db_path = Path(db_path)
        self.backup_dir = Path(backup_dir)
        self.backup_dir.mkdir(parents=True, exist_ok=True)
    
    def create_backup(self, backup_name: str = None) -> str:
        """Create database backup"""
        if not backup_name:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            backup_name = f"attendance_backup_{timestamp}.db"
        
        backup_path = self.backup_dir / backup_name
        
        try:
            shutil.copy2(self.db_path, backup_path)
            logger.info(f"Backup created: {backup_path}")
            return str(backup_path)
        except Exception as e:
            logger.error(f"Backup failed: {e}")
            raise
    
    def restore_backup(self, backup_path: str) -> bool:
        """Restore database from backup"""
        try:
            backup_file = Path(backup_path)
            if not backup_file.exists():
                logger.error(f"Backup file not found: {backup_path}")
                return False
            
            # Create current backup before restore
            self.create_backup(f"pre_restore_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db")
            
            # Restore backup
            shutil.copy2(backup_file, self.db_path)
            logger.info(f"Database restored from: {backup_path}")
            return True
            
        except Exception as e:
            logger.error(f"Restore failed: {e}")
            return False

    def list_recent_backups(self, limit: int = 8) -> List[Dict[str, Any]]:
        """Return newest backup files with size and mtime."""
        try:
            if not self.backup_dir.exists():
                return []
            files = sorted(
                self.backup_dir.glob("*.db"),
                key=lambda p: p.stat().st_mtime,
                reverse=True,
            )[:limit]
            out = []
            for p in files:
                st = p.stat()
                out.append(
                    {
                        "name": p.name,
                        "path": str(p),
                        "size_mb": round(st.st_size / (1024**2), 2),
                        "modified": datetime.fromtimestamp(st.st_mtime).isoformat(timespec="seconds"),
                    }
                )
            return out
        except Exception as e:
            logger.error("list_recent_backups: %s", e)
            return []

    def export_data_json(self) -> Dict[str, Any]:
        """Export all data as JSON for migration"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                
                data = {}
                
                # Export users
                cursor = conn.execute("SELECT * FROM users")
                data['users'] = [dict(row) for row in cursor.fetchall()]
                
                # Export students
                cursor = conn.execute("SELECT * FROM students")
                data['students'] = [dict(row) for row in cursor.fetchall()]
                
                # Export face_embeddings
                cursor = conn.execute("SELECT * FROM face_embeddings")
                data['face_embeddings'] = [dict(row) for row in cursor.fetchall()]
                
                # Export attendance
                cursor = conn.execute("SELECT * FROM attendance")
                data['attendance'] = [dict(row) for row in cursor.fetchall()]
                
                return data
                
        except Exception as e:
            logger.error(f"Data export failed: {e}")
            return {}
    
    def import_data_json(self, data: Dict[str, Any]) -> bool:
        """Import data from JSON"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Import users
                if 'users' in data:
                    for user in data['users']:
                        cursor.execute('''
                            INSERT OR REPLACE INTO users 
                            (id, username, email, password_hash, role, created_at, last_login)
                            VALUES (?, ?, ?, ?, ?, ?, ?)
                        ''', (user['id'], user['username'], user['email'], 
                              user['password_hash'], user['role'], 
                              user['created_at'], user.get('last_login')))
                
                # Import students
                if 'students' in data:
                    for student in data['students']:
                        cursor.execute('''
                            INSERT OR REPLACE INTO students 
                            (id, name, roll_number, email, phone, course, created_at, is_active)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                        ''', (student['id'], student['name'], student['roll_number'],
                              student['email'], student['phone'], student['course'],
                              student['created_at'], student.get('is_active', 1)))
                
                # Import face_embeddings
                if 'face_embeddings' in data:
                    for embedding in data['face_embeddings']:
                        cursor.execute('''
                            INSERT OR REPLACE INTO face_embeddings
                            (id, student_id, embedding_data, photo_id, created_at)
                            VALUES (?, ?, ?, ?, ?)
                        ''', (embedding['id'], embedding['student_id'],
                              embedding['embedding_data'], embedding['photo_id'],
                              embedding['created_at']))
                
                # Import attendance
                if 'attendance' in data:
                    for record in data['attendance']:
                        cursor.execute('''
                            INSERT OR REPLACE INTO attendance
                            (id, student_id, date, time_in, time_out, status, marked_by, created_at)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                        ''', (record['id'], record['student_id'], record['date'],
                              record['time_in'], record['time_out'], record['status'],
                              record['marked_by'], record['created_at']))
                
                conn.commit()
                logger.info("Data import completed successfully")
                return True
                
        except Exception as e:
            logger.error(f"Data import failed: {e}")
            return False

# Convenience functions
def backup_database(db_path: str = "data/attendance.db") -> str:
    """Quick backup function"""
    manager = BackupManager(db_path)
    return manager.create_backup()

def restore_database(backup_path: str, db_path: str = "data/attendance.db") -> bool:
    """Quick restore function"""
    manager = BackupManager(db_path)
    return manager.restore_backup(backup_path)
