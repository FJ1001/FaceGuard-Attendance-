# Live Tracking & Alerts Enhancement Guide

## Overview

This enhancement adds comprehensive real-time tracking and alert capabilities to the EyeAmHere attendance system. The system now provides:

- **Real-time Student Tracking** - Live status of all students (in/out/completed)
- **Multi-Type Alert System** - Focus, mask, attendance, and tracking alerts
- **Alert Management** - View, resolve, and analyze historical alerts
- **Student Insights** - Detailed tracking data and attendance patterns
- **Interactive Dashboards** - Real-time monitoring and analytics

---

## New Components

### 1. Alert Service (`services/alert_service.py`)

**Purpose**: Generates, stores, and retrieves system alerts

**Key Classes**:
- `AlertSeverity` - Enum: INFO, WARNING, CRITICAL
- `AlertType` - Enum: Focus alerts, mask alerts, attendance alerts, tracking alerts
- `AlertService` - Main service for alert management

**Main Methods**:

```python
# Create different types of alerts
alert_service.create_focus_alert(student_id, AlertType.LOW_FOCUS, analysis_data)
alert_service.create_mask_alert(student_id, confidence_score)
alert_service.create_attendance_alert(student_id, AlertType.LATE_ARRIVAL, details)

# Retrieve alerts
active_alerts = alert_service.get_active_alerts()
history = alert_service.get_alert_history(student_id, days_back=7)
stats = alert_service.get_student_alert_stats(student_id)
summary = alert_service.get_system_alert_summary()

# Manage alerts
alert_service.resolve_alert(alert_id)
```

**Database Schema**:
```sql
CREATE TABLE alerts (
    id INTEGER PRIMARY KEY,
    student_id INTEGER,
    alert_type TEXT,
    severity TEXT,
    title TEXT,
    message TEXT,
    metadata TEXT,
    created_at TIMESTAMP,
    resolved_at TIMESTAMP,
    resolved BOOLEAN
)
```

### 2. Tracking Data Service (`services/tracking_data_service.py`)

**Purpose**: Retrieves real-time and historical student tracking data

**Key Methods**:

```python
tracking_service = TrackingDataService()

# Real-time data
status = tracking_service.get_student_current_status(student_id)
all_status = tracking_service.get_all_students_status()
class_overview = tracking_service.get_class_tracking_overview()

# Historical data
history = tracking_service.get_student_tracking_history(student_id, days_back=7)
metrics = tracking_service.get_student_focus_metrics(student_id)
insights = tracking_service.get_student_attendance_insights(student_id)

# Analysis
patterns = tracking_service.get_attendance_pattern_analysis(days_back=30)
```

**Data Returned**:
- Current status (IN/OUT/COMPLETED/ABSENT)
- Time IN/OUT timestamps
- Duration calculations
- Attendance rate percentage
- Late arrival/early departure counts
- Trend analysis
- Recommendations

### 3. Live Tracking Dashboard (`ui/pages/live_tracking_page.py`)

**Location**: 🎯 Live Tracking & Alerts (Admin Navigation)

**Features**:
- **System Status Cards** - Total students, present/absent, attendance rate, active alerts
- **Active Alerts Section** - Critical, warning, and info alerts with resolution buttons
- **Real-Time Student Status** - Live table showing all students and their status
- **Attendance Metrics** - Pie chart and breakdown of today's attendance
- **Pattern Analysis** - 7-day attendance trends with most absent students

**Usage**:
```python
from ui.pages.live_tracking_page import LiveTrackingPage

page = LiveTrackingPage()
page.render()
```

### 4. Alert History Page (`ui/pages/alert_history_page.py`)

**Location**: 🔔 Alert History (Admin Navigation)

**Features**:

**Tab 1: Overview**
- Alert statistics (critical, total active, affected students)
- Alert type distribution chart
- Alert severity distribution pie chart

**Tab 2: History**
- Filterable alert history (by time period, severity, status)
- Alert details with student names
- Bulk resolution capabilities

**Tab 3: Student Alerts**
- Per-student alert statistics
- Student-specific alert breakdown
- Attendance insights and recommendations
- Recent alerts for selected student

**Usage**:
```python
from ui.pages.alert_history_page import AlertHistoryPage

page = AlertHistoryPage()
page.render()
```

---

## Integration with Existing Components

### Integrating with Attendance Page

When marking attendance, create alerts for any issues detected:

```python
from services.alert_service import AlertService, AlertType

alert_service = AlertService()

# After recognition attempt
if recognition_failed:
    alert_service.create_attendance_alert(
        student_id=student_id,
        alert_type=AlertType.RECOGNITION_FAILED,
        details={
            'message': 'Face recognition failed',
            'reason': meta.get('reason'),
            'confidence': confidence
        }
    )
```

### Integrating with Focus Energy Service

Add focus alerts when analyzing frames:

```python
from services.alert_service import AlertService, AlertType

alert_service = AlertService()

# During focus analysis
if analysis['focus_score'] < FOCUS_ALERT_THRESHOLD:
    alert_service.create_focus_alert(
        student_id=student_id,
        alert_type=AlertType.LOW_FOCUS,
        analysis_data=analysis
    )
```

### Integrating with Mask Detection

Create mask alerts when mask is detected:

```python
from services.alert_service import AlertService, AlertType

alert_service = AlertService()

# During mask detection
if mask_detected:
    alert_service.create_mask_alert(
        student_id=student_id,
        confidence=mask_confidence
    )
```

---

## Alert Types Reference

### Focus/Energy Alerts
- `NO_FACE_DETECTED` - "❌ No Face Detected"
- `LOW_FOCUS` - "⚠️ Low Focus Score"
- `BLURRY_IMAGE` - "🌀 Image Too Blurry"
- `OFF_CENTER` - "📍 Face Off-Center"
- `POOR_LIGHTING` - "💡 Poor Lighting"

### Mask Detection Alerts
- `MASK_DETECTED` - "😷 Mask Detected"

### Attendance Alerts
- `LATE_ARRIVAL` - "⏰ Late Arrival"
- `EARLY_DEPARTURE` - "🚪 Early Departure"
- `ABNORMAL_PATTERN` - "⚠️ Abnormal Pattern"
- `NOT_MARKED` - "📋 Not Marked"
- `RECOGNITION_FAILED` - "❌ Recognition Failed"

### Tracking Alerts
- `MULTIPLE_DETECTIONS` - Multiple students detected in one frame

---

## Usage Examples

### Example 1: Check Active Alerts for a Student

```python
from services.alert_service import AlertService

alert_service = AlertService()

# Get active alerts for a specific student
student_id = 5
active_alerts = alert_service.get_active_alerts(student_id=student_id)

for alert in active_alerts:
    print(f"{alert['title']}: {alert['message']}")
    print(f"Severity: {alert['severity']}")
    print(f"Created: {alert['created_at']}")
```

### Example 2: Get Student Tracking Status

```python
from services.tracking_data_service import TrackingDataService

tracking_service = TrackingDataService()

# Get current status of all students
all_students = tracking_service.get_all_students_status()

for student in all_students:
    print(f"{student['name']}: {student['status']}")
    if student['time_in']:
        print(f"  IN: {student['time_in']}")
    if student['time_out']:
        print(f"  OUT: {student['time_out']}")
```

### Example 3: Get Student Insights

```python
from services.tracking_data_service import TrackingDataService

tracking_service = TrackingDataService()

# Get detailed insights for a student
insights = tracking_service.get_student_attendance_insights(student_id=5)

print(f"Attendance Rate: {insights['attendance_rate']}%")
print(f"Late Arrivals: {insights['late_arrivals']}")
print(f"Trend: {insights['trend']}")
print("\nRecommendations:")
for rec in insights['recommendations']:
    print(f"  - {rec}")
```

### Example 4: Create an Alert from Custom Logic

```python
from services.alert_service import AlertService, AlertType, AlertSeverity

alert_service = AlertService()

# Create custom alert
alert_service.create_alert(
    student_id=5,
    alert_type=AlertType.ABNORMAL_PATTERN,
    severity=AlertSeverity.WARNING,
    title="⚠️ Unusual Attendance Pattern",
    message="Student has been absent for 3 consecutive days",
    metadata={
        'days_absent': 3,
        'last_present': '2024-04-26',
        'pattern_detected': True
    }
)
```

---

## Dashboard Navigation

### Admin Access
From the admin dashboard sidebar:
1. **Review and Insights** section
   - 🎯 **Live Tracking & Alerts** - Real-time monitoring
   - 🔔 **Alert History** - Historical analysis and management

### Features by Role
- **Admins**: Full access to all tracking, alerts, and analytics
- **Users/Students**: Can only see their own attendance status

---

## Database Changes

The system automatically creates the required `alerts` table on first run. No manual database migration is needed.

**Alert Table Schema**:
```
alerts (
    id: INTEGER PRIMARY KEY,
    student_id: INTEGER (FK to students.id),
    alert_type: TEXT,
    severity: TEXT,
    title: TEXT,
    message: TEXT,
    metadata: TEXT (JSON),
    created_at: TIMESTAMP,
    resolved_at: TIMESTAMP,
    resolved: BOOLEAN
)
```

---

## Configuration Options

You can configure alert sensitivity in `config/settings.py`:

```python
# Focus alert thresholds
FOCUS_ALERT_THRESHOLD = 50  # Alert if focus score below 50%
FOCUS_WARNING_THRESHOLD = 70  # Warning if below 70%
FOCUS_MAX_BLUR_ALERT = 100  # Alert if blur above this

# Attendance timing
LATE_ARRIVAL_HOUR = 9  # Mark as late if after 9 AM
EARLY_DEPARTURE_HOUR = 15  # Mark as early if before 3 PM
```

---

## Performance Tips

1. **Limit Alert History Queries**: Use `days_back` parameter to limit data
2. **Batch Operations**: Get system summary instead of individual alerts when possible
3. **Caching**: Consider caching `get_all_students_status()` with 5-10 second intervals
4. **Pagination**: Use `limit` parameter in `get_alert_history()`

---

## Troubleshooting

### Alerts table not created
**Solution**: Restart the application. Table is auto-created on first alert creation.

### No alerts showing
**Check**:
1. Verify alerts are being created from recognition/focus services
2. Check database file exists and is writable
3. Verify student_id references exist in students table

### Performance issues with large datasets
**Solutions**:
1. Reduce `days_back` in queries
2. Add database indexes (auto-created)
3. Use pagination with `limit` parameter
4. Run cleanup queries to archive old resolved alerts

---

## Future Enhancements

Potential additions to the alert system:
- Email/SMS notifications for critical alerts
- Alert escalation workflows
- Automated actions (e.g., automatic absence marking)
- Machine learning for anomaly detection
- Alert customization per instructor/department
- Multi-language alert messages

---

## API Quick Reference

### Alert Service
```python
AlertService.create_focus_alert(student_id, alert_type, analysis_data)
AlertService.create_mask_alert(student_id, confidence)
AlertService.create_attendance_alert(student_id, alert_type, details)
AlertService.create_alert(student_id, alert_type, severity, title, message, metadata)
AlertService.get_active_alerts(student_id, severity)
AlertService.get_alert_history(student_id, days_back, limit)
AlertService.resolve_alert(alert_id)
AlertService.get_student_alert_stats(student_id, days_back)
AlertService.get_system_alert_summary()
```

### Tracking Data Service
```python
TrackingDataService.get_student_current_status(student_id)
TrackingDataService.get_all_students_status()
TrackingDataService.get_student_tracking_history(student_id, days_back)
TrackingDataService.get_student_focus_metrics(student_id, days_back)
TrackingDataService.get_student_attendance_insights(student_id)
TrackingDataService.get_class_tracking_overview()
TrackingDataService.get_attendance_pattern_analysis(days_back)
```

---

## Support & Questions

For issues or questions about the alert system:
1. Check this guide's troubleshooting section
2. Review the code documentation in service files
3. Check application logs in `logs/` directory
4. Verify database integrity using `scripts/` utilities

---

**Last Updated**: April 2024
**Version**: 1.0
