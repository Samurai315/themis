import streamlit as st
from lib.database import get_database
from lib.genetic_algo import ScheduleGA
from lib.gemini_ai import HybridOptimizer, GeminiScheduler
import plotly.graph_objects as go
import plotly.express as px
from lib.export_utils import ScheduleExporter
import pandas as pd
from datetime import datetime
import json
import time

st.set_page_config(page_title="Timetable Generator", page_icon="🔧", layout="wide")

# Check authentication
if not st.session_state.get("authenticated"):
    st.warning("⚠️ Please login first")
    st.stop()

# Update activity
if 'last_activity' in st.session_state:
    st.session_state.last_activity = datetime.now()

db = get_database()
user = st.session_state.user

# Initialize session state
if 'optimization_result' not in st.session_state:
    st.session_state.optimization_result = None
if 'optimization_running' not in st.session_state:
    st.session_state.optimization_running = False

# Header
st.title("🔧 Timetable Generator & Optimizer")
st.markdown("Generate and optimize weekly recurring timetables using AI + Genetic Algorithms")

st.divider()

# Check if basic setup is complete
college_profile = db.get_college_profile()
departments = db.get_all_departments()
batches = db.get_all_batches()
faculty_list = db.get_all_faculty()
subjects = db.get_all_subjects()

if not college_profile:
    st.error("❌ Please complete College Profile setup first!")
    if st.button("Go to Setup"):
        st.switch_page("pages/0_Setup.py")
    st.stop()

if not batches or not faculty_list or not subjects:
    st.warning("⚠️ Incomplete setup detected")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Batches", len(batches), delta="Required" if not batches else "✓")
    with col2:
        st.metric("Faculty", len(faculty_list), delta="Required" if not faculty_list else "✓")
    with col3:
        st.metric("Subjects", len(subjects), delta="Required" if not subjects else "✓")
    
    if st.button("Complete Setup"):
        st.switch_page("pages/0_Setup.py")
    st.stop()

# ==================== EDIT MODE CHECK ====================

edit_mode = False
existing_schedule = None
existing_sessions = []

if 'edit_schedule_id' in st.session_state and st.session_state.edit_schedule_id:
    edit_schedule_id = st.session_state.edit_schedule_id
    existing_schedule = db.get_schedule(edit_schedule_id)
    
    if existing_schedule:
        edit_mode = True
        existing_sessions = db.get_timetable_sessions(schedule_id=edit_schedule_id)
        
        st.info(f"✏️ **Edit Mode:** You are editing '{existing_schedule['title']}'")
        
        col1, col2 = st.columns([3, 1])
        with col2:
            if st.button("❌ Cancel & Exit Edit Mode", type="secondary", use_container_width=True):
                del st.session_state.edit_schedule_id
                st.rerun()

st.divider()

# ==================== MODE SELECTOR ====================

if not edit_mode:
    mode = st.radio(
        "Select Mode",
        ["➕ Create New Timetable", "✏️ Edit Existing Timetable"],
        horizontal=True
    )
    
    if mode == "✏️ Edit Existing Timetable":
        # Show existing timetables
        user_schedules = db.get_user_schedules(user['id'])
        
        if not user_schedules:
            st.warning("No timetables found to edit")
            st.stop()
        
        col1, col2 = st.columns([3, 1])
        
        with col1:
            schedule_to_edit = st.selectbox(
                "Select Timetable to Edit",
                options=[s['id'] for s in user_schedules],
                format_func=lambda x: next(f"{s['title']} ({s['academic_year']}) - {s['status']}" for s in user_schedules if s['id'] == x)
            )
        
        with col2:
            if st.button("✏️ Load for Editing", type="primary", use_container_width=True):
                st.session_state.edit_schedule_id = schedule_to_edit
                st.rerun()
        
        st.stop()

# ==================== SCHEDULE CREATION/EDITING FORM ====================

st.markdown("### 📋 Timetable Details")

col1, col2, col3 = st.columns(3)

with col1:
    schedule_title = st.text_input(
        "Timetable Name *",
        value=existing_schedule['title'] if edit_mode else "",
        placeholder="e.g., Odd Semester 2025-26",
        help="Give your timetable a descriptive name"
    )

with col2:
    semester = st.number_input(
        "Semester",
        min_value=1,
        max_value=12,
        value=existing_schedule['semester'] if edit_mode and existing_schedule['semester'] else 1,
        help="Which semester is this timetable for?"
    )

with col3:
    academic_year = st.text_input(
        "Academic Year",
        value=existing_schedule['academic_year'] if edit_mode and existing_schedule['academic_year'] else college_profile['academic_year'],
        help="Academic year (e.g., 2025-26)"
    )

# Semester configuration
st.markdown("### 📅 Semester Configuration")

col1, col2, col3 = st.columns(3)

with col1:
    num_weeks = st.number_input(
        "Teaching Weeks",
        min_value=1,
        max_value=20,
        value=16,
        help="Total weeks in the semester (excluding holidays/exams)"
    )

with col2:
    start_date = st.date_input(
        "Semester Start Date",
        help="When does the semester begin?"
    )

with col3:
    end_date = st.date_input(
        "Semester End Date",
        help="When does the semester end?"
    )

st.info(f"📅 This will generate a **weekly recurring timetable** for {num_weeks} weeks. The same schedule repeats every week.")

# Batch selection
st.markdown("### 🎓 Select Batches to Include")
st.caption("Select the batches/classes that should be included in this timetable")

programs = db.get_all_programs()
batch_selection = {}

# Get previously selected batches if editing
previously_selected = []
if edit_mode and existing_sessions:
    previously_selected = list(set(s['batch_id'] for s in existing_sessions))

for program in programs:
    with st.expander(f"📚 {program['program_name']}", expanded=True):
        program_batches = db.get_all_batches(program_id=program['id'])
        
        if program_batches:
            cols = st.columns(min(len(program_batches), 4))
            
            for idx, batch in enumerate(program_batches):
                with cols[idx % 4]:
                    # Pre-check if editing and batch was in previous timetable
                    default_checked = batch['id'] in previously_selected if edit_mode else False
                    
                    selected = st.checkbox(
                        f"{batch['batch_name']}",
                        value=default_checked,
                        key=f"batch_{batch['id']}",
                        help=f"{batch['num_students']} students | Year {batch['year']} | Semester {batch['semester']}"
                    )
                    
                    if selected:
                        batch_selection[batch['id']] = batch

selected_batches = list(batch_selection.values())

if not selected_batches:
    st.info("👆 Please select at least one batch to generate timetable")
    st.stop()

st.success(f"✅ Selected {len(selected_batches)} batch(es)")

st.divider()

# ==================== GENERATE ENTITIES & CONSTRAINTS ====================

st.markdown("### ⚙️ Timetable Configuration")

# Get allocations for selected batches
all_allocations = []
for batch in selected_batches:
    allocations = db.get_allocations_by_batch(batch['id'], semester)
    all_allocations.extend(allocations)

if not all_allocations:
    st.warning(f"⚠️ No subject allocations found for selected batches in Semester {semester}")
    st.info("💡 Go to Setup → Subject Allocation to assign subjects to these batches")
    
    if st.button("Go to Setup"):
        st.switch_page("pages/0_Setup.py")
    st.stop()

st.metric("📚 Total Subject Allocations Found", len(all_allocations))

# Show allocation summary with weekly hours
with st.expander("📋 View Subject Allocations & Weekly Hours", expanded=True):
    alloc_summary = []
    total_weekly_hours = 0
    
    for alloc in all_allocations:
        weekly_hours = alloc['total_hours_per_week']
        semester_hours = weekly_hours * num_weeks
        total_weekly_hours += weekly_hours
        
        alloc_summary.append({
            'Subject': alloc['subject_name'],
            'Batch': alloc['batch_name'],
            'Faculty': alloc['faculty_name'],
            'Theory/Week': alloc['theory_hours'],
            'Lab/Week': alloc['lab_hours'],
            'Total/Week': weekly_hours,
            'Semester Total': semester_hours
        })
    
    alloc_df = pd.DataFrame(alloc_summary)
    st.dataframe(alloc_df, use_container_width=True, hide_index=True)
    
    st.success(f"**Total Weekly Hours to Schedule: {total_weekly_hours} hours**")
    st.caption(f"Over {num_weeks} weeks = {total_weekly_hours * num_weeks} total teaching hours")

# Convert allocations to entities (WEEKLY sessions to schedule)
entities = []
constraints = []

st.markdown("### 📊 Generating Weekly Sessions")

for alloc in all_allocations:
    batch = next(b for b in selected_batches if b['id'] == alloc['batch_id'])
    subject = db.get_subject_with_lab(alloc['subject_id'])
    faculty = next(f for f in faculty_list if f['id'] == alloc['faculty_id'])
    
    # Create WEEKLY theory sessions (recurring)
    if alloc['theory_hours'] > 0:
        for session_num in range(alloc['theory_hours']):
            entity_id = f"theory_{alloc['id']}_{session_num}"
            entities.append({
                "id": entity_id,
                "name": f"{subject['subject_name']} - Lecture {session_num + 1}",
                "allocation_id": alloc['id'],
                "subject_id": alloc['subject_id'],
                "subject_code": alloc['subject_code'],
                "batch_id": alloc['batch_id'],
                "batch_name": alloc['batch_name'],
                "faculty_id": alloc['faculty_id'],
                "faculty_name": alloc['faculty_name'],
                "session_type": "Theory",
                "duration": 1,  # 1 hour per slot
                "capacity_needed": batch['num_students'],
                "requires_lab": False,
                "preferred_room_type": "Classroom",
                "recurring": True,
                "weekly_occurrence": 1
            })
    
    # Create WEEKLY lab sessions (recurring)
    if alloc['lab_hours'] > 0:
        # Labs are typically 2-3 hours in a single session
        num_lab_sessions = 1 if alloc['lab_hours'] <= 3 else 2
        hours_per_lab = alloc['lab_hours'] // num_lab_sessions
        
        for session_num in range(num_lab_sessions):
            entity_id = f"lab_{alloc['id']}_{session_num}"
            entities.append({
                "id": entity_id,
                "name": f"{subject['subject_name']} - Lab Session {session_num + 1}",
                "allocation_id": alloc['id'],
                "subject_id": alloc['subject_id'],
                "subject_code": alloc['subject_code'],
                "batch_id": alloc['batch_id'],
                "batch_name": alloc['batch_name'],
                "faculty_id": alloc['faculty_id'],
                "faculty_name": alloc['faculty_name'],
                "session_type": "Lab",
                "duration": hours_per_lab,
                "capacity_needed": batch['num_students'],
                "requires_lab": True,
                "preferred_lab_id": subject.get('preferred_lab_id'),
                "consecutive_hours": True,
                "preferred_room_type": "Lab",
                "recurring": True,
                "weekly_occurrence": 1
            })

st.write(f"**Generated {len(entities)} weekly recurring sessions:**")
theory_count = len([e for e in entities if e['session_type'] == 'Theory'])
lab_count = len([e for e in entities if e['session_type'] == 'Lab'])

col1, col2, col3 = st.columns(3)
with col1:
    st.metric("📖 Theory Lectures/Week", theory_count)
    st.caption(f"= {theory_count * num_weeks} total lectures")
with col2:
    st.metric("🖥️ Lab Sessions/Week", lab_count)
    st.caption(f"= {lab_count * num_weeks} total lab sessions")
with col3:
    total_sessions_week = len(entities)
    total_sessions_semester = total_sessions_week * num_weeks
    st.metric("Total Sessions/Week", total_sessions_week)
    st.caption(f"= {total_sessions_semester} sessions in semester")

# Validation: Check if weekly schedule fits in available slots
working_days = college_profile['working_days']
time_slots = college_profile['time_slots']
available_slots_per_week = len(working_days) * len(time_slots)

st.divider()

col1, col2 = st.columns(2)
with col1:
    st.metric("Available Slots/Week", available_slots_per_week)
    st.caption(f"{len(working_days)} days × {len(time_slots)} periods")

with col2:
    st.metric("Sessions to Schedule", len(entities))
    utilization = (len(entities) / available_slots_per_week) * 100 if available_slots_per_week > 0 else 0
    st.caption(f"Utilization: {utilization:.1f}%")

if len(entities) > available_slots_per_week:
    st.error(f"⚠️ Not enough slots! Need {len(entities)} but only {available_slots_per_week} available.")
    st.info("💡 Solutions: Add more time slots, add Saturday, or reduce subjects")
    st.stop()
elif utilization > 80:
    st.warning(f"⚠️ High utilization ({utilization:.1f}%). Schedule may be very tight.")
else:
    st.success(f"✅ Sufficient capacity. {available_slots_per_week - len(entities)} slots will remain free.")

# Generate constraints
st.markdown("### 🔒 Constraint Configuration")

constraint_tab1, constraint_tab2 = st.tabs(["✅ Hard Constraints", "💡 Soft Constraints"])

with constraint_tab1:
    st.markdown("#### Mandatory Rules (Must be satisfied)")
    
    hard_constraints = []
    
    # Faculty conflict
    hard_constraints.append({
        "type": "faculty_conflict",
        "description": "Same faculty cannot teach 2 classes simultaneously",
        "weight": 100,
        "hard": True
    })
    
    # Batch conflict
    hard_constraints.append({
        "type": "batch_conflict",
        "description": "Same batch cannot have 2 classes simultaneously",
        "weight": 100,
        "hard": True
    })
    
    # Room capacity
    hard_constraints.append({
        "type": "room_capacity",
        "description": "Room capacity must accommodate batch size",
        "weight": 80,
        "hard": True
    })
    
    # Lab requirement
    hard_constraints.append({
        "type": "lab_requirement",
        "description": "Lab sessions must be in computer labs",
        "weight": 90,
        "hard": True
    })
    
    # Faculty workload
    for faculty in faculty_list:
        faculty_entities = [e for e in entities if e['faculty_id'] == faculty['id']]
        if faculty_entities:
            hard_constraints.append({
                "type": "faculty_max_hours",
                "faculty_id": faculty['id'],
                "max_hours_per_day": faculty['max_hours_per_day'],
                "max_hours_per_week": faculty['max_hours_per_week'],
                "description": f"{faculty['faculty_name']} cannot exceed {faculty['max_hours_per_day']} hrs/day",
                "weight": 85,
                "hard": True
            })
    
    for constraint in hard_constraints[:5]:
        st.info(f"✓ {constraint['description']}")
    
    st.caption(f"Total: {len(hard_constraints)} hard constraints configured")

with constraint_tab2:
    st.markdown("#### Preferences (Optimizes for better quality)")
    
    col1, col2 = st.columns(2)
    
    with col1:
        enable_balanced = st.checkbox(
            "Balanced Daily Distribution",
            value=True,
            help="Distribute classes evenly across all working days to avoid overloading specific days"
        )
        
        enable_gaps = st.checkbox(
            "Minimize Gaps Between Classes",
            value=True,
            help="Reduce idle free periods between consecutive classes for students"
        )
        
        enable_faculty_pref = st.checkbox(
            "Faculty Time Preferences",
            value=True,
            help="Schedule faculty during their preferred days and time slots when possible"
        )
    
    with col2:
        enable_consecutive_labs = st.checkbox(
            "Consecutive Lab Sessions",
            value=True,
            help="Schedule multi-hour lab sessions in consecutive time slots (e.g., 2PM-4PM together)"
        )
        
        enable_morning_theory = st.checkbox(
            "Morning Slots for Theory",
            value=False,
            help="Prefer scheduling theory classes in morning hours (better concentration)"
        )
        
        enable_afternoon_labs = st.checkbox(
            "Afternoon Slots for Labs",
            value=False,
            help="Prefer scheduling lab sessions in afternoon hours (common practice)"
        )
    
    soft_constraints = []
    
    if enable_balanced:
        soft_constraints.append({
            "type": "balanced_distribution",
            "description": "Distribute classes evenly across days",
            "weight": 30,
            "hard": False
        })
    
    if enable_gaps:
        soft_constraints.append({
            "type": "minimize_gaps",
            "description": "Reduce idle time between classes",
            "weight": 20,
            "hard": False
        })
    
    if enable_faculty_pref:
        soft_constraints.append({
            "type": "faculty_preferences",
            "description": "Respect faculty preferred days/times",
            "weight": 15,
            "hard": False
        })
    
    if enable_consecutive_labs:
        soft_constraints.append({
            "type": "consecutive_labs",
            "description": "Schedule lab sessions consecutively",
            "weight": 25,
            "hard": False
        })
    
    if enable_morning_theory:
        soft_constraints.append({
            "type": "morning_theory",
            "description": "Prefer morning for theory lectures",
            "weight": 10,
            "hard": False
        })
    
    if enable_afternoon_labs:
        soft_constraints.append({
            "type": "afternoon_labs",
            "description": "Prefer afternoon for lab sessions",
            "weight": 10,
            "hard": False
        })
    
    st.success(f"✅ {len(soft_constraints)} soft constraints enabled")

all_constraints = hard_constraints + soft_constraints

# ==================== OPTIMIZATION SETTINGS ====================

st.divider()
st.markdown("### 🚀 Optimization Configuration")

col1, col2 = st.columns([2, 1])

with col1:
    method = st.radio(
        "Optimization Method",
        ["🤖 Hybrid (AI + GA) - Recommended", "🧠 Gemini AI Only", "🧬 Genetic Algorithm Only"],
        help="""
        • Hybrid: Best results - AI generates smart initial solution, GA refines it
        • Gemini AI: Fast but may not respect all constraints
        • Genetic Algorithm: Reliable but slower, good for complex constraints
        """
    )

with col2:
    st.info("""
    **💡 Tip:**
    
    Hybrid mode gives the best balance of speed and quality!
    """)

method_map = {
    "🤖 Hybrid (AI + GA) - Recommended": "hybrid",
    "🧠 Gemini AI Only": "gemini",
    "🧬 Genetic Algorithm Only": "genetic"
}

selected_method = method_map[method]

# GA Parameters (if applicable)
if selected_method in ["hybrid", "genetic"]:
    with st.sidebar:
        st.markdown("## 🧬 Genetic Algorithm Parameters")
        st.caption("Fine-tune the optimization algorithm")
        
        with st.expander("⚙️ Core Settings", expanded=True):
            pop_size = st.slider(
                "Population Size",
                min_value=20,
                max_value=300,
                value=100,
                step=10,
                help="🔍 Number of candidate timetables in each generation. Higher = better exploration but slower. Recommended: 100-150"
            )
            
            generations = st.slider(
                "Max Generations",
                min_value=50,
                max_value=1000,
                value=300,
                step=50,
                help="🔄 Number of evolution cycles. More generations allow better convergence but take longer. Recommended: 200-500"
            )
            
            mutation_rate = st.slider(
                "Mutation Rate",
                min_value=0.01,
                max_value=0.5,
                value=0.1,
                step=0.01,
                format="%.2f",
                help="🎲 Probability of random changes in schedules. Higher = more exploration, lower = more exploitation. Recommended: 0.05-0.15"
            )
            
            crossover_rate = st.slider(
                "Crossover Rate",
                min_value=0.5,
                max_value=1.0,
                value=0.7,
                step=0.05,
                format="%.2f",
                help="🧬 Probability of combining two parent timetables. Higher = more mixing of solutions. Recommended: 0.6-0.8"
            )
        
        with st.expander("🎯 Advanced Settings", expanded=False):
            tournament_size = st.slider(
                "Tournament Size",
                min_value=2,
                max_value=10,
                value=3,
                help="🏆 Number of candidates competing in selection. Higher = stronger selection pressure (only best survive). Recommended: 3-5"
            )
            
            elitism_rate = st.slider(
                "Elitism Rate",
                min_value=0.0,
                max_value=0.5,
                value=0.1,
                step=0.05,
                format="%.2f",
                help="👑 Percentage of best timetables preserved unchanged. Prevents losing good solutions. Recommended: 0.05-0.15"
            )
            
            mutation_strategy = st.selectbox(
                "Mutation Strategy",
                ["swap", "shift", "random"],
                help="""
                🔧 How mutations are applied:
                • swap: Exchange two time slots (gentle changes)
                • shift: Move one class to different time/room (moderate changes)
                • random: Complete random reassignment (aggressive changes)
                Recommended: swap or shift
                """
            )
        
        st.divider()
        
        # Quick presets
        st.markdown("### 🎛️ Quick Presets")
        
        if st.button("⚡ Fast (Lower Quality)", use_container_width=True):
            pop_size = 50
            generations = 100
            st.rerun()
        
        if st.button("⚖️ Balanced (Recommended)", use_container_width=True):
            pop_size = 100
            generations = 300
            st.rerun()
        
        if st.button("🎯 High Quality (Slower)", use_container_width=True):
            pop_size = 200
            generations = 500
            st.rerun()

else:
    # Default values for non-GA methods
    pop_size = 100
    generations = 300
    mutation_rate = 0.1
    crossover_rate = 0.7
    tournament_size = 3
    elitism_rate = 0.1
    mutation_strategy = "swap"

# Build config
config = {
    "population_size": pop_size,
    "generations": generations,
    "mutation_prob": mutation_rate,
    "crossover_prob": crossover_rate,
    "tournament_size": tournament_size,
    "elitism_rate": elitism_rate,
    "mutation_strategy": mutation_strategy,
    "days": college_profile['working_days'],
    "time_slots": college_profile['time_slots'],
    "rooms": [r['room_code'] for r in db.get_all_infrastructure()],
    "room_capacities": {r['room_code']: r['capacity'] for r in db.get_all_infrastructure()}
}

# ==================== RUN OPTIMIZATION ====================

st.divider()

# Summary before generation
with st.expander("📊 Generation Summary", expanded=True):
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Sessions", len(entities))
    with col2:
        st.metric("Batches", len(selected_batches))
    with col3:
        st.metric("Hard Constraints", len(hard_constraints))
    with col4:
        st.metric("Soft Constraints", len(soft_constraints))

col1, col2, col3 = st.columns([1, 2, 1])

with col2:
    button_label = "🔄 Regenerate Timetable" if edit_mode else "🚀 Generate Timetable"
    
    if st.button(button_label, type="primary", use_container_width=True, disabled=st.session_state.optimization_running):
        if not schedule_title:
            st.error("❌ Please enter a timetable name")
        else:
            # Create or update schedule record
            if edit_mode:
                schedule_id = existing_schedule['id']
                # Delete old sessions
                db.delete_timetable_sessions_by_schedule(schedule_id)
                
                # Update metadata with semester info
                metadata = {
                    'num_weeks': num_weeks,
                    'start_date': str(start_date) if start_date else None,
                    'end_date': str(end_date) if end_date else None,
                    'recurring_weekly': True
                }
                description_with_meta = f"{existing_schedule.get('description', '').split('[META]')[0]}\n[META]{json.dumps(metadata)}[/META]"
                
                # Update metadata
                db.update_schedule(schedule_id, {
                    'title': schedule_title,
                    'description': description_with_meta,
                    'semester': semester,
                    'academic_year': academic_year,
                    'status': 'optimizing'
                })
            else:
                # Create metadata
                metadata = {
                    'num_weeks': num_weeks,
                    'start_date': str(start_date) if start_date else None,
                    'end_date': str(end_date) if end_date else None,
                    'recurring_weekly': True
                }
                description_with_meta = f"Timetable for {len(selected_batches)} batch(es) - Semester {semester}\n[META]{json.dumps(metadata)}[/META]"
                
                schedule_id = db.create_schedule(
                    owner_id=user['id'],
                    title=schedule_title,
                    description=description_with_meta,
                    semester=semester,
                    academic_year=academic_year
                )
            
            st.session_state.optimization_running = True
            st.session_state.current_schedule_id = schedule_id
            
            # Progress UI
            progress_container = st.container()
            
            with progress_container:
                progress_bar = st.progress(0)
                status_text = st.empty()
                
                metrics_cols = st.columns(4)
                metric_placeholders = [col.empty() for col in metrics_cols]
                
                chart_placeholder = st.empty()
                chart_data = {'generations': [], 'best': [], 'avg': []}
                
                def progress_callback(gen, best, avg, std, message):
                    """Update UI during optimization"""
                    if selected_method in ["genetic", "hybrid"]:
                        progress = min((gen / config["generations"]) * 100, 100)
                    else:
                        progress = 50
                    
                    progress_bar.progress(int(progress) / 100)
                    status_text.text(message)
                    
                    if best > 0:
                        metric_placeholders[0].metric("🎯 Best Fitness", f"{best:.2f}")
                    if avg > 0:
                        metric_placeholders[1].metric("📊 Avg Fitness", f"{avg:.2f}")
                    if gen > 0:
                        metric_placeholders[2].metric("🔄 Generation", gen)
                        metric_placeholders[3].metric("📈 Progress", f"{int(progress)}%")
                    
                    # Update chart
                    if gen > 0 and selected_method != "gemini" and gen % 10 == 0:
                        chart_data['generations'].append(gen)
                        chart_data['best'].append(best)
                        chart_data['avg'].append(avg)
                        
                        if len(chart_data['generations']) > 1:
                            fig = go.Figure()
                            fig.add_trace(go.Scatter(
                                x=chart_data['generations'],
                                y=chart_data['best'],
                                mode='lines',
                                name='Best Fitness',
                                line=dict(color='#10B981', width=3)
                            ))
                            fig.add_trace(go.Scatter(
                                x=chart_data['generations'],
                                y=chart_data['avg'],
                                mode='lines',
                                name='Average Fitness',
                                line=dict(color='#3B82F6', width=2)
                            ))
                            fig.update_layout(
                                title="Real-time Optimization Progress",
                                xaxis_title="Generation",
                                yaxis_title="Fitness Score",
                                height=350,
                                showlegend=True
                            )
                            chart_placeholder.plotly_chart(fig, use_container_width=True)
                    
                    time.sleep(0.01)
                
                try:
                    # Run optimization
                    with st.spinner("Initializing optimizer..."):
                        optimizer = HybridOptimizer(entities, all_constraints, config)
                    
                    result = optimizer.optimize(
                        method=selected_method,
                        progress_callback=progress_callback
                    )
                    
                    # Validate result
                    if not result.get('schedule') or len(result['schedule']) == 0:
                        raise Exception("Optimization failed to generate any sessions")
                    
                    progress_bar.progress(0.9)
                    status_text.text("💾 Saving timetable to database...")
                    
                    # Map result to timetable sessions
                    sessions_created = 0
                    conflicts_detected = []
                    
                    # Get infrastructure for room allocation
                    all_rooms = db.get_all_infrastructure()
                    classrooms = [r for r in all_rooms if r['room_type'] == 'Classroom']
                    labs = [r for r in all_rooms if r['room_type'] == 'Lab']
                    
                    for slot in result['schedule']:
                        # Find the entity this slot corresponds to
                        entity_id = slot.get('entity_id')
                        entity = next((e for e in entities if e['id'] == entity_id), None)
                        
                        if not entity:
                            continue
                        
                        # Find appropriate room
                        room = None
                        
                        if entity['requires_lab']:
                            # This is a lab session
                            if entity.get('preferred_lab_id'):
                                # Try preferred lab first
                                room = next((r for r in labs if r['id'] == entity['preferred_lab_id']), None)
                            
                            if not room:
                                # Find any lab with sufficient capacity
                                available_labs = [r for r in labs if r['capacity'] >= entity['capacity_needed']]
                                room = available_labs[0] if available_labs else (labs[0] if labs else None)
                        else:
                            # This is a theory class
                            available_classrooms = [r for r in classrooms if r['capacity'] >= entity['capacity_needed']]
                            room = available_classrooms[0] if available_classrooms else (classrooms[0] if classrooms else None)
                        
                        if not room:
                            continue
                        
                        # Create the session data
                        session_data = {
                            'schedule_id': schedule_id,
                            'subject_id': entity['subject_id'],
                            'batch_id': entity['batch_id'],
                            'faculty_id': entity['faculty_id'],
                            'room_id': room['id'],
                            'day_of_week': slot['day'],
                            'time_slot': slot['time'],
                            'duration': entity['duration'],
                            'session_type': entity['session_type']
                        }
                        
                        # Check for conflicts
                        check_conflicts = db.check_session_conflicts(session_data)
                        
                        if check_conflicts:
                            conflicts_detected.extend(check_conflicts)
                        
                        # Create session
                        try:
                            db.create_timetable_session(session_data)
                            sessions_created += 1
                        except Exception as e:
                            print(f"❌ Failed to create session: {e}")
                    
                    progress_bar.progress(1.0)
                    
                    # Update schedule status
                    final_status = 'finalized' if not conflicts_detected else 'draft'
                    
                    db.update_schedule(schedule_id, {
                        'status': final_status,
                        'optimization_config': json.dumps(config),
                        'optimization_history': json.dumps([{
                            'method': result['method'],
                            'fitness': result.get('fitness'),
                            'timestamp': datetime.now().isoformat(),
                            'sessions_created': sessions_created,
                            'conflicts_detected': len(conflicts_detected)
                        }])
                    })
                    
                    st.session_state.optimization_result = result
                    status_text.text("✅ Timetable Generated Successfully!")
                    
                    # Show results
                    st.divider()
                    
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("✅ Sessions Created", sessions_created)
                    with col2:
                        st.metric("📊 Total Entities", len(entities))
                    with col3:
                        success_rate = (sessions_created / len(entities) * 100) if len(entities) > 0 else 0
                        st.metric("Success Rate", f"{success_rate:.1f}%")
                    
                    if sessions_created == 0:
                        st.error("❌ No sessions were created!")
                        st.info("💡 Check: Do you have rooms/labs configured in Setup?")
                    elif sessions_created < len(entities):
                        st.warning(f"⚠️ Only {sessions_created}/{len(entities)} sessions created.")
                    else:
                        st.success(f"✅ All {sessions_created} sessions scheduled successfully!")
                    
                    if conflicts_detected:
                        st.warning(f"⚠️ {len(conflicts_detected)} conflict(s) detected.")
                        with st.expander("View Conflicts"):
                            for conflict in conflicts_detected[:10]:
                                st.error(conflict['message'])
                    
                    st.balloons()
                    
                    # Show action buttons
                    st.divider()
                    col1, col2, col3 = st.columns(3)
                    
                    with col1:
                        if st.button("👁️ View Timetable", type="primary", use_container_width=True):
                            st.session_state.view_schedule_id = schedule_id
                            st.switch_page("pages/5_View_Timetable.py")
                    
                    with col2:
                        if st.button("🔄 Regenerate", use_container_width=True):
                            db.delete_timetable_sessions_by_schedule(schedule_id)
                            st.rerun()
                    
                    with col3:
                        if st.button("🏠 Go to Dashboard", use_container_width=True):
                            st.switch_page("pages/1_Dashboard.py")
                    
                except Exception as e:
                    st.error(f"❌ Optimization failed: {str(e)}")
                    import traceback
                    with st.expander("🔍 Error Details"):
                        st.code(traceback.format_exc())
                finally:
                    st.session_state.optimization_running = False

# Footer
st.divider()
st.caption(f"Timetable Generator | {college_profile['college_name']} | Academic Year: {college_profile['academic_year']}")
st.caption(f"Mode: {selected_method.upper()} | Population: {pop_size} | Generations: {generations}")
