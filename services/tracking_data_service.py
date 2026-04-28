"""
Student tracking data service
Retrieves real-time and historical tracking data for students
"""
import logging
import json
from typing import List, Dict, Optional, Tuple
from datetime import date, datetime, timedelta
from database.connection import get_db_connection
from database.student_repository import StudentRepository
import pandas as pd

logger = logging.getLogger(__name__)


class TrackingDataService:
    """Service for retrieving student tracking and attendance data"""
    
    def __init__(self):
        self.db_connection = get_db_connection
        self.student_repo = StudentRepository()
    
    def get_student_current_status(self, student_id: int) -> Dict:
        """Get current real-time status of a student"""
        try:
            with self.db_connection() as conn:
                cursor = conn.cursor()
                
                today = date.today().isoformat()
                
                # Get today's attendance
                cursor.execute('''
                    SELECT id, time_in, time_out, status
                    FROM attendance
                    WHERE student_id = ? AND date = ?
                ''', (student_id, today))
                
                attendance = cursor.fetchone()
                
                # Get student info
                cursor.execute('''
                    SELECT id, name, roll_number, email
                    FROM students
                    WHERE id = ?
                ''', (student_id,))
                
                student = cursor.fetchone()
                
                if not student:
                    return {}
                
                status = "absent"
                if attendance:
                    if attendance['time_in'] and attendance['time_out']:
                        status = "completed"
                    elif attendance['time_in']:
                        status = "present"
                
                return {
                    'student_id': student_id,
                    'name': student['name'],
                    'roll_number': student['roll_number'],
                    'email': student['email'],
                    'status': status,
                    'time_in': attendance['time_in'] if attendance else None,
                    'time_out': attendance['time_out'] if attendance else None,
                    'last_updated': attendance['time_out'] or attendance['time_in'] if attendance else None,
                }
        except Exception as e:
            logger.error(f"Error getting student status: {e}")
            return {}
    
    def get_all_students_status(self) -> List[Dict]:
        """Get real-time status of all active students"""
        try:
            with self.db_connection() as conn:
                cursor = conn.cursor()
                
                today = date.today().isoformat()
                
                # Get all students with today's attendance
                cursor.execute('''
                    SELECT s.id, s.name, s.roll_number, s.email,
                           a.time_in, a.time_out, a.status
                    FROM students s
                    LEFT JOIN attendance a ON s.id = a.student_id AND a.date = ?
                    WHERE s.is_active = 1
                    ORDER BY s.name ASC
                ''', (today,))
                
                students_status = []
                
                for row in cursor.fetchall():
                    status = "absent"
                    if row['time_in']:
                        status = "present" if not row['time_out'] else "completed"
                    
                    students_status.append({
                        'student_id': row['id'],
                        'name': row['name'],
                        'roll_number': row['roll_number'],
                        'status': status,
                        'time_in': row['time_in'],
                        'time_out': row['time_out'],
                    })
                
                return students_status
        except Exception as e:
            logger.error(f"Error getting all students status: {e}")
            return []
    
    def get_student_tracking_history(self, student_id: int, days_back: int = 7) -> List[Dict]:
        """Get historical tracking data for a student"""
        try:
            with self.db_connection() as conn:
                cursor = conn.cursor()
                
                start_date = (date.today() - timedelta(days=days_back)).isoformat()
                end_date = date.today().isoformat()
                
                cursor.execute('''
                    SELECT date, time_in, time_out, status, marked_by
                    FROM attendance
                    WHERE student_id = ? AND date BETWEEN ? AND ?
                    ORDER BY date DESC
                ''', (student_id, start_date, end_date))
                
                records = []
                for row in cursor.fetchall():
                    records.append({
                        'date': row['date'],
                        'time_in': row['time_in'],
                        'time_out': row['time_out'],
                        'status': row['status'],
                        'marked_by': row['marked_by'],
                        'duration': self._calculate_duration(row['time_in'], row['time_out']),
                    })
                
                return records
        except Exception as e:
            logger.error(f"Error getting tracking history: {e}")
            return []
    
    def get_student_focus_metrics(self, student_id: int, days_back: int = 7) -> Dict:
        """Get focus and energy metrics for a student"""
        try:
            # Note: This would require storing focus scores in database
            # For now, returning structure that can be populated
            return {
                'student_id': student_id,
                'avg_focus_score': 0,
                'focus_trend': 'stable',
                'alerts_this_week': 0,
                'most_common_issue': None,
                'improvement_needed': [],
            }
        except Exception as e:
            logger.error(f"Error getting focus metrics: {e}")
            return {}
    
    def get_student_attendance_insights(self, student_id: int) -> Dict:
        """Get attendance patterns and insights for a student"""
        try:
            with self.db_connection() as conn:
                cursor = conn.cursor()
                
                # Last 30 days
                start_date = (date.today() - timedelta(days=30)).isoformat()
                end_date = date.today().isoformat()
                
                # Get attendance records
                cursor.execute('''
                    SELECT date, time_in, time_out, status
                    FROM attendance
                    WHERE student_id = ? AND date BETWEEN ? AND ?
                    ORDER BY date DESC
                ''', (student_id, start_date, end_date))
                
                records = cursor.fetchall()
                total_days = 30
                present_days = len(records)
                
                # Calculate statistics
                late_arrivals = 0
                early_departures = 0
                avg_duration = 0
                durations = []
                
                for record in records:
                    if record['time_in']:
                        # Check if late (after 9:00 AM)
                        time_in = datetime.fromisoformat(record['time_in']).time()
                        if time_in.hour >= 9 and time_in.minute > 0:
                            late_arrivals += 1
                        
                        # Check duration
                        if record['time_out']:
                            time_out = datetime.fromisoformat(record['time_out']).time()
                            time_in_dt = datetime.fromisoformat(record['time_in'])
                            time_out_dt = datetime.fromisoformat(record['time_out'])
                            duration = (time_out_dt - time_in_dt).total_seconds() / 3600
                            durations.append(duration)
                            
                            if time_out.hour < 15:  # Before 3 PM
                                early_departures += 1
                
                avg_duration = sum(durations) / len(durations) if durations else 0
                attendance_rate = (present_days / total_days * 100) if total_days > 0 else 0
                
                return {
                    'student_id': student_id,
                    'days_tracked': total_days,
                    'days_present': present_days,
                    'attendance_rate': round(attendance_rate, 1),
                    'late_arrivals': late_arrivals,
                    'early_departures': early_departures,
                    'avg_duration_hours': round(avg_duration, 1),
                    'trend': self._determine_trend(records),
                    'recommendations': self._generate_recommendations(
                        attendance_rate, late_arrivals, early_departures
                    ),
                }
        except Exception as e:
            logger.error(f"Error getting attendance insights: {e}")
            return {}
    
    def get_class_tracking_overview(self) -> Dict:
        """Get overview of entire class tracking status"""
        try:
            with self.db_connection() as conn:
                cursor = conn.cursor()
                
                today = date.today().isoformat()
                
                # Get class statistics
                cursor.execute("SELECT COUNT(*) FROM students WHERE is_active = 1")
                total_students = cursor.fetchone()[0]
                
                cursor.execute('''
                    SELECT COUNT(DISTINCT student_id) FROM attendance
                    WHERE date = ? AND time_in IS NOT NULL
                ''', (today,))
                present_today = cursor.fetchone()[0]
                
                cursor.execute('''
                    SELECT COUNT(DISTINCT student_id) FROM attendance
                    WHERE date = ? AND time_out IS NOT NULL
                ''', (today,))
                departed = cursor.fetchone()[0]
                
                # Get recent activity
                cursor.execute('''
                    SELECT s.name, MAX(a.time_in) as last_time
                    FROM attendance a
                    JOIN students s ON a.student_id = s.id
                    WHERE a.date = ?
                    GROUP BY a.student_id
                    ORDER BY last_time DESC
                    LIMIT 5
                ''', (today,))
                
                recent_activity = [
                    {'name': row['name'], 'time': row['last_time']}
                    for row in cursor.fetchall()
                ]
                
                return {
                    'total_students': total_students,
                    'present_today': present_today,
                    'absent_today': total_students - present_today,
                    'departed': departed,
                    'still_present': present_today - departed,
                    'attendance_rate': round((present_today / total_students * 100) if total_students > 0 else 0, 1),
                    'recent_activity': recent_activity,
                }
        except Exception as e:
            logger.error(f"Error getting class overview: {e}")
            return {}
    
    def get_attendance_pattern_analysis(self, days_back: int = 30) -> Dict:
        """Analyze attendance patterns across the class"""
        try:
            with self.db_connection() as conn:
                cursor = conn.cursor()
                
                start_date = (date.today() - timedelta(days=days_back)).isoformat()
                end_date = date.today().isoformat()
                
                # Get daily attendance statistics
                cursor.execute('''
                    SELECT a.date, COUNT(DISTINCT a.student_id) as present_count
                    FROM attendance a
                    WHERE a.date BETWEEN ? AND ? AND a.time_in IS NOT NULL
                    GROUP BY a.date
                    ORDER BY a.date DESC
                ''', (start_date, end_date))
                
                daily_stats = []
                for row in cursor.fetchall():
                    daily_stats.append({
                        'date': row['date'],
                        'present': row['present_count'],
                    })
                
                # Get most absent students
                cursor.execute('''
                    SELECT s.id, s.name, COUNT(DISTINCT a.date) as days_absent
                    FROM students s
                    LEFT JOIN attendance a ON s.id = a.student_id 
                        AND a.date BETWEEN ? AND ?
                    WHERE s.is_active = 1
                    GROUP BY s.id
                    HAVING days_absent < 15
                    ORDER BY days_absent DESC
                    LIMIT 10
                ''', (start_date, end_date))
                
                most_absent = [
                    {'name': row['name'], 'absent_days': row['days_absent']}
                    for row in cursor.fetchall()
                ]
                
                avg_present = sum([s['present'] for s in daily_stats]) / len(daily_stats) if daily_stats else 0
                
                return {
                    'period_days': days_back,
                    'daily_stats': daily_stats,
                    'avg_daily_attendance': round(avg_present, 1),
                    'most_absent_students': most_absent,
                }
        except Exception as e:
            logger.error(f"Error analyzing patterns: {e}")
            return {}

    def generate_live_tracking_report(self, days_back: int = 7) -> Dict:
        """Generate a compact live tracking report for dashboards and downloads."""
        try:
            class_overview = self.get_class_tracking_overview()
            pattern_data = self.get_attendance_pattern_analysis(days_back=days_back)
            students_status = self.get_all_students_status()

            active_alerts: List[Dict] = []
            try:
                from services.alert_service import AlertService

                active_alerts = AlertService().get_active_alerts()
            except Exception as alert_error:
                logger.error(f"Error loading alerts for report: {alert_error}")

            status_counts = {
                'present': len([s for s in students_status if s.get('status') == 'present']),
                'completed': len([s for s in students_status if s.get('status') == 'completed']),
                'absent': len([s for s in students_status if s.get('status') == 'absent']),
            }

            top_alerts = sorted(
                active_alerts,
                key=lambda item: (
                    item.get('severity', '') != 'critical',
                    item.get('severity', ''),
                    item.get('created_at', ''),
                ),
            )[:5]

            top_students = [
                {
                    'student_id': student['student_id'],
                    'name': student['name'],
                    'roll_number': student['roll_number'],
                    'status': student['status'],
                    'time_in': student['time_in'],
                    'time_out': student['time_out'],
                }
                for student in students_status[:10]
            ]

            report = {
                'generated_at': datetime.now().isoformat(timespec='seconds'),
                'period_days': days_back,
                'summary': {
                    'total_students': class_overview.get('total_students', 0),
                    'present_today': class_overview.get('present_today', 0),
                    'absent_today': class_overview.get('absent_today', 0),
                    'attendance_rate': class_overview.get('attendance_rate', 0),
                    'active_alerts': len(active_alerts),
                    'critical_alerts': len([a for a in active_alerts if a.get('severity') == 'critical']),
                },
                'status_counts': status_counts,
                'recent_activity': class_overview.get('recent_activity', []),
                'top_alerts': top_alerts,
                'top_students': top_students,
                'pattern_analysis': pattern_data,
                'insights': self._build_report_insights(class_overview, active_alerts, pattern_data),
            }

            return report
        except Exception as e:
            logger.error(f"Error generating live tracking report: {e}")
            return {}

    def _build_report_insights(self, class_overview: Dict, active_alerts: List[Dict], pattern_data: Dict) -> List[str]:
        """Build short, actionable insights for the live tracking report."""
        insights = []

        attendance_rate = class_overview.get('attendance_rate', 0)
        critical_alerts = len([a for a in active_alerts if a.get('severity') == 'critical'])
        warning_alerts = len([a for a in active_alerts if a.get('severity') == 'warning'])

        if attendance_rate >= 90:
            insights.append(f"Attendance is strong at {attendance_rate:.1f}%.")
        elif attendance_rate >= 75:
            insights.append(f"Attendance is moderate at {attendance_rate:.1f}%; a small drop may need attention.")
        else:
            insights.append(f"Attendance is low at {attendance_rate:.1f}% and should be reviewed.")

        if critical_alerts:
            insights.append(f"There are {critical_alerts} critical alert(s) requiring immediate review.")
        elif warning_alerts:
            insights.append(f"There are {warning_alerts} warning alert(s) to monitor.")

        daily_stats = pattern_data.get('daily_stats', []) if isinstance(pattern_data, dict) else []
        if daily_stats:
            latest = daily_stats[0].get('present', 0)
            insights.append(f"Latest tracked day shows {latest} present student(s).")

        return insights[:3]
    
    def _calculate_duration(self, time_in: Optional[str], time_out: Optional[str]) -> Optional[str]:
        """Calculate duration between time_in and time_out"""
        try:
            if not time_in:
                return None
            if not time_out:
                return None
            
            in_dt = datetime.fromisoformat(time_in)
            out_dt = datetime.fromisoformat(time_out)
            duration = out_dt - in_dt
            
            hours = duration.seconds // 3600
            minutes = (duration.seconds % 3600) // 60
            
            return f"{hours}h {minutes}m"
        except:
            return None
    
    def _determine_trend(self, records: List) -> str:
        """Determine attendance trend from recent records"""
        if len(records) < 5:
            return "insufficient_data"
        
        recent_present = len([r for r in records[:5] if r['time_in']])
        older_present = len([r for r in records[5:10] if r['time_in']]) if len(records) >= 10 else 0
        
        if recent_present > older_present + 1:
            return "improving"
        elif recent_present < older_present - 1:
            return "declining"
        else:
            return "stable"
    
    def _generate_recommendations(self, attendance_rate: float, 
                                 late_arrivals: int, early_departures: int) -> List[str]:
        """Generate recommendations based on attendance data"""
        recommendations = []
        
        if attendance_rate < 75:
            recommendations.append("Attendance rate is below 75%. Focus on being present daily.")
        
        if late_arrivals > 5:
            recommendations.append("Multiple late arrivals detected. Try arriving earlier.")
        
        if early_departures > 3:
            recommendations.append("Leaving early multiple times. Maintain full duration.")
        
        if attendance_rate >= 90 and late_arrivals == 0:
            recommendations.append("Great! Excellent attendance and punctuality.")
        
        return recommendations
