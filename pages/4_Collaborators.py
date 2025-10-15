import streamlit as st
from lib.database import get_database
from datetime import datetime
import time

st.set_page_config(page_title="Collaborators", page_icon="👥", layout="wide")

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
st.title("👥 Share & Collaborate")
st.markdown("Manage schedule sharing and collaborator permissions")

st.divider()

# Get user's owned schedules
user_schedules = db.get_user_schedules(user['id'])
owned_schedules = [s for s in user_schedules if s['owner_id'] == user['id']]
shared_schedules = [s for s in user_schedules if s['owner_id'] != user['id']]

# Tab layout
tab1, tab2, tab3 = st.tabs(["📤 Share Schedule", "👥 My Collaborators", "📥 Shared with Me"])

# ==================== TAB 1: SHARE SCHEDULE ====================
with tab1:
    st.markdown("### Share Your Schedule")
    
    if not owned_schedules:
        st.info("📭 You don't own any schedules to share yet")
        if st.button("➕ Create New Schedule"):
            st.switch_page("pages/2_New_Schedule.py")
    else:
        col1, col2 = st.columns([2, 1])
        
        with col1:
            # Schedule selector
            schedule_options = {s['title']: s['id'] for s in owned_schedules}
            
            # Pre-select if coming from another page
            default_index = 0
            if 'current_schedule_id' in st.session_state:
                current_id = st.session_state.current_schedule_id
                if current_id in schedule_options.values():
                    default_index = list(schedule_options.values()).index(current_id)
            
            selected_title = st.selectbox(
                "Select Schedule to Share",
                list(schedule_options.keys()),
                index=default_index,
                key="share_schedule_select"
            )
            schedule_id = schedule_options[selected_title]
            schedule = db.get_schedule(schedule_id)
        
        with col2:
            st.metric("Current Status", schedule['status'])
            st.metric("Entities", len(schedule.get('entities', [])))
        
        st.divider()
        
        # Share form
        col1, col2 = st.columns([3, 1])
        
        with col1:
            st.markdown("### 📧 Share with User")
            
            with st.form("share_form", clear_on_submit=True):
                user_email = st.text_input(
                    "User Email",
                    placeholder="Enter collaborator's email address"
                )
                
                col_a, col_b = st.columns(2)
                
                with col_a:
                    permission = st.selectbox(
                        "Permission Level",
                        ["view", "comment", "edit"],
                        help="View: Read-only | Comment: Can add notes | Edit: Full access"
                    )
                
                with col_b:
                    notify = st.checkbox("Notify user", value=True)
                
                submit = st.form_submit_button("🔗 Share Schedule", type="primary", use_container_width=True)
                
                if submit:
                    if not user_email:
                        st.error("❌ Please enter an email address")
                    else:
                        # Find target user
                        target_user = db.get_user_by_email(user_email)
                        
                        if not target_user:
                            st.error(f"❌ User with email '{user_email}' not found")
                            st.info("💡 The user must have an account in Themis first")
                        elif target_user['id'] == user['id']:
                            st.error("❌ You cannot share a schedule with yourself")
                        else:
                            # Check if already shared
                            existing = db.get_schedule_permissions(schedule_id, target_user['id'])
                            
                            if existing:
                                # Update permission
                                with db.get_connection() as conn:
                                    cursor = conn.cursor()
                                    cursor.execute("""
                                        UPDATE share_permissions
                                        SET permission = ?
                                        WHERE schedule_id = ? AND user_id = ?
                                    """, (permission, schedule_id, target_user['id']))
                                
                                st.success(f"✅ Updated sharing permissions for {user_email} to '{permission}'")
                            else:
                                # Create new share
                                db.share_schedule(schedule_id, target_user['id'], permission)
                                st.success(f"✅ Schedule shared with {user_email} ({permission} access)")
                            
                            if notify:
                                st.info(f"📧 Notification sent to {user_email}")
                            
                            st.balloons()
                            time.sleep(1)
                            st.rerun()
        
        with col2:
            st.markdown("### 🔒 Permission Levels")
            
            st.info("""
            **👁️ View**
            - Read-only access
            - Can view schedule details
            - Cannot make changes
            
            **💬 Comment**
            - Can view schedule
            - Can add comments
            - Cannot edit entities
            
            **✏️ Edit**
            - Full access to schedule
            - Can modify entities
            - Can run optimization
            - Cannot delete schedule
            """)
        
        st.divider()
        
        # Current collaborators for selected schedule
        st.markdown("### 👥 Current Collaborators")
        
        collaborators = db.get_schedule_collaborators(schedule_id)
        
        if not collaborators:
            st.info(f"📭 '{selected_title}' has not been shared with anyone yet")
        else:
            st.markdown(f"**{len(collaborators)} collaborator(s)**")
            
            for collaborator in collaborators:
                with st.expander(
                    f"👤 {collaborator['username']} ({collaborator['email']}) - {collaborator['permission'].upper()}",
                    expanded=True
                ):
                    col1, col2, col3 = st.columns([2, 1, 1])
                    
                    with col1:
                        st.write(f"**Username:** {collaborator['username']}")
                        st.write(f"**Email:** {collaborator['email']}")
                        st.caption(f"Shared on: {collaborator['shared_at'][:19]}")
                    
                    with col2:
                        # Change permission
                        new_permission = st.selectbox(
                            "Change Permission",
                            ["view", "comment", "edit"],
                            index=["view", "comment", "edit"].index(collaborator['permission']),
                            key=f"perm_{schedule_id}_{collaborator['id']}"
                        )
                        
                        if new_permission != collaborator['permission']:
                            if st.button("Update", key=f"update_{schedule_id}_{collaborator['id']}"):
                                with db.get_connection() as conn:
                                    cursor = conn.cursor()
                                    cursor.execute("""
                                        UPDATE share_permissions
                                        SET permission = ?
                                        WHERE schedule_id = ? AND user_id = ?
                                    """, (new_permission, schedule_id, collaborator['id']))
                                
                                st.success("Permission updated!")
                                time.sleep(1)
                                st.rerun()
                    
                    with col3:
                        # Remove access
                        if st.button(
                            "🗑️ Remove Access",
                            key=f"remove_{schedule_id}_{collaborator['id']}",
                            type="secondary"
                        ):
                            with db.get_connection() as conn:
                                cursor = conn.cursor()
                                cursor.execute("""
                                    DELETE FROM share_permissions
                                    WHERE schedule_id = ? AND user_id = ?
                                """, (schedule_id, collaborator['id']))
                            
                            st.success(f"Removed access for {collaborator['email']}")
                            time.sleep(1)
                            st.rerun()
        
        st.divider()
        
        # Quick share link (placeholder for future feature)
        st.markdown("### 🔗 Share Link")
        
        col1, col2 = st.columns([3, 1])
        
        with col1:
            share_link = f"https://themis.app/schedule/{schedule_id}"
            st.text_input(
                "Public Link",
                value=share_link,
                disabled=True,
                help="Feature coming soon: Generate public sharing links"
            )
        
        with col2:
            if st.button("📋 Copy Link", disabled=True):
                st.info("🚧 Coming soon!")

# ==================== TAB 2: MY COLLABORATORS ====================
with tab2:
    st.markdown("### My Collaborators Overview")
    
    if not owned_schedules:
        st.info("📭 You don't own any schedules yet")
    else:
        # Aggregate all collaborators across user's schedules
        all_collaborators = {}
        
        for schedule in owned_schedules:
            collaborators = db.get_schedule_collaborators(schedule['id'])
            
            for collab in collaborators:
                user_email = collab['email']
                
                if user_email not in all_collaborators:
                    all_collaborators[user_email] = {
                        'username': collab['username'],
                        'email': collab['email'],
                        'user_id': collab['id'],
                        'schedules': []
                    }
                
                all_collaborators[user_email]['schedules'].append({
                    'title': schedule['title'],
                    'id': schedule['id'],
                    'permission': collab['permission']
                })
        
        if not all_collaborators:
            st.info("📭 You haven't shared any schedules with collaborators yet")
        else:
            st.metric("👥 Total Collaborators", len(all_collaborators))
            
            st.divider()
            
            # Display each collaborator
            for email, collab_data in all_collaborators.items():
                with st.expander(
                    f"👤 {collab_data['username']} ({email}) - {len(collab_data['schedules'])} schedule(s)",
                    expanded=False
                ):
                    st.markdown(f"**Shared Schedules:**")
                    
                    for sched in collab_data['schedules']:
                        col1, col2, col3 = st.columns([3, 1, 1])
                        
                        with col1:
                            st.write(f"📅 {sched['title']}")
                        
                        with col2:
                            st.caption(f"Permission: {sched['permission']}")
                        
                        with col3:
                            if st.button(
                                "Remove",
                                key=f"remove_collab_{sched['id']}_{collab_data['user_id']}",
                                type="secondary"
                            ):
                                with db.get_connection() as conn:
                                    cursor = conn.cursor()
                                    cursor.execute("""
                                        DELETE FROM share_permissions
                                        WHERE schedule_id = ? AND user_id = ?
                                    """, (sched['id'], collab_data['user_id']))
                                
                                st.success("Access removed")
                                time.sleep(1)
                                st.rerun()
                    
                    st.divider()
                    
                    # Bulk actions
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        if st.button(
                            f"🗑️ Remove from All Schedules",
                            key=f"remove_all_{collab_data['user_id']}",
                            type="secondary"
                        ):
                            with db.get_connection() as conn:
                                cursor = conn.cursor()
                                for sched in collab_data['schedules']:
                                    cursor.execute("""
                                        DELETE FROM share_permissions
                                        WHERE schedule_id = ? AND user_id = ?
                                    """, (sched['id'], collab_data['user_id']))
                            
                            st.success(f"Removed {email} from all schedules")
                            time.sleep(1)
                            st.rerun()

# ==================== TAB 3: SHARED WITH ME ====================
with tab3:
    st.markdown("### Schedules Shared With Me")
    
    if not shared_schedules:
        st.info("📭 No schedules have been shared with you yet")
    else:
        st.metric("🔗 Shared Schedules", len(shared_schedules))
        
        st.divider()
        
        # Display shared schedules
        for schedule in shared_schedules:
            # Get owner info
            owner = db.get_user_by_id(schedule['owner_id'])
            owner_name = owner['username'] if owner else "Unknown"
            owner_email = owner['email'] if owner else "N/A"
            
            # Get my permission
            my_permission = db.get_schedule_permissions(schedule['id'], user['id'])
            
            with st.expander(
                f"📅 {schedule['title']} (by {owner_name}) - {my_permission.upper() if my_permission else 'VIEW'}",
                expanded=True
            ):
                col1, col2, col3 = st.columns([2, 1, 1])
                
                with col1:
                    st.write(f"**Title:** {schedule['title']}")
                    st.write(f"**Description:** {schedule.get('description', 'No description')}")
                    st.write(f"**Owner:** {owner_name} ({owner_email})")
                
                with col2:
                    st.metric("Status", schedule['status'])
                    st.metric("Entities", len(schedule.get('entities', [])))
                    st.metric("Constraints", len(schedule.get('constraints', [])))
                
                with col3:
                    st.write(f"**My Access:** {my_permission.upper() if my_permission else 'VIEW'}")
                    st.caption(f"Created: {schedule['created_at'][:10]}")
                    st.caption(f"Updated: {schedule['updated_at'][:10]}")
                
                st.divider()
                
                # Actions based on permission
                col1, col2, col3, col4 = st.columns(4)
                
                with col1:
                    if st.button("👁️ View Details", key=f"view_shared_{schedule['id']}", use_container_width=True):
                        st.session_state.current_schedule_id = schedule['id']
                        st.switch_page("pages/3_Optimizer.py")
                
                with col2:
                    if my_permission in ['edit']:
                        if st.button("✏️ Edit", key=f"edit_shared_{schedule['id']}", use_container_width=True):
                            st.session_state.current_schedule_id = schedule['id']
                            st.switch_page("pages/2_New_Schedule.py")
                    else:
                        st.button("✏️ Edit", disabled=True, use_container_width=True, help="You need edit permission")
                
                with col3:
                    if my_permission in ['edit']:
                        if st.button("🔧 Optimize", key=f"optimize_shared_{schedule['id']}", use_container_width=True):
                            st.session_state.current_schedule_id = schedule['id']
                            st.switch_page("pages/3_Optimizer.py")
                    else:
                        st.button("🔧 Optimize", disabled=True, use_container_width=True, help="You need edit permission")
                
                with col4:
                    if st.button("❌ Leave", key=f"leave_shared_{schedule['id']}", type="secondary", use_container_width=True):
                        # Remove self from shared schedule
                        with db.get_connection() as conn:
                            cursor = conn.cursor()
                            cursor.execute("""
                                DELETE FROM share_permissions
                                WHERE schedule_id = ? AND user_id = ?
                            """, (schedule['id'], user['id']))
                        
                        st.success("You have left this schedule")
                        time.sleep(1)
                        st.rerun()

# Statistics sidebar
with st.sidebar:
    st.markdown("### 📊 Collaboration Stats")
    
    # Count total shares
    total_shared_by_me = 0
    for schedule in owned_schedules:
        collaborators = db.get_schedule_collaborators(schedule['id'])
        total_shared_by_me += len(collaborators)
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.metric("Shared by Me", total_shared_by_me)
    
    with col2:
        st.metric("Shared with Me", len(shared_schedules))
    
    st.divider()
    
    st.markdown("### 🎯 Quick Actions")
    
    if st.button("📤 Share New Schedule", use_container_width=True):
        if owned_schedules:
            st.rerun()
        else:
            st.info("Create a schedule first!")
    
    if st.button("📊 View Dashboard", use_container_width=True):
        st.switch_page("pages/1_Dashboard.py")
    
    st.divider()
    
    st.markdown("### 💡 Tips")
    st.caption("""
    • **View** access is read-only
    
    • **Comment** allows feedback
    
    • **Edit** grants full control
    
    • Remove access anytime
    
    • Collaborators are notified of changes
    """)

# Footer
st.divider()
col1, col2 = st.columns(2)

with col1:
    st.caption(f"User: {user['username']} ({user['email']})")

with col2:
    st.caption(f"Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
