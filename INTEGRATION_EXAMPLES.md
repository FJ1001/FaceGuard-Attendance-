# Integration Examples for Live Tracking & Alerts

This file provides practical examples of how to integrate the alert system into existing EyeAmHere components.

## Example 1: Add Alerts to Attendance Marking

**File**: `services/attendance_service.py`

```python
from services.alert_service import AlertService, AlertType

class AttendanceService:
    def __init__(self):
        self.attendance_repo = AttendanceRepository()
        self.student_service = StudentService()
        self.alert_service = AlertService()  # Add this
    
    def mark_attendance_by_recognition(self, image, marked_by: str = 'system'):
        """Mark attendance using face recognition"""
        try:
            is_recognized, student_info, confidence, meta = self.student_service.recognize_student(image)

            if not is_recognized:
                message = self._recognition_failure_message(meta, confidence)
                
                # ADD: Create alert for failed recognition
                self.alert_service.create_attendance_alert(
                    student_id=meta.get('student_id'),
                    alert_type=AlertType.RECOGNITION_FAILED,
                    details={
                        'message': message,
                        'reason': meta.get('reason'),
                        'confidence': confidence,
                        'threshold': meta.get('threshold'),
                    }
                ) if meta.get('student_id') else None
                
                return False, message, None

            success, message = self.attendance_repo.mark_attendance(
                student_info['student_id'], 'present', marked_by
            )
            
            # ADD: Check for late arrival and create alert if needed
            if success:
                from datetime import datetime, time
                current_time = datetime.now().time()
                if current_time > time(9, 0):  # After 9 AM
                    self.alert_service.create_attendance_alert(
                        student_id=student_info['student_id'],
                        alert_type=AlertType.LATE_ARRIVAL,
                        details={
                            'message': f'Late arrival at {current_time.strftime("%H:%M")}',
                            'arrival_time': current_time.isoformat(),
                        }
                    )

            student_info['recognition_confidence'] = confidence
            student_info['recognition_margin'] = meta.get('margin_achieved')
            student_info['runner_up_similarity'] = meta.get('second_similarity')

            return success, message, student_info

        except Exception as e:
            logger.error(f"Error marking attendance by recognition: {e}")
            return False, f"Error marking attendance: {str(e)}", None
```

---

## Example 2: Add Alerts to Focus Energy Service

**File**: `face_focus/focus_energy_service.py`

```python
class FocusEnergyService:
    def __init__(self):
        self.face_cascade = cv2.CascadeClassifier(...)
        self.eye_cascade = cv2.CascadeClassifier(...)
        self.alert_service = AlertService()  # Add this
    
    def analyze_image(self, image_bgr: np.ndarray, student_id: int = None) -> Dict[str, Any]:
        """Return a score, status, and alerts for a single frame."""
        # ... existing analysis code ...
        
        result = {
            "focus_score": focus_score,
            "status": status,
            "energy_score": energy_score,
            "alerts": alerts,
            # ... other fields ...
        }
        
        # ADD: Create alert if significant issue detected
        if student_id and status == "critical":
            # Determine alert type
            if not face_detected:
                alert_type = AlertType.NO_FACE_DETECTED
            elif clarity < 50:
                alert_type = AlertType.BLURRY_IMAGE
            elif brightness < 50:
                alert_type = AlertType.POOR_LIGHTING
            else:
                alert_type = AlertType.LOW_FOCUS
            
            # Create the alert
            self.alert_service.create_focus_alert(
                student_id=student_id,
                alert_type=alert_type,
                analysis_data={
                    'focus_score': focus_score,
                    'brightness': brightness,
                    'clarity': clarity,
                    'face_detected': face_detected,
                    'centering': result.get('components', {}).get('centering', 0),
                }
            )
        
        return result
```

---

## Example 3: Add Alerts to Mask Detection

**File**: `face_mask/mask_gate.py`

```python
from services.alert_service import AlertService, AlertType

class MaskGate:
    def __init__(self):
        self.detector = YOLOMaskDetector()
        self.alert_service = AlertService()  # Add this
    
    def check_mask_status(self, frame, student_id: int = None) -> Dict:
        """Check mask status in frame"""
        detections = self.detector.detect(frame)
        
        results = {
            'mask_detected': False,
            'confidence': 0,
            'count': 0,
        }
        
        for detection in detections:
            if detection['class'] == 'with_mask':
                results['mask_detected'] = True
                results['confidence'] = detection['confidence']
                results['count'] += 1
                
                # ADD: Create alert when mask detected
                if student_id:
                    self.alert_service.create_mask_alert(
                        student_id=student_id,
                        confidence=detection['confidence']
                    )
        
        return results
```

---

## Example 4: Add Attendance Anomaly Detection

**File**: `services/attendance_service.py`

```python
from services.alert_service import AlertService, AlertType
from datetime import datetime, timedelta

class AttendanceService:
    def __init__(self):
        self.attendance_repo = AttendanceRepository()
        self.student_service = StudentService()
        self.alert_service = AlertService()
    
    def detect_abnormal_patterns(self, student_id: int):
        """Detect abnormal attendance patterns"""
        try:
            # Get last 10 days of attendance
            end_date = date.today()
            start_date = end_date - timedelta(days=10)
            
            records = self.get_attendance_records(
                start_date=start_date,
                end_date=end_date,
                student_id=student_id
            )
            
            # Check for consecutive absences
            if len(records) == 0:
                # Student absent for entire 10 days
                self.alert_service.create_attendance_alert(
                    student_id=student_id,
                    alert_type=AlertType.ABNORMAL_PATTERN,
                    details={
                        'message': f'Student absent for {10} consecutive days',
                        'days_absent': 10,
                        'pattern': 'extended_absence'
                    }
                )
                return
            
            # Check for early departures
            early_departures = 0
            for record in records:
                if record.get('time_out'):
                    time_out = datetime.fromisoformat(record['time_out']).time()
                    if time_out.hour < 15:  # Before 3 PM
                        early_departures += 1
            
            if early_departures >= 5:
                self.alert_service.create_attendance_alert(
                    student_id=student_id,
                    alert_type=AlertType.ABNORMAL_PATTERN,
                    details={
                        'message': f'Student has {early_departures} early departures in last 10 days',
                        'early_departures': early_departures,
                        'pattern': 'early_departures'
                    }
                )
        
        except Exception as e:
            logger.error(f"Error detecting abnormal patterns: {e}")
```

---

## Example 5: Create Custom Alert Dashboard Widget

**File**: `ui/components/alert_widget.py` (New File)

```python
import streamlit as st
from services.alert_service import AlertService, AlertSeverity
from datetime import datetime

class AlertWidget:
    """Reusable alert widget for displaying alerts in any page"""
    
    def __init__(self):
        self.alert_service = AlertService()
    
    def render_active_alerts_compact(self, max_alerts: int = 5):
        """Render compact active alerts widget"""
        alerts = self.alert_service.get_active_alerts()
        
        if not alerts:
            st.success("✅ No active alerts")
            return
        
        # Separate by severity
        critical = [a for a in alerts if a['severity'] == 'critical']
        warning = [a for a in alerts if a['severity'] == 'warning']
        
        if critical:
            st.error(f"🔴 {len(critical)} Critical Alert{'s' if len(critical) > 1 else ''}")
            for alert in critical[:max_alerts]:
                st.write(f"• {alert['title']}: {alert['message']}")
        
        if warning:
            st.warning(f"⚠️ {len(warning)} Warning{'s' if len(warning) > 1 else ''}")
            for alert in warning[:max_alerts]:
                st.write(f"• {alert['title']}")
    
    def render_student_alerts_compact(self, student_id: int):
        """Render alerts for specific student"""
        alerts = self.alert_service.get_active_alerts(student_id=student_id)
        
        if not alerts:
            st.info("ℹ️ No active alerts for this student")
            return
        
        for alert in alerts[:3]:
            emoji = {
                'critical': '🔴',
                'warning': '⚠️',
                'info': 'ℹ️'
            }.get(alert['severity'], '•')
            
            st.write(f"{emoji} {alert['title']}")
            st.caption(alert['message'])
    
    def render_alert_timeline(self, student_id: int, days: int = 7):
        """Render timeline of alerts"""
        alerts = self.alert_service.get_alert_history(
            student_id=student_id,
            days_back=days
        )
        
        if not alerts:
            st.info("No alerts in this period")
            return
        
        # Group by date
        from collections import defaultdict
        by_date = defaultdict(list)
        
        for alert in alerts:
            date_str = alert['created_at'][:10]
            by_date[date_str].append(alert)
        
        # Render timeline
        for date_str in sorted(by_date.keys(), reverse=True):
            with st.expander(f"📅 {date_str}"):
                for alert in by_date[date_str]:
                    time_str = alert['created_at'][11:19]
                    st.write(f"**{time_str}**: {alert['title']}")
                    st.caption(alert['message'])

# Usage in other pages:
# from ui.components.alert_widget import AlertWidget
# widget = AlertWidget()
# widget.render_alert_timeline(student_id=5, days=7)
```

---

## Example 6: Add Alert Summary to Dashboard

**File**: `ui/pages/dashboard_page.py`

```python
# In _render_admin_dashboard method, add:

def _render_alert_summary_card(self):
    """Render alert summary card in dashboard"""
    from services.alert_service import AlertService
    
    alert_service = AlertService()
    summary = alert_service.get_system_alert_summary()
    
    with st.container(border=True):
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if summary['critical'] > 0:
                st.error(f"🔴 {summary['critical']} Critical")
            else:
                st.success("✅ No Critical")
        
        with col2:
            st.info(f"🔔 {summary['total_active']} Active")
        
        with col3:
            st.warning(f"⚠️ {summary['students_affected']} Affected")
        
        if st.button("View Details →", use_container_width=True):
            st.session_state.current_page = "Live Tracking & Alerts"
            st.rerun()
```

---

## Example 7: Scheduled Alert Cleanup (Optional)

**File**: `scripts/cleanup_alerts.py` (New File)

```python
"""
Script to clean up old resolved alerts periodically
Run this daily or weekly to maintain database performance
"""
import logging
from datetime import datetime, timedelta
from database.connection import get_db_connection

logger = logging.getLogger(__name__)

def cleanup_old_alerts(days_to_keep: int = 30):
    """Remove resolved alerts older than specified days"""
    try:
        cutoff_date = (datetime.now() - timedelta(days=days_to_keep)).isoformat()
        
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # Delete old resolved alerts
            cursor.execute('''
                DELETE FROM alerts
                WHERE resolved = 1 AND resolved_at < ?
            ''', (cutoff_date,))
            
            deleted_count = cursor.rowcount
            conn.commit()
            
            logger.info(f"Cleaned up {deleted_count} old resolved alerts")
            return deleted_count
    
    except Exception as e:
        logger.error(f"Error cleaning up alerts: {e}")
        return 0

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    cleanup_old_alerts(days_to_keep=30)
```

---

## Example 8: Export Alerts to CSV

**File**: Add to `services/alert_service.py`

```python
def export_alerts_to_csv(self, filepath: str, days_back: int = 30):
    """Export alerts to CSV file"""
    try:
        import csv
        
        alerts = self.get_alert_history(days_back=days_back, limit=10000)
        
        with open(filepath, 'w', newline='', encoding='utf-8') as csvfile:
            fieldnames = [
                'student_id', 'alert_type', 'severity', 'title', 'message',
                'created_at', 'resolved_at', 'resolved'
            ]
            
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            
            for alert in alerts:
                writer.writerow({
                    'student_id': alert['student_id'],
                    'alert_type': alert['alert_type'],
                    'severity': alert['severity'],
                    'title': alert['title'],
                    'message': alert['message'],
                    'created_at': alert['created_at'],
                    'resolved_at': alert['resolved_at'],
                    'resolved': '✓' if alert['resolved_at'] else ''
                })
        
        logger.info(f"Exported {len(alerts)} alerts to {filepath}")
        return True
    
    except Exception as e:
        logger.error(f"Error exporting alerts: {e}")
        return False

# Usage:
# alert_service.export_alerts_to_csv('alerts_report.csv', days_back=7)
```

---

## Example 9: Real-time Alert Monitoring Task

**File**: `scripts/monitor_alerts.py` (New File)

```python
"""
Background task for monitoring and processing alerts
Can be run as a scheduled job or background service
"""
import logging
import time
from datetime import datetime, timedelta
from services.alert_service import AlertService, AlertType
from services.tracking_data_service import TrackingDataService
from database.connection import get_db_connection

logger = logging.getLogger(__name__)

class AlertMonitor:
    """Continuous alert monitoring and processing"""
    
    def __init__(self):
        self.alert_service = AlertService()
        self.tracking_service = TrackingDataService()
    
    def check_late_arrivals(self):
        """Periodically check for late arrivals"""
        try:
            cutoff_time = datetime.now().replace(hour=9, minute=0)
            
            if datetime.now() > cutoff_time:
                with get_db_connection() as conn:
                    cursor = conn.cursor()
                    
                    # Find unmarked students
                    cursor.execute('''
                        SELECT id FROM students
                        WHERE is_active = 1
                        AND id NOT IN (
                            SELECT DISTINCT student_id FROM attendance
                            WHERE date = date('now')
                        )
                    ''')
                    
                    for row in cursor.fetchall():
                        student_id = row[0]
                        
                        # Create alert for not marked
                        self.alert_service.create_attendance_alert(
                            student_id=student_id,
                            alert_type=AlertType.NOT_MARKED,
                            details={
                                'message': 'Student has not marked attendance',
                                'time_checked': datetime.now().isoformat()
                            }
                        )
            
        except Exception as e:
            logger.error(f"Error checking late arrivals: {e}")
    
    def run(self, interval_seconds: int = 300):
        """Run monitor continuously"""
        logger.info("Alert monitor started")
        
        try:
            while True:
                self.check_late_arrivals()
                time.sleep(interval_seconds)
        
        except KeyboardInterrupt:
            logger.info("Alert monitor stopped")
        except Exception as e:
            logger.error(f"Alert monitor error: {e}")

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    monitor = AlertMonitor()
    monitor.run(interval_seconds=60)  # Check every minute
```

---

## Testing Examples

**File**: `tests/test_alert_service.py` (New File)

```python
import pytest
from services.alert_service import AlertService, AlertType, AlertSeverity

def test_create_focus_alert():
    """Test creating a focus alert"""
    alert_service = AlertService()
    
    result = alert_service.create_focus_alert(
        student_id=1,
        alert_type=AlertType.LOW_FOCUS,
        analysis_data={
            'focus_score': 45,
            'brightness': 100,
            'clarity': 150
        }
    )
    
    assert result == True

def test_get_active_alerts():
    """Test retrieving active alerts"""
    alert_service = AlertService()
    
    alerts = alert_service.get_active_alerts()
    assert isinstance(alerts, list)

def test_resolve_alert():
    """Test resolving an alert"""
    alert_service = AlertService()
    
    # Create an alert first
    alert_service.create_focus_alert(1, AlertType.LOW_FOCUS, {})
    
    # Get active alerts
    alerts = alert_service.get_active_alerts()
    if alerts:
        result = alert_service.resolve_alert(alerts[0]['id'])
        assert result == True

def test_get_student_alert_stats():
    """Test getting alert statistics"""
    alert_service = AlertService()
    
    stats = alert_service.get_student_alert_stats(student_id=1)
    
    assert 'total_alerts' in stats
    assert 'active_alerts' in stats
    assert 'critical_count' in stats
```

---

These examples provide a foundation for integrating the alert system throughout the EyeAmHere application. Adapt them to your specific use cases and integrate incrementally to ensure stability.
