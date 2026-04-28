"""
Database migration utilities
Handle schema changes and data preservation
"""
import sqlite3
import logging
from pathlib import Path
from typing import List, Dict, Any
from database.connection import get_db_connection
from utils.backup_manager import BackupManager


logger = logging.getLogger(__name__)


class DatabaseMigration:
    """Handle database migrations and schema updates"""
    
    def __init__(self, db_path: str = "data/attendance.db"):
        self.db_path = Path(db_path)
        self.backup_manager = BackupManager(str(db_path))
    
    def migrate_from_old_system(self, old_db_path: str) -> bool:
        """Migrate data from old database system"""
        try:
            old_db = Path(old_db_path)
            if not old_db.exists():
                logger.warning(f"Old database not found: {old_db_path}")
                return False
            
            # Create backup of current database
            self.backup_manager.create_backup("pre_migration_backup.db")
            
            # Export data from old database
            old_data = self._export_old_data(old_db_path)
            
            # Import into new database
            success = self._import_migrated_data(old_data)
            
            if success:
                logger.info("Migration completed successfully")
                return True
            else:
                logger.error("Migration failed")
                return False
                
        except Exception as e:
            logger.error(f"Migration error: {e}")
            return False
    
    def _export_old_data(self, old_db_path: str) -> Dict[str, Any]:
        """Export data from old database format"""
        try:
            with sqlite3.connect(old_db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                data = {}
                
                # Check which tables exist in old database
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
                tables = [row[0] for row in cursor.fetchall()]
                
                for table in tables:
                    try:
                        cursor.execute(f"SELECT * FROM {table}")
                        data[table] = [dict(row) for row in cursor.fetchall()]
                        logger.info(f"Exported {len(data[table])} records from {table}")
                    except Exception as e:
                        logger.warning(f"Could not export table {table}: {e}")
                
                return data
                
        except Exception as e:
            logger.error(f"Old data export failed: {e}")
            return {}
    
    def _import_migrated_data(self, old_data: Dict[str, Any]) -> bool:
        """Import migrated data into new database structure"""
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                
                # Map old table structure to new structure
                table_mappings = {
                    'users': self._migrate_users,
                    'students': self._migrate_students,
                    'face_embeddings': self._migrate_face_embeddings,
                    'attendance': self._migrate_attendance
                }
                
                for old_table, migration_func in table_mappings.items():
                    if old_table in old_data:
                        success = migration_func(cursor, old_data[old_table])
                        if not success:
                            logger.warning(f"Migration of {old_table} had issues")
                
                conn.commit()
                return True
                
        except Exception as e:
            logger.error(f"Data import failed: {e}")
            return False
    
    def _migrate_users(self, cursor, users_data: List[Dict]) -> bool:
        """Migrate users table"""
        try:
            for user in users_data:
                cursor.execute('''
                    INSERT OR REPLACE INTO users 
                    (username, email, password_hash, role, created_at)
                    VALUES (?, ?, ?, ?, ?)
                ''', (
                    user.get('username', user.get('email', 'unknown')),
                    user.get('email'),
                    user.get('password_hash', user.get('password')),
                    user.get('role', 'user'),
                    user.get('created_at', user.get('created_date'))
                ))
            logger.info(f"Migrated {len(users_data)} users")
            return True
        except Exception as e:
            logger.error(f"User migration failed: {e}")
            return False
    
    def _migrate_students(self, cursor, students_data: List[Dict]) -> bool:
        """Migrate students table"""
        try:
            for student in students_data:
                cursor.execute('''
                    INSERT OR REPLACE INTO students 
                    (name, roll_number, email, phone, course, created_at, is_active)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (
                    student.get('name'),
                    student.get('roll_number'),
                    student.get('email'),
                    student.get('phone'),
                    student.get('course'),
                    student.get('created_at'),
                    student.get('is_active', 1)
                ))
            logger.info(f"Migrated {len(students_data)} students")
            return True
        except Exception as e:
            logger.error(f"Student migration failed: {e}")
            return False
    
    def _migrate_face_embeddings(self, cursor, embeddings_data: List[Dict]) -> bool:
        """Migrate face embeddings table"""
        try:
            for embedding in embeddings_data:
                cursor.execute('''
                    INSERT OR REPLACE INTO face_embeddings
                    (student_id, embedding_data, photo_id, created_at)
                    VALUES (?, ?, ?, ?)
                ''', (
                    embedding.get('student_id'),
                    embedding.get('embedding_data'),
                    embedding.get('photo_id'),
                    embedding.get('created_at')
                ))
            logger.info(f"Migrated {len(embeddings_data)} face embeddings")
            return True
        except Exception as e:
            logger.error(f"Face embeddings migration failed: {e}")
            return False
    
    def _migrate_attendance(self, cursor, attendance_data: List[Dict]) -> bool:
        """Migrate attendance table"""
        try:
            for record in attendance_data:
                cursor.execute('''
                    INSERT OR REPLACE INTO attendance
                    (student_id, date, time_in, time_out, status, marked_by, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (
                    record.get('student_id'),
                    record.get('date'),
                    record.get('time_in'),
                    record.get('time_out'),
                    record.get('status', 'present'),
                    record.get('marked_by', 'system'),
                    record.get('created_at')
                ))
            logger.info(f"Migrated {len(attendance_data)} attendance records")
            return True
        except Exception as e:
            logger.error(f"Attendance migration failed: {e}")
            return False


def migrate_from_old_database(old_db_path: str) -> bool:
    """Convenience function for migration"""
    migration = DatabaseMigration()
    return migration.migrate_from_old_system(old_db_path)


# ADMIN CREATION FUNCTIONS WITH DEBUGGING
def create_default_admin():
    """Create default admin user from configuration"""
    try:
        from config.settings import ADMIN_EMAIL, ADMIN_PASSWORD, ADMIN_ROLE
        
        # Debug: Print what values we got
        logger.info(f"📧 Admin Email: {ADMIN_EMAIL}")
        logger.info(f"🔑 Admin Password: {'*' * len(ADMIN_PASSWORD) if ADMIN_PASSWORD else 'None'}")
        logger.info(f"👤 Admin Role: {ADMIN_ROLE}")
        
        # Try importing user repository
        try:
            from database.user_repository import UserRepository
            logger.info("✅ UserRepository imported successfully")
        except ImportError as e:
            logger.error(f"❌ Failed to import UserRepository: {e}")
            return False
        
        # Try importing hash function
        try:
            from auth.authentication import hash_password
            logger.info("✅ hash_password imported successfully")
        except ImportError as e:
            # Try alternative import paths
            try:
                from auth.auth import hash_password
                logger.info("✅ hash_password imported from auth.auth")
            except ImportError:
                try:
                    # helpers module is named helperrs.py in this project
                    from utils.helperrs import hash_string as hash_password
                    logger.info("✅ hash_password imported from utils.helperrs.hash_string")
                except ImportError:
                    logger.error(f"❌ Could not import hash_password function: {e}")
                    return False
        
        user_repo = UserRepository()

        # Any admin row means we're done (avoids duplicate username when legacy DB used another email)
        try:
            with get_db_connection() as conn:
                cur = conn.cursor()
                cur.execute(
                    "SELECT email FROM users WHERE role = 'admin' ORDER BY id LIMIT 1"
                )
                row = cur.fetchone()
            if row:
                legacy_email = row["email"]
                if legacy_email == ADMIN_EMAIL:
                    logger.info("ℹ️ Admin user already exists: %s", ADMIN_EMAIL)
                else:
                    logger.warning(
                        "ℹ️ An admin already exists as %s (not %s). "
                        "Log in with that email and password you set when it was created, "
                        "or update the users table email to match ADMIN_EMAIL.",
                        legacy_email,
                        ADMIN_EMAIL,
                    )
                return True
        except Exception as e:
            logger.error(f"❌ Error checking existing admin: {e}")
            return False

        # No admin yet — create using configured email
        try:
            existing_by_email = user_repo.get_user_by_email(ADMIN_EMAIL)
            if existing_by_email:
                logger.info(f"ℹ️ User already exists: {ADMIN_EMAIL}")
                return True
        except Exception as e:
            logger.error(f"❌ Error checking email: {e}")
            return False
        
        # Create admin user
        try:
            hashed_password = hash_password(ADMIN_PASSWORD)
            logger.info("✅ Password hashed successfully")
        except Exception as e:
            logger.error(f"❌ Error hashing password: {e}")
            return False
        
        # Try to create admin
        try:
            # Try different method signatures that might exist
            admin_created = None
            
            # Method 1: Try with username, email, password_hash, role
            try:
                admin_created = user_repo.create_user(
                    username="admin",
                    email=ADMIN_EMAIL,
                    password_hash=hashed_password,
                    role=ADMIN_ROLE
                )
            except Exception as e1:
                logger.warning(f"Method 1 failed: {e1}")
                
                # Method 2: Try with email, password, role
                try:
                    admin_created = user_repo.create_user(
                        email=ADMIN_EMAIL,
                        password=hashed_password,
                        role=ADMIN_ROLE
                    )
                except Exception as e2:
                    logger.warning(f"Method 2 failed: {e2}")
                    
                    # Method 3: Try with different parameter names
                    try:
                        admin_created = user_repo.create_user(
                            email=ADMIN_EMAIL,
                            password_hash=hashed_password,
                            role=ADMIN_ROLE
                        )
                    except Exception as e3:
                        logger.error(f"All creation methods failed. Last error: {e3}")
                        return False
            
            ok = admin_created[0] if isinstance(admin_created, tuple) else bool(admin_created)
            if ok:
                logger.info(f"✅ Default admin created: {ADMIN_EMAIL}")
                return True
            logger.error("❌ Failed to create admin user: %s", admin_created)
            return False
                
        except Exception as e:
            logger.error(f"❌ Unexpected error during admin creation: {e}")
            return False
            
    except Exception as e:
        logger.error(f"❌ Admin creation error: {e}")
        import traceback
        logger.error(f"Full traceback: {traceback.format_exc()}")
        return False


def initialize_fresh_database():
    """Initialize a fresh database with default admin"""
    try:
        # First, ensure all tables exist (you might already have this)
        from database.connection import create_tables_and_admin
        create_tables_and_admin()
        
        # Then create default admin
        admin_created = create_default_admin()
        
        if admin_created:
            logger.info("✅ Fresh database initialized with admin")
            return True
        else:
            logger.warning("⚠️ Database initialized but admin creation failed")
            return False
            
    except Exception as e:
        logger.error(f"❌ Database initialization failed: {e}")
        return False


def ensure_admin_exists():
    """Ensure admin exists - safe to call multiple times"""
    return create_default_admin()
