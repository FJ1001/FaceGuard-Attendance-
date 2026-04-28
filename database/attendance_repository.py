"""
Attendance data repository
Extracted from db.py attendance-related functions
"""
import logging
import pandas as pd
from typing import List, Dict, Optional, Tuple
from datetime import date, datetime, timedelta
from database.connection import get_db_connection

logger = logging.getLogger(__name__)

class AttendanceRepository:
    """Handle all attendance-related database operations"""
    
    def mark_attendance(self, student_id: int, status: str = 'present', 
                       marked_by: str = 'system') -> Tuple[bool, str]:
        """Mark attendance for a student"""
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                today = date.today().isoformat()
                now = datetime.now().isoformat(timespec="seconds")
                
                # Get student name
                cursor.execute("SELECT name FROM students WHERE id = ?", (student_id,))
                student = cursor.fetchone()
                if not student:
                    return False, "Student not found"
                
                student_name = student['name']
                
                # Check if attendance already marked today
                cursor.execute('''
                    SELECT id, time_in, time_out FROM attendance 
                    WHERE student_id = ? AND date = ?
                ''', (student_id, today))
                
                existing = cursor.fetchone()
                
                if existing:
                    # Update time_out if already has time_in
                    if existing['time_in'] and not existing['time_out']:
                        cursor.execute('''
                            UPDATE attendance 
                            SET time_out = ?, marked_by = ?
                            WHERE id = ?
                        ''', (now, marked_by, existing['id']))
                        conn.commit()
                        return True, f"Time-out marked for {student_name}"
                    else:
                        return False, f"Attendance already marked for {student_name} today"
                else:
                    # Mark new attendance
                    cursor.execute('''
                        INSERT INTO attendance (student_id, date, time_in, status, marked_by)
                        VALUES (?, ?, ?, ?, ?)
                    ''', (student_id, today, now, status, marked_by))
                    conn.commit()
                    
                    logger.info(f"Attendance marked for student {student_name}")
                    return True, f"Attendance marked for {student_name}"
                
        except Exception as e:
            logger.error(f"Error marking attendance: {e}")
            return False, f"Error marking attendance: {str(e)}"
    
    def get_attendance_records(self, start_date: date = None, end_date: date = None, 
                             student_id: int = None) -> List[Dict]:
        """Get attendance records with filters"""
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                
                # Build query with filters
                query = '''
                    SELECT a.*, s.name, s.roll_number 
                    FROM attendance a
                    JOIN students s ON a.student_id = s.id
                    WHERE 1=1
                '''
                params = []
                
                if start_date:
                    query += " AND a.date >= ?"
                    params.append(start_date)
                
                if end_date:
                    query += " AND a.date <= ?"
                    params.append(end_date)
                
                if student_id:
                    query += " AND a.student_id = ?"
                    params.append(student_id)
                
                query += " ORDER BY a.date DESC, a.time_in DESC"
                
                cursor.execute(query, params)
                
                records = []
                for row in cursor.fetchall():
                    records.append({
                        'id': row['id'],
                        'student_id': row['student_id'],
                        'student_name': row['name'],
                        'roll_number': row['roll_number'],
                        'date': row['date'],
                        'time_in': row['time_in'],
                        'time_out': row['time_out'],
                        'status': row['status'],
                        'marked_by': row['marked_by'],
                        'created_at': row['created_at']
                    })
                
                return records
                
        except Exception as e:
            logger.error(f"Error getting attendance records: {e}")
            return []
    
    def get_today_stats(self) -> Dict:
        """Get today's attendance statistics"""
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                today = date.today().isoformat()
                
                # Total students
                cursor.execute("SELECT COUNT(*) FROM students WHERE is_active = 1")
                total_students = cursor.fetchone()[0]
                
                # Present today
                cursor.execute('''
                    SELECT COUNT(*) FROM attendance 
                    WHERE date = ? AND status = 'present'
                ''', (today,))
                present_today = cursor.fetchone()[0]
                
                # Absent today
                absent_today = total_students - present_today
                
                # Attendance percentage
                attendance_rate = (present_today / total_students * 100) if total_students > 0 else 0
                
                return {
                    'total_students': total_students,
                    'present_today': present_today,
                    'absent_today': absent_today,
                    'attendance_rate': round(attendance_rate, 1)
                }
                
        except Exception as e:
            logger.error(f"Error getting today's stats: {e}")
            return {
                'total_students': 0,
                'present_today': 0,
                'absent_today': 0,
                'attendance_rate': 0
            }
    
    def get_attendance_analytics(self, days: int = 30) -> Dict:
        """Get attendance analytics for specified days"""
        try:
            with get_db_connection() as conn:
                start_date = date.today() - timedelta(days=days)
                end_date = date.today()
                
                # Daily attendance
                daily_query = '''
                    SELECT date, COUNT(*) as present_count
                    FROM attendance 
                    WHERE date >= ? AND date <= ? AND status = 'present'
                    GROUP BY date
                    ORDER BY date
                '''
                
                daily_df = pd.read_sql_query(daily_query, conn, params=(start_date, end_date))
                
                # Student-wise attendance
                student_query = '''
                    SELECT s.name, s.roll_number, COUNT(a.id) as days_present
                    FROM students s
                    LEFT JOIN attendance a ON s.id = a.student_id 
                        AND a.date >= ? AND a.date <= ? AND a.status = 'present'
                    WHERE s.is_active = 1
                    GROUP BY s.id, s.name, s.roll_number
                    ORDER BY days_present DESC
                '''
                
                student_df = pd.read_sql_query(student_query, conn, params=(start_date, end_date))
                
                # Weekly trends
                weekly_query = '''
                    SELECT 
                        strftime('%W', date) as week,
                        COUNT(*) as attendance_count
                    FROM attendance 
                    WHERE date >= ? AND date <= ? AND status = 'present'
                    GROUP BY strftime('%W', date)
                    ORDER BY week
                '''
                
                weekly_df = pd.read_sql_query(weekly_query, conn, params=(start_date, end_date))
                
                return {
                    'daily_attendance': daily_df.to_dict('records'),
                    'student_attendance': student_df.to_dict('records'),
                    'weekly_trends': weekly_df.to_dict('records')
                }
                
        except Exception as e:
            logger.error(f"Error getting attendance analytics: {e}")
            return {
                'daily_attendance': [],
                'student_attendance': [],
                'weekly_trends': []
            }
