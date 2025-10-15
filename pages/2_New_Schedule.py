import streamlit as st
from lib.database import get_database
import uuid
import json
from datetime import datetime

st.set_page_config(page_title="New Schedule", page_icon="✨", layout="wide")

# Check authentication
if not st.session_state.get("authenticated"):
    st.warning("⚠️ Please login first")
    st.stop()

# Update activity
if 'last_activity' in st.session_state:
    st.session_state.last_activity = datetime.now()

db = get_database()
user = st.session_state.user

# Initialize session state for form data
if 'form_entities' not in st.session_state:
    st.session_state.form_entities = []
if 'form_constraints' not in st.session_state:
    st.session_state.form_constraints = []
if 'edit_mode' not in st.session_state:
    st.session_state.edit_mode = False

# Check if editing existing schedule
edit_schedule_id = st.session_state.get('current_schedule_id')
if edit_schedule_id and not st.session_state.edit_mode:
    schedule = db.get_schedule(edit_schedule_id)
    if schedule:
        st.session_state.edit_mode = True
        st.session_state.edit_schedule = schedule
        st.session_state.form_entities = schedule.get('entities', [])
        st.session_state.form_constraints = schedule.get('constraints', [])

# Header
if st.session_state.edit_mode:
    st.title("✏️ Edit Schedule")
    st.markdown(f"Editing: **{st.session_state.edit_schedule['title']}**")
else:
    st.title("✨ Create New Schedule")
    st.markdown("Build your scheduling project with entities and constraints")

# Reset button
if st.button("🔄 Start Fresh"):
    st.session_state.form_entities = []
    st.session_state.form_constraints = []
    st.session_state.edit_mode = False
    if 'current_schedule_id' in st.session_state:
        del st.session_state.current_schedule_id
    if 'edit_schedule' in st.session_state:
        del st.session_state.edit_schedule
    st.rerun()

st.divider()

# Main form
with st.form("schedule_form", clear_on_submit=False):
    st.markdown("### 📋 Basic Information")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        default_title = st.session_state.edit_schedule['title'] if st.session_state.edit_mode else ""
        title = st.text_input(
            "Schedule Title *",
            value=default_title,
            placeholder="e.g., Fall 2025 Course Timetable"
        )
    
    with col2:
        default_status = st.session_state.edit_schedule['status'] if st.session_state.edit_mode else "draft"
        status = st.selectbox("Status", ["draft", "optimizing", "finalized"], 
                             index=["draft", "optimizing", "finalized"].index(default_status))
    
    default_desc = st.session_state.edit_schedule.get('description', '') if st.session_state.edit_mode else ""
    description = st.text_area(
        "Description",
        value=default_desc,
        placeholder="Add details about this schedule..."
    )
    
    st.divider()
    
    # Entity management
    st.markdown("### 🎯 Entities (Classes, Meetings, Resources)")
    
    col1, col2 = st.columns([3, 1])
    
    with col1:
        st.info("Entities are the items you want to schedule (e.g., classes, meetings, appointments)")
    
    with col2:
        num_entities = st.number_input("Number of entities", min_value=0, max_value=100, value=5)
    
    # Entity input
    entities = []
    
    if num_entities > 0:
        st.markdown("#### Define Your Entities")
        
        for i in range(num_entities):
            with st.expander(f"Entity {i+1}", expanded=(i < 3)):
                col1, col2, col3 = st.columns([3, 2, 2])
                
                # Get default values if editing
                default_entity = st.session_state.form_entities[i] if i < len(st.session_state.form_entities) else {}
                
                with col1:
                    name = st.text_input(
                        "Name *",
                        value=default_entity.get('name', ''),
                        key=f"entity_name_{i}",
                        placeholder="e.g., Math 101"
                    )
                
                with col2:
                    duration = st.number_input(
                        "Duration (hours)",
                        min_value=1,
                        max_value=8,
                        value=default_entity.get('duration', 2),
                        key=f"entity_dur_{i}"
                    )
                
                with col3:
                    entity_type = st.selectbox(
                        "Type",
                        ["class", "meeting", "lab", "seminar", "workshop", "other"],
                        index=["class", "meeting", "lab", "seminar", "workshop", "other"].index(
                            default_entity.get('type', 'class')
                        ),
                        key=f"entity_type_{i}"
                    )
                
                col1, col2 = st.columns(2)
                
                with col1:
                    capacity = st.number_input(
                        "Required Capacity",
                        min_value=0,
                        max_value=500,
                        value=default_entity.get('capacity_needed', 30),
                        key=f"entity_cap_{i}"
                    )
                
                with col2:
                    instructor = st.text_input(
                        "Instructor/Owner",
                        value=default_entity.get('instructor', ''),
                        key=f"entity_inst_{i}",
                        placeholder="Optional"
                    )
                
                if name:
                    entity_id = default_entity.get('id', f"entity_{uuid.uuid4().hex[:8]}")
                    entities.append({
                        "id": entity_id,
                        "name": name,
                        "duration": duration,
                        "type": entity_type,
                        "capacity_needed": capacity,
                        "instructor": instructor
                    })
    
    st.divider()
    
    # Constraint management
    st.markdown("### ⚙️ Constraints & Rules")
    
    st.info("Constraints define rules and preferences for your schedule optimization")
    
    # Predefined constraint types
    st.markdown("#### Select Constraint Types")
    
    col1, col2 = st.columns(2)
    
    with col1:
        hard_constraints = st.multiselect(
            "Hard Constraints (Must be satisfied)",
            ["no_overlap", "room_capacity", "availability", "instructor_conflict"],
            default=["no_overlap", "room_capacity"]
        )
    
    with col2:
        soft_constraints = st.multiselect(
            "Soft Constraints (Preferences)",
            ["preferred_time", "balanced_distribution", "consecutive_slots", "minimize_gaps"],
            default=["balanced_distribution"]
        )
    
    # Build constraints list
    constraints = []
    
    # Hard constraints
    for constraint_type in hard_constraints:
        if constraint_type == "no_overlap":
            constraints.append({
                "type": "no_overlap",
                "description": "No two entities in the same room at the same time",
                "weight": 100,
                "hard": True
            })
        elif constraint_type == "room_capacity":
            constraints.append({
                "type": "room_capacity",
                "description": "Room capacity must meet entity requirements",
                "weight": 80,
                "hard": True
            })
        elif constraint_type == "availability":
            constraints.append({
                "type": "availability",
                "description": "Respect entity availability constraints",
                "weight": 90,
                "hard": True
            })
        elif constraint_type == "instructor_conflict":
            constraints.append({
                "type": "instructor_conflict",
                "description": "Same instructor cannot teach multiple classes at once",
                "weight": 95,
                "hard": True
            })
    
    # Soft constraints
    for constraint_type in soft_constraints:
        if constraint_type == "preferred_time":
            constraints.append({
                "type": "preferred_time",
                "description": "Schedule entities at preferred times when possible",
                "weight": 20,
                "hard": False
            })
        elif constraint_type == "balanced_distribution":
            constraints.append({
                "type": "balanced_distribution",
                "description": "Distribute sessions evenly across days",
                "weight": 30,
                "hard": False
            })
        elif constraint_type == "consecutive_slots":
            constraints.append({
                "type": "consecutive_slots",
                "description": "Group related sessions together",
                "weight": 15,
                "hard": False
            })
        elif constraint_type == "minimize_gaps":
            constraints.append({
                "type": "minimize_gaps",
                "description": "Reduce idle time between sessions",
                "weight": 10,
                "hard": False
            })
    
    # Custom constraints
    st.markdown("#### Custom Constraints (Optional)")
    
    add_custom = st.checkbox("Add custom constraint")
    
    if add_custom:
        col1, col2, col3 = st.columns([3, 1, 1])
        
        with col1:
            custom_desc = st.text_input("Constraint Description")
        
        with col2:
            custom_weight = st.number_input("Weight", min_value=1, max_value=100, value=20)
        
        with col3:
            custom_hard = st.checkbox("Hard Constraint", value=False)
        
        if custom_desc:
            constraints.append({
                "type": "custom",
                "description": custom_desc,
                "weight": custom_weight,
                "hard": custom_hard
            })
    
    st.divider()
    
    # Configuration options
    st.markdown("### 🔧 Advanced Configuration")
    
    with st.expander("Time & Resource Settings", expanded=False):
        col1, col2 = st.columns(2)
        
        with col1:
            days = st.multiselect(
                "Available Days",
                ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"],
                default=["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
            )
        
        with col2:
            time_slots = st.multiselect(
                "Time Slots (select at least 5)",
                ["08:00", "09:00", "10:00", "11:00", "12:00", "13:00", "14:00", 
                 "15:00", "16:00", "17:00", "18:00", "19:00", "20:00"],
                default=["08:00", "09:00", "10:00", "11:00", "12:00", "13:00", 
                        "14:00", "15:00", "16:00", "17:00"]
            )
        
        rooms_input = st.text_input(
            "Rooms (comma-separated)",
            value="R101, R102, R103, R104, R105",
            help="Enter room names separated by commas"
        )
        
        rooms = [r.strip() for r in rooms_input.split(",") if r.strip()]
        
        # Room capacities
        st.markdown("**Room Capacities** (optional)")
        room_capacities = {}
        
        cols = st.columns(min(len(rooms), 5))
        for idx, room in enumerate(rooms[:10]):  # Limit to 10 rooms for UI
            with cols[idx % 5]:
                capacity = st.number_input(
                    f"{room}",
                    min_value=10,
                    max_value=500,
                    value=50,
                    key=f"room_cap_{room}"
                )
                room_capacities[room] = capacity
    
    # Submit buttons
    st.divider()
    
    col1, col2, col3 = st.columns([1, 1, 2])
    
    with col1:
        submit = st.form_submit_button("💾 Save Schedule", type="primary", use_container_width=True)
    
    with col2:
        save_and_optimize = st.form_submit_button("🚀 Save & Optimize", use_container_width=True)
    
    # Form submission
    if submit or save_and_optimize:
        # Validation
        if not title:
            st.error("❌ Please enter a schedule title")
        elif not entities:
            st.error("❌ Please add at least one entity")
        elif not days or not time_slots or not rooms:
            st.error("❌ Please configure days, time slots, and rooms")
        else:
            # Prepare configuration
            config = {
                "days": days,
                "time_slots": time_slots,
                "rooms": rooms,
                "room_capacities": room_capacities
            }
            
            # Save or update schedule
            if st.session_state.edit_mode:
                # Update existing schedule
                updates = {
                    "title": title,
                    "description": description,
                    "status": status,
                    "entities": json.dumps(entities),
                    "constraints": json.dumps(constraints)
                }
                
                db.update_schedule(edit_schedule_id, updates)
                st.success(f"✅ Schedule '{title}' updated successfully!")
                
                # Save version
                db.save_version(edit_schedule_id, user['id'], "Manual update via edit form")
                
                schedule_id = edit_schedule_id
            else:
                # Create new schedule
                schedule_id = db.create_schedule(user['id'], title, description)
                
                # Update with entities and constraints
                updates = {
                    "entities": json.dumps(entities),
                    "constraints": json.dumps(constraints),
                    "status": status
                }
                
                db.update_schedule(schedule_id, updates)
                st.success(f"✅ Schedule '{title}' created successfully!")
            
            # Clear cache
            st.cache_data.clear()
            
            # Show confetti
            st.balloons()
            
            # Clear form state
            st.session_state.form_entities = []
            st.session_state.form_constraints = []
            st.session_state.edit_mode = False
            if 'edit_schedule' in st.session_state:
                del st.session_state.edit_schedule
            
            # Navigate based on button clicked
            if save_and_optimize:
                st.session_state.current_schedule_id = schedule_id
                st.info("🚀 Redirecting to optimizer...")
                st.switch_page("pages/3_Optimizer.py")
            else:
                col1, col2 = st.columns(2)
                
                with col1:
                    if st.button("📊 Go to Dashboard", use_container_width=True):
                        st.switch_page("pages/1_Dashboard.py")
                
                with col2:
                    if st.button("🔧 Optimize Now", use_container_width=True):
                        st.session_state.current_schedule_id = schedule_id
                        st.switch_page("pages/3_Optimizer.py")

# Summary sidebar
with st.sidebar:
    st.markdown("### 📊 Schedule Summary")
    
    if entities:
        st.metric("Entities Defined", len(entities))
        
        # Entity types breakdown
        entity_types = {}
        for entity in entities:
            etype = entity.get('type', 'unknown')
            entity_types[etype] = entity_types.get(etype, 0) + 1
        
        st.markdown("**By Type:**")
        for etype, count in entity_types.items():
            st.caption(f"• {etype.title()}: {count}")
    else:
        st.info("No entities added yet")
    
    st.divider()
    
    if constraints:
        st.metric("Constraints", len(constraints))
        
        hard_count = len([c for c in constraints if c.get('hard', False)])
        soft_count = len([c for c in constraints if not c.get('hard', False)])
        
        st.caption(f"• Hard: {hard_count}")
        st.caption(f"• Soft: {soft_count}")
    else:
        st.info("No constraints selected")
    
    st.divider()
    
    st.markdown("### 💡 Tips")
    st.caption("""
    • Add more entities for complex schedules
    
    • Balance hard and soft constraints
    
    • Configure room capacities for better optimization
    
    • Use custom constraints for special requirements
    """)

# Footer
st.divider()
st.caption("All changes are saved to the database automatically")
