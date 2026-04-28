"""
Analytics service for attendance data - Fixed version
Provides meaningful insights and reports with correct percentage calculations
"""
import logging
from datetime import date, datetime, timedelta
from typing import Dict, List, Optional, Tuple
import pandas as pd
from database.connection import get_db_connection

logger = logging.getLogger(__name__)

class AnalyticsService:
    """Advanced analytics for attendance system with fixed calculations"""
    
    def __init__(self):
        self.db_connection = get_db_connection
    
    def get_comprehensive_analytics(self, days_back: int = 30) -> Dict:
        """Get comprehensive analytics for the dashboard"""
        try:
            end_date = date.today()
            start_date = end_date - timedelta(days=days_back)
            
            analytics = {
                'overview': self.get_overview_stats(),
                'daily_trends': self.get_daily_attendance_trends(start_date, end_date),
                'student_performance': self.get_student_performance_analysis(start_date, end_date),
                'course_analytics': self.get_course_wise_analytics(start_date, end_date),
                'time_patterns': self.get_time_pattern_analysis(start_date, end_date),
                'weekly_summary': self.get_weekly_summary(start_date, end_date),
                'alerts': self.get_attendance_alerts(),
                'predictions': self.get_trend_predictions(start_date, end_date)
            }
            # Add AI-generated narrative insights
            analytics['ai_insights'] = self.generate_ai_insights(analytics)
            
            return analytics
            
        except Exception as e:
            logger.error(f"Error generating analytics: {e}")
            return {}
    
    def get_overview_stats(self) -> Dict:
        """Get high-level overview statistics"""
        try:
            with self.db_connection() as conn:
                cursor = conn.cursor()
                
                # Total students
                cursor.execute("SELECT COUNT(*) FROM students WHERE is_active = 1")
                total_students = cursor.fetchone()[0]
                
                # Students with attendance today
                cursor.execute("""
                    SELECT COUNT(DISTINCT student_id) 
                    FROM attendance 
                    WHERE date = ? AND time_in IS NOT NULL
                """, (date.today(),))
                present_today = cursor.fetchone()[0]
                
                # Total attendance records
                cursor.execute("SELECT COUNT(*) FROM attendance")
                total_records = cursor.fetchone()[0]
                
                # Average daily attendance (last 30 days)
                cursor.execute("""
                    SELECT AVG(daily_count) FROM (
                        SELECT COUNT(DISTINCT student_id) as daily_count
                        FROM attendance 
                        WHERE date >= ? AND time_in IS NOT NULL
                        GROUP BY date
                    )
                """, (date.today() - timedelta(days=30),))
                
                avg_daily_result = cursor.fetchone()
                avg_daily = avg_daily_result[0] if avg_daily_result and avg_daily_result[0] else 0
                
                # Attendance rate calculation
                attendance_rate = (present_today / total_students * 100) if total_students > 0 else 0
                weekly_rate = (avg_daily / total_students * 100) if total_students > 0 and avg_daily > 0 else 0
                
                return {
                    'total_students': total_students,
                    'present_today': present_today,
                    'absent_today': max(0, total_students - present_today),
                    'attendance_rate_today': round(attendance_rate, 1),
                    'avg_weekly_rate': round(weekly_rate, 1),
                    'total_records': total_records,
                    'avg_daily_attendance': round(avg_daily, 1)
                }
                
        except Exception as e:
            logger.error(f"Error getting overview stats: {e}")
            return {}
    
    def get_daily_attendance_trends(self, start_date: date, end_date: date) -> List[Dict]:
        """Get daily attendance trends"""
        try:
            with self.db_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    SELECT 
                        date,
                        COUNT(DISTINCT student_id) as present_count,
                        COUNT(DISTINCT CASE WHEN time_in IS NOT NULL THEN student_id END) as checked_in,
                        COUNT(DISTINCT CASE WHEN time_out IS NOT NULL THEN student_id END) as checked_out
                    FROM attendance
                    WHERE date BETWEEN ? AND ?
                    GROUP BY date
                    ORDER BY date
                """, (start_date, end_date))
                
                results = cursor.fetchall()
                
                # Get total students for percentage calculation
                cursor.execute("SELECT COUNT(*) FROM students WHERE is_active = 1")
                total_students_result = cursor.fetchone()
                total_students = total_students_result[0] if total_students_result else 0
                
                trends = []
                for row in results:
                    present_count = row['present_count'] or 0
                    checked_in = row['checked_in'] or 0
                    checked_out = row['checked_out'] or 0
                    
                    # Fixed percentage calculation
                    attendance_rate = (present_count / total_students * 100) if total_students > 0 else 0
                    
                    # Parse date to get day name
                    try:
                        date_obj = datetime.strptime(row['date'], '%Y-%m-%d')
                        day_name = date_obj.strftime('%A')
                    except:
                        day_name = 'Unknown'
                    
                    trends.append({
                        'date': row['date'],
                        'present_count': present_count,
                        'checked_in': checked_in,
                        'checked_out': checked_out,
                        'attendance_rate': round(attendance_rate, 1),
                        'day_name': day_name,
                        'total_students': total_students
                    })
                
                return trends
                
        except Exception as e:
            logger.error(f"Error getting daily trends: {e}")
            return []
    
    def get_student_performance_analysis(self, start_date: date, end_date: date) -> List[Dict]:
        """Analyze individual student performance with corrected calculations"""
        try:
            with self.db_connection() as conn:
                cursor = conn.cursor()
                
                # Calculate actual working days (excluding weekends if needed)
                total_days = (end_date - start_date).days + 1
                
                # Count actual days with attendance records (more accurate)
                cursor.execute("""
                    SELECT COUNT(DISTINCT date) as working_days
                    FROM attendance
                    WHERE date BETWEEN ? AND ?
                """, (start_date, end_date))
                
                working_days_result = cursor.fetchone()
                working_days = working_days_result['working_days'] if working_days_result and working_days_result['working_days'] else total_days
                
                # If no attendance records exist, use business days calculation
                if working_days == 0:
                    working_days = sum(1 for i in range(total_days) 
                                     if (start_date + timedelta(days=i)).weekday() < 5)
                
                cursor.execute("""
                    SELECT 
                        s.id,
                        s.name,
                        s.roll_number,
                        s.course,
                        COUNT(DISTINCT a.date) as days_attended,
                        COUNT(DISTINCT CASE WHEN a.time_in IS NOT NULL THEN a.date END) as days_checked_in,
                        COUNT(DISTINCT CASE WHEN a.time_out IS NOT NULL THEN a.date END) as days_checked_out,
                        AVG(
                            CASE WHEN a.time_in IS NOT NULL THEN
                                CAST(strftime('%H', a.time_in) AS INTEGER) * 60 + 
                                CAST(strftime('%M', a.time_in) AS INTEGER)
                            END
                        ) as avg_arrival_minutes,
                        COUNT(DISTINCT CASE 
                            WHEN a.time_in IS NOT NULL AND 
                                 CAST(strftime('%H', a.time_in) AS INTEGER) * 60 + 
                                 CAST(strftime('%M', a.time_in) AS INTEGER) > 540 -- 9:00 AM
                            THEN a.date 
                        END) as late_days
                    FROM students s
                    LEFT JOIN attendance a ON s.id = a.student_id 
                        AND a.date BETWEEN ? AND ?
                    WHERE s.is_active = 1
                    GROUP BY s.id, s.name, s.roll_number, s.course
                    ORDER BY days_attended DESC
                """, (start_date, end_date))
                
                results = cursor.fetchall()
                
                performance = []
                for row in results:
                    days_attended = row['days_attended'] or 0
                    days_checked_in = row['days_checked_in'] or 0
                    days_checked_out = row['days_checked_out'] or 0
                    late_days = row['late_days'] or 0
                    
                    # Fixed attendance percentage calculation
                    attendance_percentage = (days_attended / working_days * 100) if working_days > 0 else 0
                    
                    # Convert average arrival minutes to time
                    avg_arrival = "N/A"
                    if row['avg_arrival_minutes'] is not None:
                        total_minutes = int(row['avg_arrival_minutes'])
                        hours = total_minutes // 60
                        minutes = total_minutes % 60
                        avg_arrival = f"{hours:02d}:{minutes:02d}"
                    
                    # Fixed performance category based on corrected percentage
                    if attendance_percentage >= 90:
                        category = "Excellent"
                        status = "🟢"
                    elif attendance_percentage >= 75:
                        category = "Good"
                        status = "🟡"
                    elif attendance_percentage >= 60:
                        category = "Average"
                        status = "🟠"
                    else:
                        category = "Poor"
                        status = "🔴"
                    
                    # Fixed punctuality rate calculation
                    punctuality_rate = ((days_attended - late_days) / max(days_attended, 1) * 100) if days_attended > 0 else 100
                    
                    performance.append({
                        'student_id': row['id'],
                        'name': row['name'],
                        'roll_number': row['roll_number'],
                        'course': row['course'],
                        'days_attended': days_attended,
                        'working_days': working_days,
                        'attendance_percentage': round(attendance_percentage, 1),
                        'category': category,
                        'status': status,
                        'avg_arrival_time': avg_arrival,
                        'late_days': late_days,
                        'punctuality_rate': round(punctuality_rate, 1),
                        'days_checked_in': days_checked_in,
                        'days_checked_out': days_checked_out
                    })
                
                return performance
                
        except Exception as e:
            logger.error(f"Error analyzing student performance: {e}")
            return []
    
    def get_course_wise_analytics(self, start_date: date, end_date: date) -> List[Dict]:
        """Get course-wise attendance analytics with fixed calculations"""
        try:
            with self.db_connection() as conn:
                cursor = conn.cursor()
                
                # Get working days for the period
                cursor.execute("""
                    SELECT COUNT(DISTINCT date) as working_days
                    FROM attendance
                    WHERE date BETWEEN ? AND ?
                """, (start_date, end_date))
                
                working_days_result = cursor.fetchone()
                working_days = working_days_result['working_days'] if working_days_result else (end_date - start_date).days + 1
                
                cursor.execute("""
                    SELECT 
                        s.course,
                        COUNT(DISTINCT s.id) as total_students,
                        COUNT(DISTINCT a.student_id) as students_with_attendance,
                        COUNT(DISTINCT a.date) as active_days,
                        COUNT(DISTINCT CASE WHEN a.time_in IS NOT NULL THEN a.student_id || '_' || a.date END) as total_attendance_instances,
                        AVG(daily_stats.daily_count) as avg_daily_attendance
                    FROM students s
                    LEFT JOIN attendance a ON s.id = a.student_id 
                        AND a.date BETWEEN ? AND ?
                    LEFT JOIN (
                        SELECT 
                            s2.course,
                            a2.date,
                            COUNT(DISTINCT a2.student_id) as daily_count
                        FROM students s2
                        JOIN attendance a2 ON s2.id = a2.student_id
                        WHERE a2.date BETWEEN ? AND ? AND a2.time_in IS NOT NULL
                        GROUP BY s2.course, a2.date
                    ) daily_stats ON s.course = daily_stats.course
                    WHERE s.is_active = 1
                    GROUP BY s.course
                    HAVING total_students > 0
                    ORDER BY total_students DESC
                """, (start_date, end_date, start_date, end_date))
                
                results = cursor.fetchall()
                
                course_analytics = []
                for row in results:
                    total_students = row['total_students'] or 0
                    avg_attendance = row['avg_daily_attendance'] or 0
                    
                    # Fixed attendance rate calculation
                    attendance_rate = (avg_attendance / total_students * 100) if total_students > 0 and avg_attendance > 0 else 0
                    
                    # Performance rating based on corrected rate
                    if attendance_rate >= 85:
                        rating = "Excellent"
                        color = "#10b981"
                    elif attendance_rate >= 70:
                        rating = "Good"
                        color = "#3b82f6"
                    elif attendance_rate >= 55:
                        rating = "Average"
                        color = "#f59e0b"
                    else:
                        rating = "Needs Attention"
                        color = "#ef4444"
                    
                    course_analytics.append({
                        'course': row['course'] or 'Unknown',
                        'total_students': total_students,
                        'avg_daily_attendance': round(avg_attendance, 1),
                        'attendance_rate': round(attendance_rate, 1),
                        'rating': rating,
                        'color': color,
                        'active_days': row['active_days'] or 0,
                        'students_with_attendance': row['students_with_attendance'] or 0
                    })
                
                return course_analytics
                
        except Exception as e:
            logger.error(f"Error getting course analytics: {e}")
            return []
    
    def get_time_pattern_analysis(self, start_date: date, end_date: date) -> Dict:
        """Analyze attendance time patterns"""
        try:
            with self.db_connection() as conn:
                cursor = conn.cursor()
                
                # Hourly check-in patterns
                cursor.execute("""
                    SELECT 
                        strftime('%H', time_in) as hour,
                        COUNT(*) as check_ins
                    FROM attendance
                    WHERE date BETWEEN ? AND ? AND time_in IS NOT NULL
                    GROUP BY strftime('%H', time_in)
                    ORDER BY hour
                """, (start_date, end_date))
                
                hourly_checkins = []
                for row in cursor.fetchall():
                    hour = row['hour']
                    if hour:  # Only add valid hours
                        hourly_checkins.append({
                            'hour': f"{hour}:00",
                            'count': row['check_ins']
                        })
                
                # Day of week patterns
                cursor.execute("""
                    SELECT 
                        CASE strftime('%w', date)
                            WHEN '0' THEN 'Sunday'
                            WHEN '1' THEN 'Monday'
                            WHEN '2' THEN 'Tuesday'
                            WHEN '3' THEN 'Wednesday'
                            WHEN '4' THEN 'Thursday'
                            WHEN '5' THEN 'Friday'
                            WHEN '6' THEN 'Saturday'
                        END as day_name,
                        COUNT(DISTINCT student_id) as attendance_count
                    FROM attendance
                    WHERE date BETWEEN ? AND ? AND time_in IS NOT NULL
                    GROUP BY strftime('%w', date)
                    ORDER BY strftime('%w', date)
                """, (start_date, end_date))
                
                weekly_patterns = []
                for row in cursor.fetchall():
                    if row['day_name']:  # Only add valid day names
                        weekly_patterns.append({
                            'day': row['day_name'],
                            'count': row['attendance_count'] or 0
                        })
                
                # Peak hours analysis
                peak_hour = "N/A"
                if hourly_checkins:
                    peak_hour = max(hourly_checkins, key=lambda x: x['count'])['hour']
                
                return {
                    'hourly_checkins': hourly_checkins,
                    'weekly_patterns': weekly_patterns,
                    'peak_hour': peak_hour,
                    'total_checkins': sum(h['count'] for h in hourly_checkins)
                }
                
        except Exception as e:
            logger.error(f"Error analyzing time patterns: {e}")
            return {}
    
    def get_weekly_summary(self, start_date: date, end_date: date) -> Dict:
        """Get weekly attendance summary"""
        try:
            with self.db_connection() as conn:
                cursor = conn.cursor()
                
                # This week vs last week
                this_week_start = date.today() - timedelta(days=date.today().weekday())
                last_week_start = this_week_start - timedelta(days=7)
                last_week_end = this_week_start - timedelta(days=1)
                
                # This week attendance
                cursor.execute("""
                    SELECT COUNT(DISTINCT student_id) as attendance
                    FROM attendance
                    WHERE date >= ? AND time_in IS NOT NULL
                """, (this_week_start,))
                
                this_week_result = cursor.fetchone()
                this_week = this_week_result['attendance'] if this_week_result else 0
                
                # Last week attendance
                cursor.execute("""
                    SELECT COUNT(DISTINCT student_id) as attendance
                    FROM attendance
                    WHERE date BETWEEN ? AND ? AND time_in IS NOT NULL
                """, (last_week_start, last_week_end))
                
                last_week_result = cursor.fetchone()
                last_week = last_week_result['attendance'] if last_week_result else 0
                
                # Calculate change
                if last_week > 0:
                    change_percent = ((this_week - last_week) / last_week) * 100
                else:
                    change_percent = 100 if this_week > 0 else 0
                
                return {
                    'this_week': this_week,
                    'last_week': last_week,
                    'change_percent': round(change_percent, 1),
                    'trend': 'up' if change_percent > 0 else 'down' if change_percent < 0 else 'stable'
                }
                
        except Exception as e:
            logger.error(f"Error getting weekly summary: {e}")
            return {}
    
    def get_attendance_alerts(self) -> List[Dict]:
        """Generate attendance alerts and warnings"""
        try:
            alerts = []
            
            with self.db_connection() as conn:
                cursor = conn.cursor()
                
                # Get working days in last 30 days
                cursor.execute("""
                    SELECT COUNT(DISTINCT date) as working_days
                    FROM attendance
                    WHERE date >= ?
                """, (date.today() - timedelta(days=30),))
                
                working_days_result = cursor.fetchone()
                working_days = working_days_result['working_days'] if working_days_result else 22  # Default ~22 working days per month
                
                # Students with low attendance (< 60% in last 30 days)
                threshold_days = int(working_days * 0.6)  # 60% of working days
                
                cursor.execute("""
                    SELECT 
                        s.name, s.roll_number, s.course,
                        COUNT(DISTINCT a.date) as days_attended
                    FROM students s
                    LEFT JOIN attendance a ON s.id = a.student_id 
                        AND a.date >= ? AND a.time_in IS NOT NULL
                    WHERE s.is_active = 1
                    GROUP BY s.id, s.name, s.roll_number, s.course
                    HAVING days_attended < ?
                    ORDER BY days_attended ASC
                    LIMIT 10
                """, (date.today() - timedelta(days=30), threshold_days))
                
                low_attendance = cursor.fetchall()
                for student in low_attendance:
                    days_attended = student['days_attended'] or 0
                    attendance_rate = (days_attended / working_days * 100) if working_days > 0 else 0
                    
                    alerts.append({
                        'type': 'low_attendance',
                        'severity': 'high' if attendance_rate < 40 else 'medium',
                        'title': f'Low Attendance Alert',
                        'message': f"{student['name']} ({student['roll_number']}) has {attendance_rate:.1f}% attendance ({days_attended}/{working_days} days)",
                        'student': student['name'],
                        'action': 'Contact student/parent',
                        'attendance_rate': round(attendance_rate, 1)
                    })
                
                # Students absent for consecutive days
                cursor.execute("""
                    SELECT s.name, s.roll_number, s.course, MAX(a.date) as last_attendance
                    FROM students s
                    LEFT JOIN attendance a ON s.id = a.student_id AND a.time_in IS NOT NULL
                    WHERE s.is_active = 1
                    GROUP BY s.id
                    HAVING last_attendance < ? OR last_attendance IS NULL
                """, (date.today() - timedelta(days=5),))
                
                absent_students = cursor.fetchall()
                for student in absent_students:
                    last_date = student['last_attendance']
                    if last_date:
                        try:
                            last_attendance_date = datetime.strptime(last_date, '%Y-%m-%d').date()
                            days_absent = (date.today() - last_attendance_date).days
                        except:
                            days_absent = 30  # Default if date parsing fails
                    else:
                        days_absent = 30  # No attendance record
                    
                    alerts.append({
                        'type': 'consecutive_absence',
                        'severity': 'high' if days_absent >= 7 else 'medium',
                        'title': f'Consecutive Absence Alert',
                        'message': f"{student['name']} absent for {days_absent} days",
                        'student': student['name'],
                        'action': 'Immediate follow-up required',
                        'days_absent': days_absent
                    })
                
                return alerts[:15]  # Limit to 15 alerts
                
        except Exception as e:
            logger.error(f"Error generating alerts: {e}")
            return []
    
    def get_trend_predictions(self, start_date: date, end_date: date) -> Dict:
        """Simple trend analysis and predictions"""
        try:
            with self.db_connection() as conn:
                cursor = conn.cursor()
                
                # Get daily attendance for trend analysis
                cursor.execute("""
                    SELECT date, COUNT(DISTINCT student_id) as attendance
                    FROM attendance
                    WHERE date BETWEEN ? AND ? AND time_in IS NOT NULL
                    GROUP BY date
                    ORDER BY date
                """, (start_date, end_date))
                
                daily_data = cursor.fetchall()
                
                if len(daily_data) < 7:
                    return {'trend': 'insufficient_data', 'message': 'Need more data for predictions'}
                
                # Simple moving average trend
                recent_values = [d['attendance'] for d in daily_data[-7:]]
                previous_values = [d['attendance'] for d in daily_data[-14:-7]] if len(daily_data) >= 14 else recent_values
                
                recent_avg = sum(recent_values) / len(recent_values)
                previous_avg = sum(previous_values) / len(previous_values)
                
                trend_direction = 'increasing' if recent_avg > previous_avg else 'decreasing' if recent_avg < previous_avg else 'stable'
                
                return {
                    'trend': trend_direction,
                    'recent_average': round(recent_avg, 1),
                    'previous_average': round(previous_avg, 1),
                    'change': round(recent_avg - previous_avg, 1),
                    'prediction': f"Expected attendance: {round(recent_avg, 0)}±2 students"
                }
                
        except Exception as e:
            logger.error(f"Error generating predictions: {e}")
            return {}
    
    def generate_ai_insights(self, analytics: Dict) -> List[str]:
        """Generate human-readable AI narrative insights from analytics data.

        Uses template-based NLP — no LLM or external API needed.
        Returns a list of insight strings, ordered by importance.
        """
        insights: List[str] = []
        try:
            overview = analytics.get("overview", {})
            weekly = analytics.get("weekly_summary", {})
            predictions = analytics.get("predictions", {})
            student_perf = analytics.get("student_performance", [])
            course_data = analytics.get("course_analytics", [])
            time_patterns = analytics.get("time_patterns", {})
            alerts = analytics.get("alerts", [])

            total_students = overview.get("total_students", 0)
            present_today = overview.get("present_today", 0)
            rate_today = overview.get("attendance_rate_today", 0)
            avg_weekly = overview.get("avg_weekly_rate", 0)

            # ── Today's pulse ─────────────────────────────────────────
            if total_students > 0:
                absent_today = total_students - present_today
                if rate_today >= 90:
                    insights.append(
                        f"📈 Excellent turnout today — {present_today} of {total_students} students "
                        f"present ({rate_today:.0f}%). Keep it up!"
                    )
                elif rate_today >= 70:
                    insights.append(
                        f"✅ Good attendance today: {present_today}/{total_students} students present "
                        f"({rate_today:.0f}%). {absent_today} absent."
                    )
                elif rate_today > 0:
                    insights.append(
                        f"⚠️ Below-average attendance today — only {present_today} of {total_students} "
                        f"students present ({rate_today:.0f}%). {absent_today} students are absent."
                    )
                else:
                    insights.append(
                        f"📋 No attendance has been marked yet today. "
                        f"{total_students} students enrolled."
                    )

            # ── Week-over-week trend ───────────────────────────────────
            change = weekly.get("change_percent", 0)
            trend = weekly.get("trend", "stable")
            if trend == "up" and abs(change) >= 5:
                insights.append(
                    f"📊 Attendance improved by {abs(change):.0f}% compared to last week — "
                    "a positive trend worth celebrating."
                )
            elif trend == "down" and abs(change) >= 5:
                insights.append(
                    f"📉 Attendance dropped {abs(change):.0f}% versus last week. "
                    "Consider sending reminders or investigating the cause."
                )

            # ── At-risk students ──────────────────────────────────────
            at_risk = [s for s in student_perf if s.get("attendance_percentage", 100) < 60]
            critical = [s for s in at_risk if s.get("attendance_percentage", 100) < 40]
            if critical:
                names = ", ".join(s["name"] for s in critical[:3])
                extras = f" and {len(critical) - 3} more" if len(critical) > 3 else ""
                insights.append(
                    f"🚨 {len(critical)} student(s) are in critical attendance status (<40%): "
                    f"{names}{extras}. Immediate intervention recommended."
                )
            elif at_risk:
                insights.append(
                    f"⚠️ {len(at_risk)} student(s) are at risk of failing attendance requirements "
                    f"(<60% attendance). Early counselling advised."
                )

            # ── Consecutive absences ──────────────────────────────────
            long_absences = [
                a for a in alerts
                if a.get("type") == "consecutive_absence" and a.get("days_absent", 0) >= 5
            ]
            if long_absences:
                eg = long_absences[0]
                insights.append(
                    f"🔴 {eg['student']} has been absent for {eg.get('days_absent', '?')} consecutive days. "
                    "Follow-up is strongly recommended."
                )

            # ── Best / worst performers ───────────────────────────────
            perfect = [s for s in student_perf if s.get("attendance_percentage", 0) >= 95]
            if perfect:
                names = ", ".join(s["name"] for s in perfect[:3])
                extras = f" (+{len(perfect) - 3} more)" if len(perfect) > 3 else ""
                insights.append(
                    f"🌟 {len(perfect)} student(s) have near-perfect attendance (≥95%): "
                    f"{names}{extras}."
                )

            # ── Day-of-week pattern ───────────────────────────────────
            weekly_patterns = time_patterns.get("weekly_patterns", [])
            if weekly_patterns:
                sorted_days = sorted(weekly_patterns, key=lambda d: d.get("avg_attendance", 0))
                worst_day = sorted_days[0] if sorted_days else None
                best_day = sorted_days[-1] if sorted_days else None
                if worst_day and best_day and worst_day["day"] != best_day["day"]:
                    worst_avg = worst_day.get("avg_attendance", 0)
                    best_avg = best_day.get("avg_attendance", 0)
                    if best_avg > 0:
                        diff_pct = round((best_avg - worst_avg) / best_avg * 100)
                        if diff_pct >= 10:
                            insights.append(
                                f"📅 {worst_day['day']}s have the lowest average attendance "
                                f"({diff_pct}% below {best_day['day']}s). "
                                "Consider scheduling important sessions on peak days."
                            )

            # ── Course comparison ─────────────────────────────────────
            if len(course_data) >= 2:
                sorted_courses = sorted(course_data, key=lambda c: c.get("attendance_rate", 0))
                best_c = sorted_courses[-1]
                worst_c = sorted_courses[0]
                if best_c["course"] != worst_c["course"]:
                    insights.append(
                        f"🏫 {best_c['course']} leads with {best_c['attendance_rate']:.0f}% attendance. "
                        f"{worst_c['course']} lags at {worst_c['attendance_rate']:.0f}% — "
                        "may need targeted engagement."
                    )

            # ── Prediction ────────────────────────────────────────────
            pred_trend = predictions.get("trend", "")
            pred_msg = predictions.get("prediction", "")
            if pred_trend == "increasing" and pred_msg:
                insights.append(f"🔮 Trend forecast: {pred_msg}. Attendance is on an upward trajectory.")
            elif pred_trend == "decreasing" and pred_msg:
                insights.append(f"🔮 Trend forecast: {pred_msg}. Attendance is declining — proactive measures advised.")

            # ── Peak hour ─────────────────────────────────────────────
            peak_hour = time_patterns.get("peak_hour")
            if peak_hour not in (None, "N/A"):
                try:
                    h = int(str(peak_hour).split(":")[0])
                    ampm = "AM" if h < 12 else "PM"
                    h12 = h if 1 <= h <= 12 else (h - 12 if h > 12 else 12)
                    insights.append(
                        f"⏰ Peak check-in time is around {h12}:00 {ampm}. "
                        "Ensure attendance systems are ready then."
                    )
                except Exception:
                    pass

            if not insights:
                insights.append(
                    "💡 Not enough data for insights yet. Register students and start marking "
                    "attendance to see AI-generated reports here."
                )

        except Exception as e:
            logger.error(f"Error generating AI insights: {e}")
            insights.append("💡 AI insights temporarily unavailable. Refresh to retry.")

        return insights

    def export_analytics_report(self, start_date: date, end_date: date) -> Dict:
        """Generate comprehensive analytics report for export"""
        try:
            analytics = self.get_comprehensive_analytics((end_date - start_date).days)
            
            # Create export-friendly format
            report = {
                'report_period': f"{start_date} to {end_date}",
                'generated_on': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'summary': analytics.get('overview', {}),
                'student_performance': analytics.get('student_performance', []),
                'course_analytics': analytics.get('course_analytics', []),
                'daily_trends': analytics.get('daily_trends', []),
                'alerts': analytics.get('alerts', [])
            }
            
            return report
            
        except Exception as e:
            logger.error(f"Error exporting analytics: {e}")
            return {}
