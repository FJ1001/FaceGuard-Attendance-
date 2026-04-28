"""
Student data repository
Extracted from db.py student-related functions
"""
import logging
import base64
import numpy as np
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
from database.connection import get_db_connection
from config.settings import (
    BIOMETRIC_HARD_DELETE_ON_STUDENT_DELETE,
    BIOMETRIC_RETENTION_DAYS,
    EMBEDDING_SIZE,
)

logger = logging.getLogger(__name__)

class StudentRepository:
    """Handle all student-related database operations"""
    
    def add_student_with_photos(self, name: str, roll_number: str, email: str, 
                              phone: str, course: str, embeddings_data: List[Tuple]) -> Tuple[bool, str]:
        """Add student with face embeddings"""
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                
                # Check if student already exists
                cursor.execute("SELECT id FROM students WHERE roll_number = ? OR email = ?", 
                             (roll_number, email))
                if cursor.fetchone():
                    return False, "Student with this roll number or email already exists"
                
                # Insert student
                cursor.execute('''
                    INSERT INTO students (name, roll_number, email, phone, course)
                    VALUES (?, ?, ?, ?, ?)
                ''', (name, roll_number, email, phone, course))
                
                student_id = cursor.lastrowid
                
                # Insert embeddings
                for photo_id, embedding in embeddings_data:
                    if isinstance(embedding, np.ndarray):
                        embedding_b64 = base64.b64encode(embedding.tobytes()).decode('utf-8')
                    else:
                        embedding_b64 = embedding
                    
                    cursor.execute('''
                        INSERT INTO face_embeddings (student_id, embedding_data, photo_id)
                        VALUES (?, ?, ?)
                    ''', (student_id, embedding_b64, photo_id))
                
                conn.commit()
                logger.info(f"Student {name} added with {len(embeddings_data)} face embeddings")
                return True, f"Student {name} added successfully"
                
        except Exception as e:
            logger.error(f"Error adding student: {e}")
            return False, f"Error adding student: {str(e)}"
    
    def get_all_students(self) -> List[Dict]:
        """Get all active students"""
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT s.*, COUNT(fe.id) as photo_count
                    FROM students s
                    LEFT JOIN face_embeddings fe ON s.id = fe.student_id
                    WHERE s.is_active = 1
                    GROUP BY s.id
                    ORDER BY s.name
                ''')
                
                students = []
                for row in cursor.fetchall():
                    students.append({
                        'id': row['id'],
                        'name': row['name'],
                        'roll_number': row['roll_number'],
                        'email': row['email'],
                        'phone': row['phone'],
                        'course': row['course'],
                        'photo_count': row['photo_count'],
                        'created_at': row['created_at']
                    })
                
                return students
                
        except Exception as e:
            logger.error(f"Error getting students: {e}")
            return []
    
    def delete_student(self, student_id: int) -> Tuple[bool, str]:
        """Soft delete student (mark as inactive)"""
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                
                # Check if student exists
                cursor.execute("SELECT name FROM students WHERE id = ?", (student_id,))
                student = cursor.fetchone()
                if not student:
                    return False, "Student not found"
                
                if BIOMETRIC_HARD_DELETE_ON_STUDENT_DELETE:
                    cursor.execute("DELETE FROM face_embeddings WHERE student_id = ?", (student_id,))

                cursor.execute(
                    "UPDATE students SET is_active = 0, deleted_at = CURRENT_TIMESTAMP WHERE id = ?",
                    (student_id,),
                )
                conn.commit()
                
                logger.info(f"Student {student['name']} deleted")
                return True, f"Student {student['name']} deleted successfully"
                
        except Exception as e:
            logger.error(f"Error deleting student: {e}")
            return False, f"Error deleting student: {str(e)}"

    def delete_student_by_roll(self, roll_number: str) -> Tuple[bool, str]:
        """Soft delete an active student by roll number."""
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()

                cursor.execute(
                    "SELECT id, name FROM students WHERE roll_number = ? AND is_active = 1",
                    (roll_number,),
                )
                student = cursor.fetchone()
                if not student:
                    return False, "Active student not found"

                if BIOMETRIC_HARD_DELETE_ON_STUDENT_DELETE:
                    cursor.execute("DELETE FROM face_embeddings WHERE student_id = ?", (student["id"],))

                cursor.execute(
                    "UPDATE students SET is_active = 0, deleted_at = CURRENT_TIMESTAMP WHERE id = ?",
                    (student["id"],),
                )
                conn.commit()

                logger.info("Student %s deleted by roll number %s", student["name"], roll_number)
                return True, f"Student {student['name']} deleted successfully"

        except Exception as e:
            logger.error(f"Error deleting student by roll: {e}")
            return False, f"Error deleting student: {str(e)}"

    def purge_inactive_biometrics(self, retention_days: int = BIOMETRIC_RETENTION_DAYS) -> Tuple[int, str]:
        """Delete biometric embeddings for inactive students past retention window."""
        try:
            cutoff = (datetime.now() - timedelta(days=max(retention_days, 0))).isoformat(
                sep=" ",
                timespec="seconds",
            )
            with get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    SELECT id FROM students
                    WHERE is_active = 0
                      AND deleted_at IS NOT NULL
                      AND deleted_at <= ?
                    """,
                    (cutoff,),
                )
                student_ids = [row["id"] for row in cursor.fetchall()]
                if not student_ids:
                    return 0, "No inactive biometric records eligible for purge"

                placeholders = ",".join("?" for _ in student_ids)
                cursor.execute(
                    f"DELETE FROM face_embeddings WHERE student_id IN ({placeholders})",
                    student_ids,
                )
                deleted_count = cursor.rowcount
                conn.commit()

                logger.info("Purged %s biometric embeddings for inactive students", deleted_count)
                return deleted_count, f"Purged {deleted_count} biometric embeddings"

        except Exception as e:
            logger.error(f"Error purging inactive biometrics: {e}")
            return 0, f"Error purging biometrics: {str(e)}"
    
    def get_student_embeddings(self) -> List[Tuple]:
        """Get all student embeddings for recognition"""
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT s.id, s.name, s.roll_number, fe.embedding_data
                    FROM students s
                    JOIN face_embeddings fe ON s.id = fe.student_id
                    WHERE s.is_active = 1
                ''')
                
                embeddings = []
                for row in cursor.fetchall():
                    try:
                        # Decode embedding
                        embedding_bytes = base64.b64decode(row['embedding_data'])
                        embedding = np.frombuffer(embedding_bytes, dtype=np.float32)
                        
                        # Ensure correct size
                        if len(embedding) != EMBEDDING_SIZE:
                            if len(embedding) > EMBEDDING_SIZE:
                                embedding = embedding[:EMBEDDING_SIZE]
                            else:
                                # Pad with zeros
                                padded = np.zeros(EMBEDDING_SIZE, dtype=np.float32)
                                padded[:len(embedding)] = embedding
                                embedding = padded
                        
                        embeddings.append((
                            row['id'], row['name'], row['roll_number'], embedding
                        ))
                        
                    except Exception as e:
                        logger.warning(f"Error decoding embedding for student {row['name']}: {e}")
                        continue
                
                return embeddings
                
        except Exception as e:
            logger.error(f"Error getting student embeddings: {e}")
            return []
    
    def delete_all_students(self) -> Tuple[bool, str]:
        """Delete all students and their data"""
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                
                # Get count first
                cursor.execute("SELECT COUNT(*) FROM students WHERE is_active = 1")
                count = cursor.fetchone()[0]
                
                if count == 0:
                    return False, "No students to delete"
                
                # Delete all related data
                cursor.execute("DELETE FROM face_embeddings")
                cursor.execute("DELETE FROM attendance")
                cursor.execute("DELETE FROM students")
                
                conn.commit()
                
                logger.info(f"Deleted {count} students and all related data")
                return True, f"Successfully deleted {count} students and all related data"
                
        except Exception as e:
            logger.error(f"Error deleting all students: {e}")
            return False, f"Error deleting students: {str(e)}"
