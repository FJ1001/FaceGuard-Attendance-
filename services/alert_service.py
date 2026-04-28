"""
Alert management service for real-time tracking and notifications
Handles generating, storing, and retrieving alerts for students
"""
import logging
from typing import List, Dict, Tuple, Optional, Any
from datetime import datetime, date, timedelta
from enum import Enum
from database.connection import get_db_connection

logger = logging.getLogger(__name__)


class AlertSeverity(Enum):
    """Alert severity levels"""
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


class AlertType(Enum):
    """Types of alerts"""
    # Focus/Attention alerts
    LOW_FOCUS = "low_focus"
    BLURRY_IMAGE = "blurry_image"
    OFF_CENTER = "off_center"
    POOR_LIGHTING = "poor_lighting"
    NO_FACE_DETECTED = "no_face_detected"
    
    # Mask detection
    MASK_DETECTED = "mask_detected"
    
    # Attendance alerts
    LATE_ARRIVAL = "late_arrival"
    EARLY_DEPARTURE = "early_departure"
    ABNORMAL_PATTERN = "abnormal_pattern"
    NOT_MARKED = "not_marked"
    
    # Tracking alerts
    RECOGNITION_FAILED = "recognition_failed"
    MULTIPLE_DETECTIONS = "multiple_detections"


class AlertService:
    """Service for managing alerts and tracking events"""
    
    def __init__(self):
        self.db_connection = get_db_connection
        self._ensure_alerts_table()
    
    def _ensure_alerts_table(self):
        """Ensure alerts table exists in database"""
        try:
            with self.db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS alerts (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        student_id INTEGER NOT NULL,
                        alert_type TEXT NOT NULL,
                        severity TEXT NOT NULL,
                        title TEXT NOT NULL,
                        message TEXT NOT NULL,
                        metadata TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        resolved_at TIMESTAMP,
                        resolved BOOLEAN DEFAULT 0,
                        FOREIGN KEY (student_id) REFERENCES students(id)
                    )
                ''')
                
                # Create indexes for faster queries
                cursor.execute('''
                    CREATE INDEX IF NOT EXISTS idx_alerts_student_date 
                    ON alerts(student_id, created_at DESC)
                ''')
                cursor.execute('''
                    CREATE INDEX IF NOT EXISTS idx_alerts_type 
                    ON alerts(alert_type, created_at DESC)
                ''')
                cursor.execute('''
                    CREATE INDEX IF NOT EXISTS idx_alerts_severity 
                    ON alerts(severity, created_at DESC)
                ''')
                
                conn.commit()
                logger.info("Alerts table ensured")
        except Exception as e:
            logger.error(f"Error ensuring alerts table: {e}")
    
    def create_focus_alert(self, student_id: int, alert_type: AlertType, 
                          analysis_data: Dict[str, Any]) -> bool:
        """Create a focus/energy alert based on analysis data"""
        try:
            severity_map = {
                AlertType.NO_FACE_DETECTED: AlertSeverity.CRITICAL,
                AlertType.LOW_FOCUS: AlertSeverity.WARNING,
                AlertType.BLURRY_IMAGE: AlertSeverity.WARNING,
                AlertType.OFF_CENTER: AlertSeverity.INFO,
                AlertType.POOR_LIGHTING: AlertSeverity.WARNING,
            }
            
            severity = severity_map.get(alert_type, AlertSeverity.INFO)
            
            # Create alert message based on analysis
            title_map = {
                AlertType.NO_FACE_DETECTED: "❌ No Face Detected",
                AlertType.LOW_FOCUS: "⚠️ Low Focus Score",
                AlertType.BLURRY_IMAGE: "🌀 Image Too Blurry",
                AlertType.OFF_CENTER: "📍 Face Off-Center",
                AlertType.POOR_LIGHTING: "💡 Poor Lighting",
            }
            
            title = title_map.get(alert_type, "Focus Alert")
            
            focus_score = analysis_data.get('focus_score', 0)
            brightness = analysis_data.get('brightness', 0)
            clarity = analysis_data.get('clarity', 0)
            
            message_map = {
                AlertType.NO_FACE_DETECTED: "Center your face in the frame and face the camera.",
                AlertType.LOW_FOCUS: f"Focus score: {focus_score:.1f}/100. Try better lighting and centering.",
                AlertType.BLURRY_IMAGE: f"Clarity score: {clarity:.1f}. Stay still and improve lighting.",
                AlertType.OFF_CENTER: "Move your face toward the center of the frame.",
                AlertType.POOR_LIGHTING: f"Brightness: {brightness:.1f}/255. Improve lighting conditions.",
            }
            
            message = message_map.get(alert_type, "Please improve your positioning and lighting.")
            
            return self.create_alert(
                student_id=student_id,
                alert_type=alert_type,
                severity=severity,
                title=title,
                message=message,
                metadata=analysis_data
            )
        except Exception as e:
            logger.error(f"Error creating focus alert: {e}")
            return False
    
    def create_mask_alert(self, student_id: int, confidence: float) -> bool:
        """Create a mask detection alert"""
        try:
            return self.create_alert(
                student_id=student_id,
                alert_type=AlertType.MASK_DETECTED,
                severity=AlertSeverity.WARNING,
                title="😷 Mask Detected",
                message=f"Mask detected with {confidence*100:.1f}% confidence. Remove mask for attendance marking.",
                metadata={"mask_confidence": confidence}
            )
        except Exception as e:
            logger.error(f"Error creating mask alert: {e}")
            return False
    
    def create_attendance_alert(self, student_id: int, alert_type: AlertType, 
                               details: Dict[str, Any]) -> bool:
        """Create an attendance-related alert"""
        try:
            title_map = {
                AlertType.LATE_ARRIVAL: "⏰ Late Arrival",
                AlertType.EARLY_DEPARTURE: "🚪 Early Departure",
                AlertType.ABNORMAL_PATTERN: "⚠️ Abnormal Pattern",
                AlertType.NOT_MARKED: "📋 Not Marked",
                AlertType.RECOGNITION_FAILED: "❌ Recognition Failed",
            }
            
            title = title_map.get(alert_type, "Attendance Alert")
            message = details.get('message', f"Attendance issue detected: {alert_type.value}")
            
            severity = AlertSeverity.WARNING
            if alert_type in [AlertType.NOT_MARKED, AlertType.ABNORMAL_PATTERN]:
                severity = AlertSeverity.CRITICAL
            
            return self.create_alert(
                student_id=student_id,
                alert_type=alert_type,
                severity=severity,
                title=title,
                message=message,
                metadata=details
            )
        except Exception as e:
            logger.error(f"Error creating attendance alert: {e}")
            return False
    
    def create_alert(self, student_id: int, alert_type: AlertType, 
                    severity: AlertSeverity, title: str, message: str,
                    metadata: Optional[Dict] = None) -> bool:
        """Create and store an alert"""
        try:
            import json
            
            with self.db_connection() as conn:
                cursor = conn.cursor()
                
                metadata_json = json.dumps(metadata) if metadata else None
                
                cursor.execute('''
                    INSERT INTO alerts 
                    (student_id, alert_type, severity, title, message, metadata)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (
                    student_id,
                    alert_type.value,
                    severity.value,
                    title,
                    message,
                    metadata_json
                ))
                
                conn.commit()
                logger.info(f"Alert created for student {student_id}: {title}")
                return True
        except Exception as e:
            logger.error(f"Error creating alert: {e}")
            return False
    
    def get_active_alerts(self, student_id: Optional[int] = None, 
                         severity: Optional[AlertSeverity] = None) -> List[Dict]:
        """Get active (unresolved) alerts"""
        try:
            with self.db_connection() as conn:
                cursor = conn.cursor()
                
                query = '''
                    SELECT id, student_id, alert_type, severity, title, message, 
                           metadata, created_at
                    FROM alerts
                    WHERE resolved = 0
                '''
                params = []
                
                if student_id:
                    query += " AND student_id = ?"
                    params.append(student_id)
                
                if severity:
                    query += " AND severity = ?"
                    params.append(severity.value)
                
                query += " ORDER BY created_at DESC LIMIT 100"
                
                cursor.execute(query, params)
                alerts = []
                
                for row in cursor.fetchall():
                    import json
                    alert = {
                        'id': row['id'],
                        'student_id': row['student_id'],
                        'alert_type': row['alert_type'],
                        'severity': row['severity'],
                        'title': row['title'],
                        'message': row['message'],
                        'metadata': json.loads(row['metadata']) if row['metadata'] else {},
                        'created_at': row['created_at'],
                    }
                    alerts.append(alert)
                
                return alerts
        except Exception as e:
            logger.error(f"Error fetching active alerts: {e}")
            return []
    
    def get_alert_history(self, student_id: Optional[int] = None, 
                         days_back: int = 7, limit: int = 100) -> List[Dict]:
        """Get historical alerts"""
        try:
            with self.db_connection() as conn:
                cursor = conn.cursor()
                
                start_date = datetime.now() - timedelta(days=days_back)
                
                query = '''
                    SELECT id, student_id, alert_type, severity, title, message,
                           metadata, created_at, resolved_at
                    FROM alerts
                    WHERE created_at >= ?
                '''
                params = [start_date]
                
                if student_id:
                    query += " AND student_id = ?"
                    params.append(student_id)
                
                query += " ORDER BY created_at DESC LIMIT ?"
                params.append(limit)
                
                cursor.execute(query, params)
                alerts = []
                
                for row in cursor.fetchall():
                    import json
                    alert = {
                        'id': row['id'],
                        'student_id': row['student_id'],
                        'alert_type': row['alert_type'],
                        'severity': row['severity'],
                        'title': row['title'],
                        'message': row['message'],
                        'metadata': json.loads(row['metadata']) if row['metadata'] else {},
                        'created_at': row['created_at'],
                        'resolved_at': row['resolved_at'],
                    }
                    alerts.append(alert)
                
                return alerts
        except Exception as e:
            logger.error(f"Error fetching alert history: {e}")
            return []
    
    def resolve_alert(self, alert_id: int) -> bool:
        """Mark an alert as resolved"""
        try:
            with self.db_connection() as conn:
                cursor = conn.cursor()
                now = datetime.now().isoformat(timespec="seconds")
                
                cursor.execute('''
                    UPDATE alerts
                    SET resolved = 1, resolved_at = ?
                    WHERE id = ?
                ''', (now, alert_id))
                
                conn.commit()
                return True
        except Exception as e:
            logger.error(f"Error resolving alert: {e}")
            return False
    
    def get_student_alert_stats(self, student_id: int, days_back: int = 7) -> Dict:
        """Get alert statistics for a student"""
        try:
            with self.db_connection() as conn:
                cursor = conn.cursor()
                
                start_date = datetime.now() - timedelta(days=days_back)
                
                # Get alert counts by severity
                cursor.execute('''
                    SELECT severity, COUNT(*) as count
                    FROM alerts
                    WHERE student_id = ? AND created_at >= ?
                    GROUP BY severity
                ''', (student_id, start_date))
                
                severity_counts = {row['severity']: row['count'] for row in cursor.fetchall()}
                
                # Get alert counts by type
                cursor.execute('''
                    SELECT alert_type, COUNT(*) as count
                    FROM alerts
                    WHERE student_id = ? AND created_at >= ?
                    GROUP BY alert_type
                    ORDER BY count DESC
                    LIMIT 5
                ''', (student_id, start_date))
                
                type_counts = {row['alert_type']: row['count'] for row in cursor.fetchall()}
                
                # Get total active alerts
                cursor.execute('''
                    SELECT COUNT(*) FROM alerts
                    WHERE student_id = ? AND resolved = 0
                ''', (student_id,))
                
                active_count = cursor.fetchone()[0]
                
                return {
                    'total_alerts': sum(severity_counts.values()),
                    'active_alerts': active_count,
                    'by_severity': severity_counts,
                    'by_type': type_counts,
                    'critical_count': severity_counts.get('critical', 0),
                    'warning_count': severity_counts.get('warning', 0),
                }
        except Exception as e:
            logger.error(f"Error getting alert stats: {e}")
            return {
                'total_alerts': 0,
                'active_alerts': 0,
                'by_severity': {},
                'by_type': {},
                'critical_count': 0,
                'warning_count': 0,
            }
    
    def get_system_alert_summary(self) -> Dict:
        """Get system-wide alert summary"""
        try:
            with self.db_connection() as conn:
                cursor = conn.cursor()
                
                # Total active alerts
                cursor.execute("SELECT COUNT(*) FROM alerts WHERE resolved = 0")
                total_active = cursor.fetchone()[0]
                
                # Critical alerts
                cursor.execute('''
                    SELECT COUNT(*) FROM alerts 
                    WHERE resolved = 0 AND severity = 'critical'
                ''')
                critical = cursor.fetchone()[0]
                
                # Students with active alerts
                cursor.execute('''
                    SELECT COUNT(DISTINCT student_id) FROM alerts 
                    WHERE resolved = 0
                ''')
                students_with_alerts = cursor.fetchone()[0]
                
                # Most common alert type
                cursor.execute('''
                    SELECT alert_type, COUNT(*) as count
                    FROM alerts
                    WHERE resolved = 0
                    GROUP BY alert_type
                    ORDER BY count DESC
                    LIMIT 1
                ''')
                
                most_common = cursor.fetchone()
                
                return {
                    'total_active': total_active,
                    'critical': critical,
                    'students_affected': students_with_alerts,
                    'most_common_type': most_common[0] if most_common else None,
                }
        except Exception as e:
            logger.error(f"Error getting system alert summary: {e}")
            return {
                'total_active': 0,
                'critical': 0,
                'students_affected': 0,
                'most_common_type': None,
            }
