# Quick Start Guide - Live Tracking & Alerts

## What's New? 🎯

Your EyeAmHere system now has:

✅ **Real-Time Student Tracking** - See who's IN/OUT instantly
✅ **Smart Alert System** - Focus, mask, and attendance alerts
✅ **Live Dashboard** - Monitor everything at a glance
✅ **Alert History** - View and analyze past alerts
✅ **Student Insights** - Deep dive into attendance patterns

---

## Getting Started (30 seconds)

### Step 1: No Installation Needed! 
The system is already integrated. Just restart your Streamlit app:

```bash
streamlit run main.py
```

### Step 2: Access New Features in Admin Dashboard

**In the sidebar, look for:**

| Feature | Location | Icon |
|---------|----------|------|
| Live Tracking | Review & Insights → Live Tracking & Alerts | 🎯 |
| Alert History | Review & Insights → Alert History | 🔔 |

---

## What You Can Do Now

### 🎯 Live Tracking & Alerts Page

**Real-time monitoring with:**

1. **System Status** - See at a glance:
   - Total students
   - Who's present/absent
   - Current attendance rate
   - Active alerts

2. **Active Alerts** - Immediately see:
   - 🔴 Critical alerts (need action)
   - ⚠️ Warnings (monitor these)
   - ℹ️ Info alerts (for reference)

3. **Student Status Table** - Live list:
   - Student name and roll number
   - Current status (IN/OUT/COMPLETED)
   - Time in/out timestamps

4. **Attendance Metrics** - Visual breakdown:
   - Pie chart of today's attendance
   - 7-day attendance trends
   - Most absent students

---

### 🔔 Alert History Page

**Analyze alerts with three tabs:**

**📊 Overview Tab:**
- Total critical alerts
- All active alerts
- Students affected
- Alert type distribution charts

**📜 History Tab:**
- Filter alerts by time, severity, status
- See all alerts from last 30+ days
- Resolve individual alerts
- View alert details

**👤 Student Alerts Tab:**
- Select any student
- See their alert statistics
- View attendance insights
- Get personalized recommendations

---

## Key Features

### Alert Types

| Type | Example | What It Means |
|------|---------|---------------|
| 🔴 Critical | No Face Detected | Immediate issue |
| ⚠️ Warning | Low Focus Score | Needs attention |
| ℹ️ Info | Face Off-Center | Minor suggestion |

### Alert Categories

- **Focus/Attention** - Low focus, blurry, off-center, poor lighting, no face
- **Mask Detection** - Mask detected during attendance
- **Attendance** - Late arrival, early departure, abnormal pattern
- **Tracking** - Recognition failed, multiple detections

---

## Common Tasks

### Find Why a Student is Absent
1. Go to **Alert History → Student Alerts**
2. Select the student
3. Check their attendance insights and recommendations

### See Who Has Issues Today
1. Go to **Live Tracking & Alerts**
2. Look at "Active Alerts" section
3. Sort by severity (critical first)

### Review Last Week's Attendance Patterns
1. Go to **Alert History → Overview**
2. Charts show alert distribution
3. Check "Most Absent Students" section

### Check Specific Student's Focus Issues
1. Go to **Alert History → Student Alerts**
2. Select student
3. See breakdown of their focus-related alerts
4. View recommendations

---

## Alert Examples

### ✅ No Issues
```
✅ No active alerts. Everything is normal!
```

### ⚠️ Warning Alert
```
⚠️ LOW FOCUS SCORE
Focus score: 45.0/100. Try better lighting and centering.
👤 Created 5 minutes ago
```

### 🔴 Critical Alert
```
🔴 NO FACE DETECTED
Center your face in the frame and face the camera.
👤 Created 2 minutes ago
[Resolve] button
```

---

## Dashboard Widgets

All new pages integrate into your admin dashboard:

```
Admin Dashboard
├── Daily Operation
│   ├── Mark Attendance
│   ├── Student Management
│   └── Attendance Records
├── Review & Insights ← NEW!
│   ├── Dashboard Overview
│   ├── Analytics
│   ├── 🎯 Live Tracking & Alerts ← NEW!
│   └── 🔔 Alert History ← NEW!
└── Administration
    ├── System Health
    ├── Live Mask Detection
    ├── Focus & Energy Monitor
    ├── User Management
    └── Danger Zone
```

---

## Database

The system automatically creates the alerts table on first use. No action needed!

**What gets stored:**
- Alert type and severity
- Alert title and message
- Student ID
- Creation and resolution times
- Custom metadata

---

## Performance

✅ Optimized queries with indexes
✅ Efficient data retrieval  
✅ Handles hundreds of alerts
✅ Real-time updates

---

## Troubleshooting

### Q: I don't see the new pages
**A**: 
1. Restart Streamlit: `streamlit run main.py`
2. Log in as Admin
3. Check sidebar under "Review & Insights"

### Q: No alerts are showing
**A**: 
1. Alerts are created when issues occur
2. Try marking attendance with issues (low light, bad focus)
3. Check database has alerts table

### Q: Data looks wrong
**A**: 
1. Refresh the page (F5 or 🔄 button)
2. Restart Streamlit
3. Check database file is not corrupted

---

## Tips & Tricks

💡 **Tip 1**: Use "Status Filter" in Live Tracking to focus on present/absent students

💡 **Tip 2**: Click the "Refresh Now" button for instant updates without waiting

💡 **Tip 3**: In Alert History, set filter to "Active" to only see current issues

💡 **Tip 4**: Export alert data for reporting (coming soon!)

💡 **Tip 5**: Check "Trend" in student insights to see if attendance is improving

---

## What Happens Behind the Scenes

When a student marks attendance:

```
Student Takes Photo
         ↓
System Analyzes Face
         ↓
✓ Recognition Success? → Check Attendance
           ↓ No
✗ Create Alert: Recognition Failed
                ↓
Check Time: Is it late (after 9 AM)?
           ↓ Yes
✗ Create Alert: Late Arrival
                ↓
Check Focus Quality
           ↓ Low
✗ Create Alert: Low Focus
                ↓
All alerts visible in Live Tracking & Alert History
```

---

## Next Steps

### To learn more:
1. Read [LIVE_TRACKING_GUIDE.md](LIVE_TRACKING_GUIDE.md) for detailed documentation
2. Check [INTEGRATION_EXAMPLES.md](INTEGRATION_EXAMPLES.md) for code examples
3. Browse the new service files:
   - `services/alert_service.py` - Alert management
   - `services/tracking_data_service.py` - Tracking data
   - `ui/pages/live_tracking_page.py` - Dashboard
   - `ui/pages/alert_history_page.py` - History

### To integrate with your code:
1. See INTEGRATION_EXAMPLES.md for ready-to-use code
2. Add alerts to attendance marking
3. Add alerts to focus monitoring
4. Add alerts to mask detection

### To customize:
1. Modify alert messages in `services/alert_service.py`
2. Adjust alert thresholds in `config/settings.py`
3. Add custom alert types to `AlertType` enum
4. Create new dashboard widgets

---

## Support

**Questions?** Check:
1. This Quick Start guide
2. LIVE_TRACKING_GUIDE.md for technical details
3. INTEGRATION_EXAMPLES.md for code samples
4. Logs in `logs/` directory

**Found a bug?** Check the logs:
```bash
tail -f logs/app.log
```

---

## What's Coming Soon 🚀

- Email notifications for critical alerts
- Alert escalation workflows
- Automatic report generation
- Custom alert rules
- Machine learning anomaly detection
- Mobile app integration

---

**Version**: 1.0  
**Last Updated**: April 2024  
**Status**: ✅ Production Ready
