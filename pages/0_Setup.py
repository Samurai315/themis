import streamlit as st
from lib.database import get_database
from datetime import datetime
import json

st.set_page_config(page_title="Setup Wizard", page_icon="⚙️", layout="wide")

# Check authentication
if not st.session_state.get("authenticated"):
    st.warning("⚠️ Please login first")
    st.stop()

# Update activity
if 'last_activity' in st.session_state:
    st.session_state.last_activity = datetime.now()

db = get_database()
user = st.session_state.user

# Header
st.title("⚙️ College Setup Wizard")
st.markdown("Configure your college infrastructure, faculty, and courses before creating timetables")

st.divider()

# Setup tabs
tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs([
    "🏫 College Profile",
    "🏢 Departments",
    "🏛️ Infrastructure",
    "👨‍🏫 Faculty",
    "📚 Programs & Batches",
    "📖 Subjects",
    "📋 Subject Allocation"
])

# ==================== TAB 1: COLLEGE PROFILE ====================
with tab1:
    st.markdown("### 🏫 College Basic Information")
    
    # Get existing profile
    college_profile = db.get_college_profile()
    
    with st.form("college_profile_form"):
        col1, col2 = st.columns(2)
        
        with col1:
            college_name = st.text_input(
                "College Name *",
                value=college_profile['college_name'] if college_profile else "",
                placeholder="e.g., ABC Institute of Technology"
            )
            
            academic_year = st.text_input(
                "Academic Year *",
                value=college_profile['academic_year'] if college_profile else "2025-26",
                placeholder="e.g., 2025-26"
            )
            
            semester = st.selectbox(
                "Current Semester",
                ["Odd Semester (1, 3, 5, 7)", "Even Semester (2, 4, 6, 8)"],
                index=0 if not college_profile else 
                      (0 if college_profile['semester'].startswith('Odd') else 1)
            )
        
        with col2:
            slot_duration = st.number_input(
                "Class Duration (minutes)",
                min_value=30,
                max_value=180,
                value=college_profile['slot_duration'] if college_profile else 60,
                step=15,
                help="Standard duration of one period"
            )
            
            max_periods = st.number_input(
                "Max Periods per Day",
                min_value=4,
                max_value=12,
                value=college_profile['max_periods_per_day'] if college_profile else 8
            )
        
        st.markdown("#### 📅 Working Days")
        all_days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        default_working = college_profile['working_days'] if college_profile else ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]
        
        working_days = st.multiselect(
            "Select Working Days",
            all_days,
            default=default_working
        )
        
        st.markdown("#### ⏰ Time Slots")
        st.caption("Define the start times for each period")
        
        col1, col2 = st.columns(2)
        
        with col1:
            start_time = st.time_input("First Period Starts", value=None)
        
        with col2:
            num_slots = st.number_input("Number of Periods", min_value=4, max_value=12, value=8)
        
        # Generate time slots automatically
        if start_time:
            from datetime import time, timedelta
            time_slots = []
            current_time = datetime.combine(datetime.today(), start_time)
            
            for i in range(num_slots):
                time_slots.append(current_time.strftime("%H:%M"))
                current_time += timedelta(minutes=slot_duration)
            
            st.info(f"Generated time slots: {', '.join(time_slots)}")
        else:
            default_slots = college_profile['time_slots'] if college_profile else [
                "09:00", "10:00", "11:00", "12:00", "14:00", "15:00", "16:00", "17:00"
            ]
            time_slots_str = st.text_input(
                "Or enter manually (comma-separated)",
                value=", ".join(default_slots),
                placeholder="09:00, 10:00, 11:00, 12:00, 14:00, 15:00"
            )
            time_slots = [t.strip() for t in time_slots_str.split(",")]
        
        submit = st.form_submit_button("💾 Save College Profile", type="primary", use_container_width=True)
        
        if submit:
            if not college_name or not academic_year or not working_days or not time_slots:
                st.error("❌ Please fill all required fields")
            else:
                profile_data = {
                    'college_name': college_name,
                    'academic_year': academic_year,
                    'semester': semester,
                    'working_days': working_days,
                    'time_slots': time_slots,
                    'slot_duration': slot_duration,
                    'max_periods_per_day': max_periods
                }
                
                db.create_or_update_college_profile(profile_data, user['id'])
                st.success("✅ College profile saved successfully!")
                st.balloons()
                st.rerun()
    
    # Display current profile
    if college_profile:
        st.divider()
        st.markdown("### 📊 Current Configuration")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("Working Days", len(college_profile['working_days']))
            st.caption(", ".join(college_profile['working_days']))
        
        with col2:
            st.metric("Periods per Day", college_profile['max_periods_per_day'])
            st.caption(f"{college_profile['slot_duration']} minutes each")
        
        with col3:
            st.metric("Time Slots", len(college_profile['time_slots']))
            st.caption(f"{college_profile['time_slots'][0]} - {college_profile['time_slots'][-1]}")

# ==================== TAB 2: DEPARTMENTS ====================
with tab2:
    st.markdown("### 🏢 Department Management")
    
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.markdown("#### ➕ Add New Department")
        
        with st.form("add_department_form"):
            dept_code = st.text_input("Department Code *", placeholder="e.g., CSE")
            dept_name = st.text_input("Department Name *", placeholder="e.g., Computer Science & Engineering")
            hod_name = st.text_input("HOD Name", placeholder="e.g., Dr. John Doe")
            description = st.text_area("Description", placeholder="Brief description of the department")
            
            submit = st.form_submit_button("Add Department", type="primary")
            
            if submit:
                if not dept_code or not dept_name:
                    st.error("❌ Code and Name are required")
                else:
                    try:
                        db.create_department(dept_code, dept_name, hod_name, description)
                        st.success(f"✅ Department '{dept_name}' added!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"❌ Error: {str(e)}")
    
    with col2:
        st.markdown("#### 📋 Existing Departments")
        
        departments = db.get_all_departments()
        
        if not departments:
            st.info("No departments added yet")
        else:
            for dept in departments:
                with st.expander(f"{dept['dept_code']} - {dept['dept_name']}", expanded=False):
                    st.write(f"**HOD:** {dept['hod_name'] or 'Not assigned'}")
                    st.write(f"**Description:** {dept['description'] or 'N/A'}")
                    st.caption(f"Created: {dept['created_at'][:10]}")
                    
                    st.divider()
                    
                    # Check dependencies
                    faculty_in_dept = db.get_all_faculty(department_id=dept['id'])
                    programs_in_dept = db.get_all_programs(department_id=dept['id'])
                    
                    if faculty_in_dept or programs_in_dept:
                        st.warning(f"⚠️ Cannot delete: {len(faculty_in_dept)} faculty and {len(programs_in_dept)} programs linked")
                    else:
                        if st.button(f"🗑️ Delete {dept['dept_code']}", key=f"del_dept_{dept['id']}", type="secondary"):
                            with db.get_connection() as conn:
                                cursor = conn.cursor()
                                cursor.execute("DELETE FROM departments WHERE id = ?", (dept['id'],))
                            st.success(f"Deleted {dept['dept_code']}")
                            st.rerun()

# ==================== TAB 3: INFRASTRUCTURE ====================
with tab3:
    st.markdown("### 🏛️ Classrooms & Labs Management")
    
    # Sub-tabs for rooms and labs
    infra_tab1, infra_tab2 = st.tabs(["🏫 Classrooms", "🖥️ Computer Labs"])
    
    with infra_tab1:
        col1, col2 = st.columns([1, 1])
        
        with col1:
            st.markdown("#### ➕ Add Classroom")
            
            with st.form("add_classroom_form"):
                room_code = st.text_input("Room Code *", placeholder="e.g., R301")
                room_name = st.text_input("Room Name *", placeholder="e.g., Lecture Hall 1")
                
                col_a, col_b = st.columns(2)
                with col_a:
                    capacity = st.number_input("Capacity *", min_value=10, max_value=500, value=60)
                with col_b:
                    floor = st.number_input("Floor", min_value=0, max_value=10, value=1)
                
                building = st.text_input("Building", placeholder="e.g., Main Block")
                
                facilities = st.multiselect(
                    "Facilities",
                    ["Projector", "AC", "Whiteboard", "Smart Board", "Audio System", "Microphone"]
                )
                
                submit = st.form_submit_button("Add Classroom", type="primary")
                
                if submit:
                    if not room_code or not room_name or not capacity:
                        st.error("❌ Please fill required fields")
                    else:
                        try:
                            db.create_infrastructure({
                                'room_code': room_code,
                                'room_name': room_name,
                                'room_type': 'Classroom',
                                'capacity': capacity,
                                'floor': floor,
                                'building': building,
                                'facilities': facilities
                            })
                            st.success(f"✅ Classroom '{room_name}' added!")
                            st.rerun()
                        except Exception as e:
                            st.error(f"❌ Error: {str(e)}")
        
        with col2:
            st.markdown("#### 📋 All Classrooms")
            
            classrooms = db.get_all_infrastructure(room_type='Classroom')
            
            if not classrooms:
                st.info("No classrooms added yet")
            else:
                for room in classrooms:
                    with st.expander(f"{room['room_code']} - {room['room_name']}", expanded=False):
                        col_a, col_b = st.columns(2)
                        with col_a:
                            st.metric("Capacity", room['capacity'])
                            st.write(f"**Floor:** {room['floor'] or 'N/A'}")
                        with col_b:
                            st.write(f"**Building:** {room['building'] or 'N/A'}")
                            if room['facilities']:
                                st.write("**Facilities:**", ", ".join(room['facilities']))
                        
                        st.divider()
                        
                        # Check if room is being used in any timetable
                        with db.get_connection() as conn:
                            cursor = conn.cursor()
                            cursor.execute("SELECT COUNT(*) as count FROM timetable_sessions WHERE room_id = ?", (room['id'],))
                            usage = cursor.fetchone()['count']
                        
                        if usage > 0:
                            st.warning(f"⚠️ Cannot delete: Used in {usage} timetable session(s)")
                        else:
                            col_del1, col_del2 = st.columns(2)
                            with col_del1:
                                if st.button(f"🗑️ Delete", key=f"del_room_{room['id']}", type="secondary", use_container_width=True):
                                    with db.get_connection() as conn:
                                        cursor = conn.cursor()
                                        cursor.execute("DELETE FROM infrastructure WHERE id = ?", (room['id'],))
                                    st.success(f"Deleted {room['room_code']}")
                                    st.rerun()
    
    with infra_tab2:
        col1, col2 = st.columns([1, 1])
        
        with col1:
            st.markdown("#### ➕ Add Computer Lab")
            
            with st.form("add_lab_form"):
                lab_code = st.text_input("Lab Code *", placeholder="e.g., LAB-CS1")
                lab_name = st.text_input("Lab Name *", placeholder="e.g., Programming Lab")
                
                lab_type = st.selectbox(
                    "Lab Type",
                    ["Programming Lab", "Database Lab", "Networking Lab", "AI/ML Lab", 
                     "Hardware Lab", "General Purpose Lab"]
                )
                
                col_a, col_b = st.columns(2)
                with col_a:
                    capacity = st.number_input("Computer Capacity *", min_value=10, max_value=100, value=30)
                with col_b:
                    floor = st.number_input("Floor", min_value=0, max_value=10, value=1, key="lab_floor")
                
                building = st.text_input("Building", placeholder="e.g., CS Block", key="lab_building")
                
                software = st.text_area(
                    "Installed Software (comma-separated)",
                    placeholder="e.g., Visual Studio, Eclipse, MySQL, Python"
                )
                
                submit = st.form_submit_button("Add Lab", type="primary")
                
                if submit:
                    if not lab_code or not lab_name:
                        st.error("❌ Please fill required fields")
                    else:
                        try:
                            facilities = [lab_type]
                            if software:
                                facilities.extend([s.strip() for s in software.split(",")])
                            
                            db.create_infrastructure({
                                'room_code': lab_code,
                                'room_name': lab_name,
                                'room_type': 'Lab',
                                'capacity': capacity,
                                'floor': floor,
                                'building': building,
                                'facilities': facilities
                            })
                            st.success(f"✅ Lab '{lab_name}' added!")
                            st.rerun()
                        except Exception as e:
                            st.error(f"❌ Error: {str(e)}")
        
        with col2:
            st.markdown("#### 📋 All Labs")
            
            labs = db.get_all_infrastructure(room_type='Lab')
            
            if not labs:
                st.info("No labs added yet")
            else:
                for lab in labs:
                    with st.expander(f"{lab['room_code']} - {lab['room_name']}", expanded=False):
                        col_a, col_b = st.columns(2)
                        with col_a:
                            st.metric("Capacity", f"{lab['capacity']} PCs")
                            st.write(f"**Floor:** {lab['floor'] or 'N/A'}")
                        with col_b:
                            st.write(f"**Building:** {lab['building'] or 'N/A'}")
                            if lab['facilities']:
                                st.write("**Type:**", lab['facilities'][0] if lab['facilities'] else 'N/A')
                        
                        st.divider()
                        
                        # Check usage
                        with db.get_connection() as conn:
                            cursor = conn.cursor()
                            cursor.execute("SELECT COUNT(*) as count FROM timetable_sessions WHERE room_id = ?", (lab['id'],))
                            usage = cursor.fetchone()['count']
                            
                            cursor.execute("SELECT COUNT(*) as count FROM subjects WHERE preferred_lab_id = ?", (lab['id'],))
                            subject_links = cursor.fetchone()['count']
                        
                        if usage > 0 or subject_links > 0:
                            st.warning(f"⚠️ Cannot delete: Used in {usage} sessions and {subject_links} subject(s)")
                        else:
                            if st.button(f"🗑️ Delete", key=f"del_lab_{lab['id']}", type="secondary", use_container_width=True):
                                with db.get_connection() as conn:
                                    cursor = conn.cursor()
                                    cursor.execute("DELETE FROM infrastructure WHERE id = ?", (lab['id'],))
                                st.success(f"Deleted {lab['room_code']}")
                                st.rerun()

# ==================== TAB 4: FACULTY ====================
with tab4:
    st.markdown("### 👨‍🏫 Faculty Management")
    
    departments = db.get_all_departments()
    
    if not departments:
        st.warning("⚠️ Please add departments first (Tab 2)")
    else:
        col1, col2 = st.columns([1, 1])
        
        with col1:
            st.markdown("#### ➕ Add Faculty Member")
            
            with st.form("add_faculty_form"):
                faculty_code = st.text_input("Faculty Code *", placeholder="e.g., FAC001")
                faculty_name = st.text_input("Faculty Name *", placeholder="e.g., Dr. Jane Smith")
                
                dept_id = st.selectbox(
                    "Department *",
                    options=[d['id'] for d in departments],
                    format_func=lambda x: next(d['dept_name'] for d in departments if d['id'] == x)
                )
                
                designation = st.selectbox(
                    "Designation",
                    ["Professor", "Associate Professor", "Assistant Professor", "Lecturer", "Lab Instructor"]
                )
                
                col_a, col_b = st.columns(2)
                with col_a:
                    email = st.text_input("Email", placeholder="jane@college.edu")
                with col_b:
                    phone = st.text_input("Phone", placeholder="+91 9876543210")
                
                col_a, col_b = st.columns(2)
                with col_a:
                    max_hours_week = st.number_input("Max Hours/Week", min_value=6, max_value=30, value=18)
                with col_b:
                    max_hours_day = st.number_input("Max Hours/Day", min_value=2, max_value=10, value=6)
                
                college_profile = db.get_college_profile()
                if college_profile:
                    preferred_days = st.multiselect(
                        "Preferred Working Days",
                        college_profile['working_days']
                    )
                    
                    preferred_times = st.multiselect(
                        "Preferred Time Slots",
                        college_profile['time_slots']
                    )
                else:
                    preferred_days = []
                    preferred_times = []
                
                submit = st.form_submit_button("Add Faculty", type="primary")
                
                if submit:
                    if not faculty_code or not faculty_name:
                        st.error("❌ Please fill required fields")
                    else:
                        try:
                            db.create_faculty({
                                'faculty_code': faculty_code,
                                'faculty_name': faculty_name,
                                'department_id': dept_id,
                                'designation': designation,
                                'email': email,
                                'phone': phone,
                                'max_hours_per_week': max_hours_week,
                                'max_hours_per_day': max_hours_day,
                                'preferred_days': preferred_days,
                                'preferred_times': preferred_times,
                                'unavailable_slots': []
                            })
                            st.success(f"✅ Faculty '{faculty_name}' added!")
                            st.rerun()
                        except Exception as e:
                            st.error(f"❌ Error: {str(e)}")
        
        with col2:
            st.markdown("#### 📋 All Faculty Members")
            
            faculty_list = db.get_all_faculty()
            
            if not faculty_list:
                st.info("No faculty added yet")
            else:
                # Filter by department
                dept_filter = st.selectbox(
                    "Filter by Department",
                    ["All"] + [d['dept_name'] for d in departments],
                    key="faculty_dept_filter"
                )
                
                for faculty in faculty_list:
                    faculty_dept = next((d for d in departments if d['id'] == faculty['department_id']), None)
                    
                    if dept_filter != "All" and faculty_dept and faculty_dept['dept_name'] != dept_filter:
                        continue
                    
                    with st.expander(f"{faculty['faculty_code']} - {faculty['faculty_name']}", expanded=False):
                        col_a, col_b = st.columns(2)
                        
                        with col_a:
                            st.write(f"**Department:** {faculty_dept['dept_name'] if faculty_dept else 'N/A'}")
                            st.write(f"**Designation:** {faculty['designation']}")
                            st.write(f"**Email:** {faculty['email'] or 'N/A'}")
                        
                        with col_b:
                            st.metric("Max Hrs/Week", faculty['max_hours_per_week'])
                            st.metric("Max Hrs/Day", faculty['max_hours_per_day'])
                        
                        # Show workload
                        workload = db.calculate_faculty_workload(faculty['id'])
                        st.progress(min(workload['total_hours'] / faculty['max_hours_per_week'], 1.0))
                        st.caption(f"Current Load: {workload['total_hours']}/{faculty['max_hours_per_week']} hours")
                        
                        st.divider()
                        
                        # Check dependencies
                        allocations = db.get_allocations_by_faculty(faculty['id'])
                        
                        with db.get_connection() as conn:
                            cursor = conn.cursor()
                            cursor.execute("SELECT COUNT(*) as count FROM timetable_sessions WHERE faculty_id = ?", (faculty['id'],))
                            sessions = cursor.fetchone()['count']
                        
                        if allocations or sessions > 0:
                            st.warning(f"⚠️ Cannot delete: {len(allocations)} allocation(s) and {sessions} session(s)")
                        else:
                            if st.button(f"🗑️ Delete {faculty['faculty_code']}", key=f"del_fac_{faculty['id']}", type="secondary", use_container_width=True):
                                with db.get_connection() as conn:
                                    cursor = conn.cursor()
                                    cursor.execute("UPDATE faculty SET is_active = 0 WHERE id = ?", (faculty['id'],))
                                st.success(f"Deleted {faculty['faculty_name']}")
                                st.rerun()

# ==================== TAB 5: PROGRAMS & BATCHES ====================
with tab5:
    st.markdown("### 📚 Programs & Batches Management")
    
    departments = db.get_all_departments()
    
    if not departments:
        st.warning("⚠️ Please add departments first (Tab 2)")
    else:
        prog_tab1, prog_tab2 = st.tabs(["📚 Programs", "🎓 Batches/Classes"])
        
        with prog_tab1:
            col1, col2 = st.columns([1, 1])
            
            with col1:
                st.markdown("#### ➕ Add Program")
                
                with st.form("add_program_form"):
                    prog_code = st.text_input("Program Code *", placeholder="e.g., BTECH-CS")
                    prog_name = st.text_input("Program Name *", placeholder="e.g., B.Tech Computer Science")
                    
                    col_a, col_b = st.columns(2)
                    with col_a:
                        duration = st.number_input("Duration (years) *", min_value=1, max_value=6, value=4)
                    with col_b:
                        dept_id = st.selectbox(
                            "Department",
                            options=[d['id'] for d in departments],
                            format_func=lambda x: next(d['dept_name'] for d in departments if d['id'] == x),
                            key="prog_dept"
                        )
                    
                    description = st.text_area("Description")
                    
                    submit = st.form_submit_button("Add Program", type="primary")
                    
                    if submit:
                        if not prog_code or not prog_name:
                            st.error("❌ Please fill required fields")
                        else:
                            try:
                                db.create_program({
                                    'program_code': prog_code,
                                    'program_name': prog_name,
                                    'duration_years': duration,
                                    'department_id': dept_id,
                                    'description': description
                                })
                                st.success(f"✅ Program '{prog_name}' added!")
                                st.rerun()
                            except Exception as e:
                                st.error(f"❌ Error: {str(e)}")
            
            with col2:
                st.markdown("#### 📋 All Programs")
                
                programs = db.get_all_programs()
                
                if not programs:
                    st.info("No programs added yet")
                else:
                    for prog in programs:
                        prog_dept = next((d for d in departments if d['id'] == prog['department_id']), None)
                        
                        with st.expander(f"{prog['program_code']} - {prog['program_name']}", expanded=False):
                            st.write(f"**Department:** {prog_dept['dept_name'] if prog_dept else 'N/A'}")
                            st.write(f"**Duration:** {prog['duration_years']} years")
                            st.write(f"**Description:** {prog['description'] or 'N/A'}")
                            
                            st.divider()
                            
                            # Check dependencies
                            batches_in_prog = db.get_all_batches(program_id=prog['id'])
                            
                            if batches_in_prog:
                                st.warning(f"⚠️ Cannot delete: {len(batches_in_prog)} batch(es) linked to this program")
                            else:
                                if st.button(f"🗑️ Delete {prog['program_code']}", key=f"del_prog_{prog['id']}", type="secondary", use_container_width=True):
                                    with db.get_connection() as conn:
                                        cursor = conn.cursor()
                                        cursor.execute("DELETE FROM programs WHERE id = ?", (prog['id'],))
                                    st.success(f"Deleted {prog['program_name']}")
                                    st.rerun()
        
        with prog_tab2:
            programs = db.get_all_programs()
            
            if not programs:
                st.warning("⚠️ Please add programs first")
            else:
                col1, col2 = st.columns([1, 1])
                
                with col1:
                    st.markdown("#### ➕ Add Batch/Class")
                    
                    with st.form("add_batch_form"):
                        batch_code = st.text_input("Batch Code *", placeholder="e.g., BTECH-DS-Y2-A")
                        batch_name = st.text_input("Batch Name *", placeholder="e.g., BTech DS Year 2 Section A")
                        
                        program_id = st.selectbox(
                            "Program *",
                            options=[p['id'] for p in programs],
                            format_func=lambda x: next(p['program_name'] for p in programs if p['id'] == x)
                        )
                        
                        col_a, col_b, col_c = st.columns(3)
                        with col_a:
                            year = st.number_input("Year *", min_value=1, max_value=6, value=1)
                        with col_b:
                            section = st.text_input("Section", placeholder="A", max_chars=1)
                        with col_c:
                            num_students = st.number_input("Students *", min_value=1, max_value=200, value=60)
                        
                        semester = st.number_input("Semester", min_value=1, max_value=12, value=1)
                        
                        submit = st.form_submit_button("Add Batch", type="primary")
                        
                        if submit:
                            if not batch_code or not batch_name:
                                st.error("❌ Please fill required fields")
                            else:
                                try:
                                    db.create_batch({
                                        'batch_code': batch_code,
                                        'batch_name': batch_name,
                                        'program_id': program_id,
                                        'year': year,
                                        'section': section.upper() if section else None,
                                        'num_students': num_students,
                                        'semester': semester
                                    })
                                    st.success(f"✅ Batch '{batch_name}' added!")
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"❌ Error: {str(e)}")
                
                with col2:
                    st.markdown("#### 📋 All Batches")
                    
                    batches = db.get_all_batches()
                    
                    if not batches:
                        st.info("No batches added yet")
                    else:
                        # Filter by program
                        prog_filter = st.selectbox(
                            "Filter by Program",
                            ["All"] + [p['program_name'] for p in programs],
                            key="batch_prog_filter"
                        )
                        
                        for batch in batches:
                            batch_prog = next((p for p in programs if p['id'] == batch['program_id']), None)
                            
                            if prog_filter != "All" and batch_prog and batch_prog['program_name'] != prog_filter:
                                continue
                            
                            with st.expander(f"{batch['batch_code']} - {batch['batch_name']}", expanded=False):
                                col_a, col_b = st.columns(2)
                                with col_a:
                                    st.write(f"**Program:** {batch_prog['program_name'] if batch_prog else 'N/A'}")
                                    st.write(f"**Year:** {batch['year']}")
                                    st.write(f"**Section:** {batch['section'] or 'N/A'}")
                                with col_b:
                                    st.metric("Students", batch['num_students'])
                                    st.metric("Semester", batch['semester'])
                                
                                st.divider()
                                
                                # Check dependencies
                                allocations = db.get_allocations_by_batch(batch['id'])
                                
                                with db.get_connection() as conn:
                                    cursor = conn.cursor()
                                    cursor.execute("SELECT COUNT(*) as count FROM timetable_sessions WHERE batch_id = ?", (batch['id'],))
                                    sessions = cursor.fetchone()['count']
                                
                                if allocations or sessions > 0:
                                    st.warning(f"⚠️ Cannot delete: {len(allocations)} allocation(s) and {sessions} session(s)")
                                else:
                                    if st.button(f"🗑️ Delete {batch['batch_code']}", key=f"del_batch_{batch['id']}", type="secondary", use_container_width=True):
                                        with db.get_connection() as conn:
                                            cursor = conn.cursor()
                                            cursor.execute("UPDATE batches SET is_active = 0 WHERE id = ?", (batch['id'],))
                                        st.success(f"Deleted {batch['batch_name']}")
                                        st.rerun()

# ==================== TAB 6: SUBJECTS ====================
with tab6:
    st.markdown("### 📖 Subject/Course Management")
    
    departments = db.get_all_departments()
    labs = db.get_all_infrastructure(room_type='Lab')
    
    if not departments:
        st.warning("⚠️ Please add departments first (Tab 2)")
    else:
        col1, col2 = st.columns([1, 1])
        
        with col1:
            st.markdown("#### ➕ Add Subject")
            
            with st.form("add_subject_form"):
                subject_code = st.text_input("Subject Code *", placeholder="e.g., CS202")
                subject_name = st.text_input("Subject Name *", placeholder="e.g., Data Structures")
                
                col_a, col_b = st.columns(2)
                with col_a:
                    subject_type = st.selectbox(
                        "Subject Type *",
                        ["Theory", "Lab", "Theory + Lab", "Tutorial", "Project"]
                    )
                with col_b:
                    credits = st.number_input("Credits", min_value=0, max_value=10, value=4)
                
                st.markdown("**Hours per Week:**")
                col_a, col_b, col_c = st.columns(3)
                with col_a:
                    theory_hours = st.number_input("Theory", min_value=0, max_value=10, value=3)
                with col_b:
                    lab_hours = st.number_input("Lab", min_value=0, max_value=10, value=0)
                with col_c:
                    tutorial_hours = st.number_input("Tutorial", min_value=0, max_value=10, value=0)
                
                total_hours = theory_hours + lab_hours + tutorial_hours
                st.info(f"Total hours per week: {total_hours}")
                
                requires_lab = st.checkbox("Requires Computer Lab", value=(lab_hours > 0))
                
                preferred_lab = None
                if requires_lab and labs:
                    preferred_lab = st.selectbox(
                        "Preferred Lab",
                        options=[None] + [lab['id'] for lab in labs],
                        format_func=lambda x: "Any Lab" if x is None else next(lab['room_name'] for lab in labs if lab['id'] == x)
                    )
                
                consecutive_hours = st.checkbox(
                    "Lab sessions must be consecutive",
                    value=True,
                    help="E.g., 2-hour lab should be scheduled in consecutive slots"
                )
                
                dept_id = st.selectbox(
                    "Department",
                    options=[d['id'] for d in departments],
                    format_func=lambda x: next(d['dept_name'] for d in departments if d['id'] == x),
                    key="subject_dept"
                )
                
                submit = st.form_submit_button("Add Subject", type="primary")
                
                if submit:
                    if not subject_code or not subject_name or total_hours == 0:
                        st.error("❌ Please fill required fields and ensure total hours > 0")
                    else:
                        try:
                            db.create_subject({
                                'subject_code': subject_code,
                                'subject_name': subject_name,
                                'subject_type': subject_type,
                                'credits': credits,
                                'theory_hours': theory_hours,
                                'lab_hours': lab_hours,
                                'tutorial_hours': tutorial_hours,
                                'total_hours_per_week': total_hours,
                                'requires_lab': 1 if requires_lab else 0,
                                'preferred_lab_id': preferred_lab,
                                'consecutive_hours': 1 if consecutive_hours else 0,
                                'department_id': dept_id
                            })
                            st.success(f"✅ Subject '{subject_name}' added!")
                            st.rerun()
                        except Exception as e:
                            st.error(f"❌ Error: {str(e)}")
        
        with col2:
            st.markdown("#### 📋 All Subjects")
            
            subjects = db.get_all_subjects()
            
            if not subjects:
                st.info("No subjects added yet")
            else:
                # Filter
                dept_filter = st.selectbox(
                    "Filter by Department",
                    ["All"] + [d['dept_name'] for d in departments],
                    key="subject_dept_filter"
                )
                
                for subject in subjects:
                    subject_dept = next((d for d in departments if d['id'] == subject['department_id']), None)
                    
                    if dept_filter != "All" and subject_dept and subject_dept['dept_name'] != dept_filter:
                        continue
                    
                    with st.expander(f"{subject['subject_code']} - {subject['subject_name']}", expanded=False):
                        col_a, col_b = st.columns(2)
                        
                        with col_a:
                            st.write(f"**Type:** {subject['subject_type']}")
                            st.write(f"**Credits:** {subject['credits']}")
                            st.write(f"**Theory:** {subject['theory_hours']} hrs/week")
                        
                        with col_b:
                            st.write(f"**Lab:** {subject['lab_hours']} hrs/week")
                            st.write(f"**Tutorial:** {subject['tutorial_hours']} hrs/week")
                            st.metric("Total Hrs/Week", subject['total_hours_per_week'])
                        
                        if subject['requires_lab']:
                            lab = next((l for l in labs if l['id'] == subject['preferred_lab_id']), None)
                            st.info(f"🖥️ Requires Lab: {lab['room_name'] if lab else 'Any Lab'}")
                        
                        st.divider()
                        
                        # Check dependencies
                        with db.get_connection() as conn:
                            cursor = conn.cursor()
                            cursor.execute("SELECT COUNT(*) as count FROM subject_allocation WHERE subject_id = ?", (subject['id'],))
                            allocations = cursor.fetchone()['count']
                            
                            cursor.execute("SELECT COUNT(*) as count FROM timetable_sessions WHERE subject_id = ?", (subject['id'],))
                            sessions = cursor.fetchone()['count']
                        
                        if allocations > 0 or sessions > 0:
                            st.warning(f"⚠️ Cannot delete: {allocations} allocation(s) and {sessions} session(s)")
                        else:
                            if st.button(f"🗑️ Delete {subject['subject_code']}", key=f"del_subj_{subject['id']}", type="secondary", use_container_width=True):
                                with db.get_connection() as conn:
                                    cursor = conn.cursor()
                                    cursor.execute("DELETE FROM subjects WHERE id = ?", (subject['id'],))
                                st.success(f"Deleted {subject['subject_name']}")
                                st.rerun()

# ==================== TAB 7: SUBJECT ALLOCATION ====================
with tab7:
    st.markdown("### 📋 Subject Allocation (Faculty ↔ Batch ↔ Subject)")
    
    batches = db.get_all_batches()
    subjects = db.get_all_subjects()
    faculty_list = db.get_all_faculty()
    
    if not batches or not subjects or not faculty_list:
        st.warning("⚠️ Please add Programs, Batches, Subjects, and Faculty first")
    else:
        col1, col2 = st.columns([1, 1])
        
        with col1:
            st.markdown("#### ➕ Allocate Subject")
            st.caption("Assign a subject to a batch and faculty")
            
            with st.form("allocate_subject_form"):
                batch_id = st.selectbox(
                    "Select Batch *",
                    options=[b['id'] for b in batches],
                    format_func=lambda x: next(b['batch_name'] for b in batches if b['id'] == x)
                )
                
                subject_id = st.selectbox(
                    "Select Subject *",
                    options=[s['id'] for s in subjects],
                    format_func=lambda x: f"{next(s['subject_code'] for s in subjects if s['id'] == x)} - {next(s['subject_name'] for s in subjects if s['id'] == x)}"
                )
                
                faculty_id = st.selectbox(
                    "Select Faculty *",
                    options=[f['id'] for f in faculty_list],
                    format_func=lambda x: f"{next(f['faculty_code'] for f in faculty_list if f['id'] == x)} - {next(f['faculty_name'] for f in faculty_list if f['id'] == x)}"
                )
                
                col_a, col_b = st.columns(2)
                with col_a:
                    semester = st.number_input("Semester", min_value=1, max_value=12, value=1, key="alloc_sem")
                with col_b:
                    academic_year = st.text_input("Academic Year", value="2025-26", key="alloc_year")
                
                submit = st.form_submit_button("Allocate Subject", type="primary")
                
                if submit:
                    try:
                        db.create_subject_allocation({
                            'subject_id': subject_id,
                            'batch_id': batch_id,
                            'faculty_id': faculty_id,
                            'semester': semester,
                            'academic_year': academic_year
                        })
                        st.success("✅ Subject allocated successfully!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"❌ Error: {str(e)}")
        
        with col2:
            st.markdown("#### 📋 Current Allocations")
            
            view_by = st.radio("View By:", ["Batch", "Faculty"], horizontal=True)
            
            if view_by == "Batch":
                selected_batch = st.selectbox(
                    "Select Batch",
                    options=[b['id'] for b in batches],
                    format_func=lambda x: next(b['batch_name'] for b in batches if b['id'] == x),
                    key="view_batch"
                )
                
                allocations = db.get_allocations_by_batch(selected_batch)
                
                if not allocations:
                    st.info("No subjects allocated to this batch yet")
                else:
                    total_hours = sum(a['total_hours_per_week'] for a in allocations)
                    st.metric("Total Hours per Week", total_hours)
                    
                    for alloc in allocations:
                        with st.expander(f"{alloc['subject_code']} - {alloc['subject_name']}", expanded=False):
                            st.write(f"**Faculty:** {alloc['faculty_name']} ({alloc['faculty_code']})")
                            st.write(f"**Hours/Week:** {alloc['total_hours_per_week']}")
                            st.write(f"**Theory:** {alloc['theory_hours']} | **Lab:** {alloc['lab_hours']}")
                            
                            st.divider()
                            
                            # Check if allocation is used in timetable
                            with db.get_connection() as conn:
                                cursor = conn.cursor()
                                cursor.execute("""
                                    SELECT COUNT(*) as count FROM timetable_sessions 
                                    WHERE subject_id = ? AND batch_id = ? AND faculty_id = ?
                                """, (alloc['subject_id'], alloc['batch_id'], alloc['faculty_id']))
                                sessions = cursor.fetchone()['count']
                            
                            if sessions > 0:
                                st.warning(f"⚠️ Cannot delete: Used in {sessions} timetable session(s)")
                            else:
                                if st.button(f"🗑️ Remove Allocation", key=f"del_alloc_{alloc['id']}", type="secondary", use_container_width=True):
                                    with db.get_connection() as conn:
                                        cursor = conn.cursor()
                                        cursor.execute("DELETE FROM subject_allocation WHERE id = ?", (alloc['id'],))
                                    st.success("Allocation removed!")
                                    st.rerun()
            
            else:  # Faculty
                selected_faculty = st.selectbox(
                    "Select Faculty",
                    options=[f['id'] for f in faculty_list],
                    format_func=lambda x: next(f['faculty_name'] for f in faculty_list if f['id'] == x),
                    key="view_faculty"
                )
                
                workload = db.calculate_faculty_workload(selected_faculty)
                faculty_info = next(f for f in faculty_list if f['id'] == selected_faculty)
                
                col_a, col_b, col_c = st.columns(3)
                with col_a:
                    st.metric("Total Hours", workload['total_hours'])
                with col_b:
                    st.metric("Max Allowed", faculty_info['max_hours_per_week'])
                with col_c:
                    remaining = faculty_info['max_hours_per_week'] - workload['total_hours']
                    st.metric("Remaining", remaining, delta=remaining)
                
                st.progress(min(workload['total_hours'] / faculty_info['max_hours_per_week'], 1.0))
                
                if not workload['allocations']:
                    st.info("No subjects allocated to this faculty yet")
                else:
                    for alloc in workload['allocations']:
                        with st.expander(f"{alloc['subject_code']} - {alloc['subject_name']}", expanded=False):
                            st.write(f"**Batch:** {alloc['batch_name']}")
                            st.write(f"**Students:** {alloc['num_students']}")
                            st.write(f"**Hours/Week:** {alloc['total_hours_per_week']}")
                            
                            st.divider()
                            
                            # Check usage
                            with db.get_connection() as conn:
                                cursor = conn.cursor()
                                cursor.execute("""
                                    SELECT COUNT(*) as count FROM timetable_sessions 
                                    WHERE subject_id = ? AND faculty_id = ?
                                """, (alloc['subject_id'], selected_faculty))
                                sessions = cursor.fetchone()['count']
                            
                            if sessions > 0:
                                st.warning(f"⚠️ Cannot delete: Used in {sessions} session(s)")
                            else:
                                # Get allocation ID
                                with db.get_connection() as conn:
                                    cursor = conn.cursor()
                                    cursor.execute("""
                                        SELECT id FROM subject_allocation 
                                        WHERE subject_id = ? AND faculty_id = ?
                                    """, (alloc['subject_id'], selected_faculty))
                                    alloc_row = cursor.fetchone()
                                
                                if alloc_row:
                                    if st.button(f"🗑️ Remove", key=f"del_fac_alloc_{alloc_row['id']}", type="secondary", use_container_width=True):
                                        with db.get_connection() as conn:
                                            cursor = conn.cursor()
                                            cursor.execute("DELETE FROM subject_allocation WHERE id = ?", (alloc_row['id'],))
                                        st.success("Allocation removed!")
                                        st.rerun()

# Footer
st.divider()
st.caption(f"Setup Wizard | Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
st.caption("💡 Complete all setup steps before generating timetables. Use delete buttons to remove unused items.")
