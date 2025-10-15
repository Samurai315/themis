import streamlit as st
from lib.database import get_database
from lib.export_utils import ScheduleExporter
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import json
import re

st.set_page_config(page_title="View Timetable", page_icon="📅", layout="wide")

# Check authentication
if not st.session_state.get("authenticated"):
    st.warning("⚠️ Please login first")
    st.stop()

# Update activity
if 'last_activity' in st.session_state:
    st.session_state.last_activity = datetime.now()

db = get_database()
user = st.session_state.user

# Get college profile
college_profile = db.get_college_profile()

if not college_profile:
    st.error("❌ Please complete setup first")
    st.stop()

# Header
st.title("📅 Timetable Viewer")

# Get user's schedules
user_schedules = db.get_user_schedules(user['id'])

if not user_schedules:
    st.info("📭 No timetables found. Create one in the Optimizer page!")
    if st.button("➕ Go to Optimizer"):
        st.switch_page("pages/3_Optimizer.py")
    st.stop()

# Schedule selector
col1, col2, col3 = st.columns([3, 1, 1])

with col1:
    # Check if coming from another page with schedule_id
    default_index = 0
    if 'view_schedule_id' in st.session_state:
        view_id = st.session_state.view_schedule_id
        schedule_ids = [s['id'] for s in user_schedules]
        if view_id in schedule_ids:
            default_index = schedule_ids.index(view_id)
    
    schedule_options = {f"{s['title']} ({s['academic_year']})": s['id'] for s in user_schedules}
    selected_title = st.selectbox(
        "Select Timetable",
        list(schedule_options.keys()),
        index=default_index
    )
    schedule_id = schedule_options[selected_title]

with col2:
    if st.button("🔄 Refresh", use_container_width=True):
        st.rerun()

with col3:
    if st.button("✏️ Edit", use_container_width=True):
        st.session_state.edit_schedule_id = schedule_id
        st.switch_page("pages/3_Optimizer.py")

# Get schedule details
schedule = db.get_schedule(schedule_id)
sessions = db.get_timetable_sessions(schedule_id=schedule_id)

# Extract metadata
num_weeks = 16
start_date = None
end_date = None

if schedule and schedule.get('description'):
    try:
        meta_match = re.search(r'\[META\](.*?)\[/META\]', schedule.get('description', '') or '')
        if meta_match:
            metadata = json.loads(meta_match.group(1))
            num_weeks = metadata.get('num_weeks', 16)
            start_date = metadata.get('start_date')
            end_date = metadata.get('end_date')
    except:
        pass

# Display semester info
st.info(f"""
📅 **Weekly Recurring Schedule**

This timetable repeats every week for **{num_weeks} weeks**.

- **Semester Start:** {start_date or 'Not specified'}
- **Semester End:** {end_date or 'Not specified'}
- **Total Teaching Weeks:** {num_weeks}
""")

# Schedule info
st.divider()

col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric("📚 Sessions per Week", len(sessions))
    st.caption(f"× {num_weeks} weeks")

with col2:
    unique_batches = len(set(s['batch_id'] for s in sessions))
    st.metric("🎓 Batches", unique_batches)

with col3:
    unique_faculty = len(set(s['faculty_id'] for s in sessions))
    st.metric("👨‍🏫 Faculty", unique_faculty)

with col4:
    status_colors = {"draft": "🟡", "finalized": "🟢", "optimizing": "🟠"}
    schedule_status = schedule.get('status', 'unknown') if schedule else 'unknown'
    st.metric("Status", f"{status_colors.get(schedule_status, '⚪')} {schedule_status}")

# Update metrics for total hours
st.divider()

col1, col2, col3, col4 = st.columns(4)

with col1:
    total_hours_week = sum(s.get('duration', 1) for s in sessions)
    st.metric("⏰ Hours/Week", total_hours_week)

with col2:
    total_hours_semester = total_hours_week * num_weeks
    st.metric("📅 Hours/Semester", total_hours_semester)

with col3:
    unique_subjects = len(set(s['subject_id'] for s in sessions))
    st.metric("📘 Subjects", unique_subjects)

with col4:
    unique_rooms = len(set(s['room_id'] for s in sessions))
    st.metric("🏛️ Rooms", unique_rooms)

st.divider()

# Check for conflicts
st.markdown("### ⚠️ Conflict Analysis")

conflicts = []

# Check faculty conflicts
for session in sessions:
    faculty_conflicts = [
        s for s in sessions 
        if s['faculty_id'] == session['faculty_id'] 
        and s['day_of_week'] == session['day_of_week']
        and s['time_slot'] == session['time_slot']
        and s['id'] != session['id']
    ]
    
    if faculty_conflicts:
        conflicts.append({
            'type': 'Faculty Conflict',
            'severity': 'High',
            'message': f"{session['faculty_name']} has multiple classes on {session['day_of_week']} at {session['time_slot']}",
            'sessions': [session] + faculty_conflicts
        })

# Check room conflicts
for session in sessions:
    room_conflicts = [
        s for s in sessions 
        if s['room_id'] == session['room_id']
        and s['day_of_week'] == session['day_of_week']
        and s['time_slot'] == session['time_slot']
        and s['id'] != session['id']
    ]
    
    if room_conflicts:
        conflicts.append({
            'type': 'Room Conflict',
            'severity': 'High',
            'message': f"Room {session['room_name']} has multiple classes on {session['day_of_week']} at {session['time_slot']}",
            'sessions': [session] + room_conflicts
        })

# Check batch conflicts
for session in sessions:
    batch_conflicts = [
        s for s in sessions 
        if s['batch_id'] == session['batch_id']
        and s['day_of_week'] == session['day_of_week']
        and s['time_slot'] == session['time_slot']
        and s['id'] != session['id']
    ]
    
    if batch_conflicts:
        conflicts.append({
            'type': 'Batch Conflict',
            'severity': 'High',
            'message': f"{session['batch_name']} has multiple classes on {session['day_of_week']} at {session['time_slot']}",
            'sessions': [session] + batch_conflicts
        })

# Remove duplicates
unique_conflicts = []
seen = set()
for conflict in conflicts:
    key = conflict['message']
    if key not in seen:
        seen.add(key)
        unique_conflicts.append(conflict)

if unique_conflicts:
    st.error(f"❌ Found {len(unique_conflicts)} conflict(s)")
    
    with st.expander("View Conflicts", expanded=True):
        for idx, conflict in enumerate(unique_conflicts, 1):
            st.markdown(f"**{idx}. {conflict['type']}:** {conflict['message']}")
else:
    st.success("✅ No conflicts detected!")

st.divider()

# Main tabs
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📋 Master Timetable",
    "🎓 Batch-wise View",
    "👨‍🏫 Faculty-wise View",
    "🏛️ Room-wise View",
    "💾 Export & Actions"
])

# ==================== TAB 1: MASTER TIMETABLE ====================
with tab1:
    st.markdown("### 📋 Complete Timetable")
    
    if not sessions:
        st.info("No sessions scheduled yet")
    else:
        # Convert to DataFrame
        df = pd.DataFrame(sessions)
        
        # Display as table
        display_cols = ['day_of_week', 'time_slot', 'subject_name', 'batch_name', 
                       'faculty_name', 'room_name', 'session_type']
        
        if all(col in df.columns for col in display_cols):
            display_df = df[display_cols].copy()
            display_df.columns = ['Day', 'Time', 'Subject', 'Batch', 'Faculty', 'Room', 'Type']
            
            st.dataframe(display_df, use_container_width=True, hide_index=True)
            
            # Download CSV
            csv = display_df.to_csv(index=False)
            schedule_title = schedule.get('title', 'timetable') if schedule else 'timetable'
            st.download_button(
                "📥 Download as CSV",
                data=csv,
                file_name=f"{schedule_title}_master.csv",
                mime="text/csv"
            )
        
        # Grid view
        st.markdown("### 📊 Grid View")
        
        # Create pivot table
        grid_data = []
        for session in sessions:
            grid_data.append({
                'Day': session['day_of_week'],
                'Time': session['time_slot'],
                'Cell': f"{session['subject_code']}\n{session['batch_name']}\n{session['room_name']}"
            })
        
        if grid_data:
            grid_df = pd.DataFrame(grid_data)
            
            # Pivot
            pivot = grid_df.pivot_table(
                index='Time',
                columns='Day',
                values='Cell',
                aggfunc=lambda x: '\n---\n'.join(x)
            )
            
            # Reorder days
            day_order = college_profile.get('working_days', ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"])
            pivot = pivot.reindex(columns=[d for d in day_order if d in pivot.columns])
            
            st.dataframe(pivot, use_container_width=True)

# ==================== TAB 2: BATCH-WISE VIEW ====================
with tab2:
    st.markdown("### 🎓 Individual Batch Timetables")
    
    # Get unique batches
    unique_batches = list(set((s['batch_id'], s['batch_name']) for s in sessions))
    unique_batches.sort(key=lambda x: x[1])
    
    if not unique_batches:
        st.info("No batches scheduled")
    else:
        # Batch selector
        selected_batch_name = st.selectbox(
            "Select Batch",
            [b[1] for b in unique_batches]
        )
        
        selected_batch_id = next(b[0] for b in unique_batches if b[1] == selected_batch_name)
        
        # Filter sessions for this batch
        batch_sessions = [s for s in sessions if s['batch_id'] == selected_batch_id]
        
        st.markdown(f"#### 📅 Timetable for {selected_batch_name}")
        st.metric("Total Classes", len(batch_sessions))
        
        # Check for gaps
        batch_df = pd.DataFrame(batch_sessions)
        if not batch_df.empty:
            # Group by day
            day_order = college_profile.get('working_days', ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"])
            for day in day_order:
                day_sessions = [s for s in batch_sessions if s['day_of_week'] == day]
                
                if day_sessions:
                    with st.expander(f"📆 {day} ({len(day_sessions)} classes)", expanded=True):
                        # Sort by time
                        day_sessions.sort(key=lambda x: x['time_slot'])
                        
                        for session in day_sessions:
                            col1, col2, col3, col4 = st.columns([2, 2, 2, 1])
                            
                            with col1:
                                st.write(f"**{session['time_slot']}**")
                            
                            with col2:
                                st.write(f"📖 {session['subject_name']}")
                            
                            with col3:
                                st.write(f"👨‍🏫 {session['faculty_name']}")
                            
                            with col4:
                                st.write(f"🏛️ {session['room_name']}")
        
        st.divider()
        
        # Batch timetable grid
        st.markdown("#### 📊 Weekly Grid")
        
        # Create grid
        grid_data = []
        for session in batch_sessions:
            grid_data.append({
                'Day': session['day_of_week'],
                'Time': session['time_slot'],
                'Cell': f"{session['subject_name']}\n{session['faculty_name']}\n{session['room_name']}"
            })
        
        if grid_data:
            grid_df = pd.DataFrame(grid_data)
            pivot = grid_df.pivot_table(
                index='Time',
                columns='Day',
                values='Cell',
                aggfunc=lambda x: '\n'.join(x)
            )
            
            # Reorder
            day_order = college_profile.get('working_days', ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"])
            pivot = pivot.reindex(columns=[d for d in day_order if d in pivot.columns])
            
            st.dataframe(pivot, use_container_width=True, height=400)
            
            # Download batch timetable
            csv = pd.DataFrame(batch_sessions)[['day_of_week', 'time_slot', 'subject_name', 
                                                'faculty_name', 'room_name', 'session_type']].to_csv(index=False)
            st.download_button(
                f"📥 Download {selected_batch_name} Timetable",
                data=csv,
                file_name=f"{selected_batch_name}_timetable.csv",
                mime="text/csv"
            )

# ==================== TAB 3: FACULTY-WISE VIEW ====================
with tab3:
    st.markdown("### 👨‍🏫 Faculty Timetables")
    
    # Get unique faculty
    unique_faculty = list(set((s['faculty_id'], s['faculty_name']) for s in sessions))
    unique_faculty.sort(key=lambda x: x[1])
    
    if not unique_faculty:
        st.info("No faculty scheduled")
    else:
        selected_faculty_name = st.selectbox(
            "Select Faculty",
            [f[1] for f in unique_faculty]
        )
        
        selected_faculty_id = next(f[0] for f in unique_faculty if f[1] == selected_faculty_name)
        
        # Get faculty details
        faculty_info = db.get_all_faculty()
        faculty = next((f for f in faculty_info if f['id'] == selected_faculty_id), None)
        
        # Filter sessions
        faculty_sessions = [s for s in sessions if s['faculty_id'] == selected_faculty_id]
        
        st.markdown(f"#### 📅 Teaching Schedule for {selected_faculty_name}")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("Total Classes", len(faculty_sessions))
        
        with col2:
            total_hours = sum(s.get('duration', 1) for s in faculty_sessions)
            if faculty:
                st.metric("Hours/Week", f"{total_hours}/{faculty.get('max_hours_per_week', 18)}")
            else:
                st.metric("Hours/Week", f"{total_hours}/?")
        
        with col3:
            unique_subjects = len(set(s['subject_id'] for s in faculty_sessions))
            st.metric("Subjects Teaching", unique_subjects)
        
        # Workload progress
        if faculty:
            max_hours = faculty.get('max_hours_per_week', 18)
            workload_pct = (total_hours / max_hours) if max_hours > 0 else 0
            st.progress(min(workload_pct, 1.0))
            
            if workload_pct > 1.0:
                st.error(f"⚠️ Overloaded! {total_hours} hours exceeds max {max_hours} hours")
            elif workload_pct > 0.9:
                st.warning(f"⚠️ Near capacity: {total_hours}/{max_hours} hours")
            else:
                st.success(f"✅ Within limits: {total_hours}/{max_hours} hours")
        
        st.divider()
        
        # Day-wise schedule
        day_order = college_profile.get('working_days', ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"])
        for day in day_order:
            day_sessions = [s for s in faculty_sessions if s['day_of_week'] == day]
            
            if day_sessions:
                with st.expander(f"📆 {day} ({len(day_sessions)} classes)", expanded=True):
                    day_sessions.sort(key=lambda x: x['time_slot'])
                    
                    for session in day_sessions:
                        col1, col2, col3, col4 = st.columns([2, 2, 2, 1])
                        
                        with col1:
                            st.write(f"**{session['time_slot']}**")
                        
                        with col2:
                            st.write(f"📖 {session['subject_name']}")
                        
                        with col3:
                            st.write(f"🎓 {session['batch_name']}")
                        
                        with col4:
                            st.write(f"🏛️ {session['room_name']}")

# ==================== TAB 4: ROOM-WISE VIEW ====================
with tab4:
    st.markdown("### 🏛️ Room Utilization")
    
    # Get unique rooms
    unique_rooms = list(set((s['room_id'], s['room_name']) for s in sessions))
    unique_rooms.sort(key=lambda x: x[1])
    
    if not unique_rooms:
        st.info("No rooms allocated")
    else:
        # Room utilization stats
        st.markdown("#### 📊 Overall Utilization")
        
        room_stats = []
        for room_id, room_name in unique_rooms:
            room_sessions = [s for s in sessions if s['room_id'] == room_id]
            room_stats.append({
                'Room': room_name,
                'Sessions': len(room_sessions),
                'Hours': sum(s.get('duration', 1) for s in room_sessions)
            })
        
        stats_df = pd.DataFrame(room_stats)
        
        fig = px.bar(
            stats_df,
            x='Room',
            y='Sessions',
            title='Room Usage (Number of Sessions)',
            color='Sessions',
            color_continuous_scale='Blues'
        )
        st.plotly_chart(fig, use_container_width=True)
        
        st.divider()
        
        # Individual room view
        selected_room_name = st.selectbox(
            "Select Room",
            [r[1] for r in unique_rooms]
        )
        
        selected_room_id = next(r[0] for r in unique_rooms if r[1] == selected_room_name)
        room_sessions = [s for s in sessions if s['room_id'] == selected_room_id]
        
        st.markdown(f"#### 📅 Schedule for {selected_room_name}")
        st.metric("Total Sessions", len(room_sessions))
        
        # Grid view
        grid_data = []
        for session in room_sessions:
            grid_data.append({
                'Day': session['day_of_week'],
                'Time': session['time_slot'],
                'Cell': f"{session['subject_code']}\n{session['batch_name']}\n{session['faculty_name']}"
            })
        
        if grid_data:
            grid_df = pd.DataFrame(grid_data)
            pivot = grid_df.pivot_table(
                index='Time',
                columns='Day',
                values='Cell',
                aggfunc=lambda x: '\n'.join(x)
            )
            
            day_order = college_profile.get('working_days', ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"])
            pivot = pivot.reindex(columns=[d for d in day_order if d in pivot.columns])
            
            st.dataframe(pivot, use_container_width=True)

# ==================== TAB 5: EXPORT & ACTIONS ====================
with tab5:
    st.markdown("### 💾 Export Timetable")
    
    col1, col2, col3 = st.columns(3)
    
    metadata = {
        'title': schedule.get('title', 'Timetable') if schedule else 'Timetable',
        'academic_year': schedule.get('academic_year', '') if schedule else '',
        'semester': schedule.get('semester', '') if schedule else '',
        'status': schedule.get('status', '') if schedule else '',
        'total_sessions': len(sessions),
        'num_weeks': num_weeks,
        'start_date': start_date,
        'end_date': end_date
    }
    
    with col1:
        st.markdown("#### 📄 PDF Export")
        if st.button("Generate PDF", use_container_width=True):
            with st.spinner("Generating PDF..."):
                # Prepare data for PDF
                pdf_data = []
                for session in sessions:
                    pdf_data.append({
                        'day': session['day_of_week'],
                        'time': session['time_slot'],
                        'subject': session['subject_name'],
                        'batch': session['batch_name'],
                        'faculty': session['faculty_name'],
                        'room': session['room_name']
                    })
                
                pdf_buffer = ScheduleExporter.export_to_pdf(pdf_data, metadata, include_stats=True)
                
                st.download_button(
                    "📥 Download PDF",
                    data=pdf_buffer,
                    file_name=f"{metadata['title']}.pdf",
                    mime="application/pdf",
                    use_container_width=True
                )
    
    with col2:
        st.markdown("#### 📊 Excel Export")
        if st.button("Generate Excel", use_container_width=True):
            with st.spinner("Generating Excel..."):
                excel_buffer = ScheduleExporter.export_to_excel(sessions, metadata)
                
                st.download_button(
                    "📥 Download Excel",
                    data=excel_buffer,
                    file_name=f"{metadata['title']}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True
                )
    
    with col3:
        st.markdown("#### 📋 JSON Export")
        json_data = ScheduleExporter.export_to_json(sessions, metadata)
        
        st.download_button(
            "📥 Download JSON",
            data=json_data,
            file_name=f"{metadata['title']}.json",
            mime="application/json",
            use_container_width=True
        )
    
    st.divider()
    
    # Actions
    st.markdown("### ⚙️ Actions")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("✏️ Edit Timetable", use_container_width=True, type="primary"):
            st.session_state.edit_schedule_id = schedule_id
            st.switch_page("pages/3_Optimizer.py")
    
    with col2:
        if st.button("📋 Duplicate", use_container_width=True):
            # Extract metadata from existing schedule
            num_weeks_dup = 16
            start_date_dup = None
            end_date_dup = None
            
            if schedule and schedule.get('description'):
                try:
                    meta_match = re.search(r'\[META\](.*?)\[/META\]', schedule.get('description', '') or '')
                    if meta_match:
                        metadata = json.loads(meta_match.group(1))
                        num_weeks_dup = metadata.get('num_weeks', 16)
                        start_date_dup = metadata.get('start_date')
                        end_date_dup = metadata.get('end_date')
                except:
                    pass
            
            new_id = db.create_schedule(
                owner_id=user['id'],
                title=f"{schedule.get('title', 'Timetable') if schedule else 'Timetable'} (Copy)",
                description=schedule.get('description', '') if schedule else '',
                semester=schedule.get('semester', None) if schedule else None,
                academic_year=schedule.get('academic_year', None) if schedule else None
            )
            
            # Copy sessions
            for session in sessions:
                db.create_timetable_session({
                    'schedule_id': new_id,
                    'subject_id': session['subject_id'],
                    'batch_id': session['batch_id'],
                    'faculty_id': session['faculty_id'],
                    'room_id': session['room_id'],
                    'day_of_week': session['day_of_week'],
                    'time_slot': session['time_slot'],
                    'duration': session.get('duration', 1),
                    'session_type': session['session_type']
                })
            
            st.success("✅ Timetable duplicated!")
            st.rerun()
    
    with col3:
        if schedule and schedule.get('owner_id') == user['id']:
            if st.button("🗑️ Delete", use_container_width=True, type="secondary"):
                if st.checkbox("Confirm deletion"):
                    db.delete_schedule(schedule_id)
                    st.success("Timetable deleted!")
                    if 'view_schedule_id' in st.session_state:
                        del st.session_state.view_schedule_id
                    st.rerun()

# Footer
st.divider()
if schedule:
    st.caption(f"Timetable: {schedule.get('title', 'Unknown')} | Created: {schedule.get('created_at', '')[:10]} | Updated: {schedule.get('updated_at', '')[:10]}")
else:
    st.caption("Timetable information not available")