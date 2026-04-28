"""
Database connection management
Extracted from db.py get_db_connection and init functions
"""
import sqlite3
import logging
from contextlib import contextmanager
from pathlib import Path
from config.settings import DB_FILE, DB_TIMEOUT, ENABLE_FOREIGN_KEYS

logger = logging.getLogger(__name__)

@contextmanager
def get_db_connection():
    """SQLite connection context manager with proper error handling"""
    connection = None
    try:
        # Ensure database directory exists
        DB_FILE.parent.mkdir(parents=True, exist_ok=True)
        
        connection = sqlite3.connect(str(DB_FILE), timeout=DB_TIMEOUT)
        connection.row_factory = sqlite3.Row  # Enable dict-like access
        
        if ENABLE_FOREIGN_KEYS:
            connection.execute("PRAGMA foreign_keys = ON")
        
        yield connection
        
    except Exception as e:
        logger.error(f"Database connection error: {e}")
        if connection:
            connection.rollback()
        raise
    finally:
        if connection:
            connection.close()


def _table_columns(cursor, table: str):
    cursor.execute(f"PRAGMA table_info({table})")
    return [row[1] for row in cursor.fetchall()]


def _add_user_column_if_missing(cursor, col: str, ddl_suffix: str):
    cols = _table_columns(cursor, "users")
    if col not in cols:
        cursor.execute(f"ALTER TABLE users ADD COLUMN {col} {ddl_suffix}")


def _ensure_auxiliary_schema(cursor, conn) -> None:
    """Audit log, rate limits, optional TOTP columns on users."""
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS audit_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            actor_email TEXT,
            action TEXT NOT NULL,
            target_type TEXT,
            target_id TEXT,
            detail TEXT,
            client_hint TEXT
        )
        """
    )
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_audit_created ON audit_log(created_at DESC)"
    )
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS password_reset_rate (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_pwd_reset_email_time ON password_reset_rate(email, created_at)"
    )
    try:
        _add_user_column_if_missing(cursor, "totp_secret", "TEXT")
        _add_user_column_if_missing(cursor, "totp_enabled", "INTEGER DEFAULT 0")
    except Exception as e:
        logger.warning("User table TOTP columns: %s", e)


def init_database():
    """Initialize database with all required tables and admin user"""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # Create users table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE NOT NULL,
                    email TEXT UNIQUE NOT NULL,
                    password_hash TEXT NOT NULL,
                    role TEXT DEFAULT 'user',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    reset_token TEXT,
                    reset_token_expires TIMESTAMP,
                    last_login TIMESTAMP
                )
            ''')
            
            # Create students table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS students (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    roll_number TEXT UNIQUE NOT NULL,
                    email TEXT UNIQUE,
                    phone TEXT,
                    course TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    is_active BOOLEAN DEFAULT 1
                )
            ''')

            cols = _table_columns(cursor, "students")
            if "deleted_at" not in cols:
                cursor.execute("ALTER TABLE students ADD COLUMN deleted_at TIMESTAMP")
            
            # Create face_embeddings table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS face_embeddings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    student_id INTEGER NOT NULL,
                    embedding_data TEXT NOT NULL,
                    photo_id TEXT UNIQUE NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (student_id) REFERENCES students (id) ON DELETE CASCADE
                )
            ''')
            
            # Create attendance table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS attendance (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    student_id INTEGER NOT NULL,
                    date DATE NOT NULL,
                    time_in TIMESTAMP,
                    time_out TIMESTAMP,
                    status TEXT DEFAULT 'present',
                    marked_by TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (student_id) REFERENCES students (id) ON DELETE CASCADE,
                    UNIQUE(student_id, date)
                )
            ''')
            
            # Create indexes for better performance
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_students_roll ON students(roll_number)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_attendance_date ON attendance(date)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_attendance_student ON attendance(student_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_users_email ON users(email)')

            _ensure_auxiliary_schema(cursor, conn)

            conn.commit()
            
            # Create default admin user
            _create_default_admin(cursor, conn)
            # One-time align legacy seed (old builds used admin@attendance.com) to .env ADMIN_*
            _migrate_legacy_admin_email_to_env(cursor, conn)

            logger.info("Database initialized successfully")
            
    except Exception as e:
        logger.error(f"Database initialization error: {e}")
        raise

def _create_default_admin(cursor, conn):
    """Create default admin if none exists — must match config.settings ADMIN_* (same as migration)."""
    try:
        cursor.execute("SELECT COUNT(*) FROM users WHERE role = 'admin'")
        admin_count = cursor.fetchone()[0]
        if admin_count > 0:
            return

        from config.settings import ADMIN_EMAIL, ADMIN_PASSWORD
        from auth.password_hashing import hash_password

        password_hash = hash_password(ADMIN_PASSWORD)
        cursor.execute(
            """
            INSERT INTO users (username, email, password_hash, role)
            VALUES (?, ?, ?, ?)
            """,
            ("admin", ADMIN_EMAIL, password_hash, "admin"),
        )
        conn.commit()
        logger.info("Default admin created for email %s (password from ADMIN_PASSWORD / .env)", ADMIN_EMAIL)
    except Exception as e:
        logger.error(f"Error creating default admin: {e}")


# Email used by older versions of _create_default_admin before settings-based seed
_LEGACY_ADMIN_EMAIL = "admin@attendance.com"


def _migrate_legacy_admin_email_to_env(cursor, conn) -> None:
    """If the only admin still has the legacy email, update to ADMIN_EMAIL / ADMIN_PASSWORD from env."""
    try:
        from config.settings import ADMIN_EMAIL, ADMIN_PASSWORD
        from auth.password_hashing import hash_password

        cursor.execute(
            "SELECT id, email FROM users WHERE role = 'admin' ORDER BY id"
        )
        rows = cursor.fetchall()
        if len(rows) != 1:
            return
        uid = rows[0]["id"]
        email = rows[0]["email"]
        if email != _LEGACY_ADMIN_EMAIL:
            return
        new_hash = hash_password(ADMIN_PASSWORD)
        cursor.execute(
            "UPDATE users SET email = ?, password_hash = ? WHERE id = ?",
            (ADMIN_EMAIL, new_hash, uid),
        )
        conn.commit()
        logger.info(
            "Updated legacy admin from %s to %s (password from ADMIN_PASSWORD)",
            _LEGACY_ADMIN_EMAIL,
            ADMIN_EMAIL,
        )
    except Exception as e:
        logger.warning("Legacy admin migration skipped: %s", e)
