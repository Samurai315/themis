import streamlit as st
from lib.database import get_database
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime

st.set_page_config(page_title="Dashboard", page_icon="📊", layout="wide")

# Check authentication
if not st.session_state.get("authenticated"):
    st.warning("⚠️ Please login first")
    st.stop()

# Update activity
if 'last_activity' in st.session_state:
    st.session_state.last_activity = datetime.now()

db = get_database()
user = st.session_state.user

# Cache function for schedules
@st.cache_data(ttl=300)
def get_cached_schedules(user_id, cache_key):
    """Get user schedules with caching"""
    return db.get_user_schedules(user_id)

def clear_cache():
    """Clear dashboard cache"""
    st.cache_data.clear()
    if 'cache_timestamp' in st.session_state:
        st.session_state.cache_timestamp = datetime.now()

# Header
st.title("📊 Schedule Dashboard")
st.markdown(f"Welcome back, **{user['username']}**!")

# Refresh button
col1, col2, col3 = st.columns([2, 1, 1])
with col3:
    if st.button("🔄 Refresh Data", use_container_width=True):
        clear_cache()
        st.rerun()

st.divider()

# Get schedules
cache_key = st.session_state.get('cache_timestamp', datetime.now())
schedules = get_cached_schedules(user['id'], cache_key)

# Statistics
owned_schedules = [s for s in schedules if s['owner_id'] == user['id']]
shared_schedules = [s for s in schedules if s['owner_id'] != user['id']]

col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric("📁 Total Schedules", len(schedules))

with col2:
    draft_count = len([s for s in schedules if s['status'] == 'draft'])
    st.metric("🟡 Draft", draft_count)

with col3:
    finalized_count = len([s for s in schedules if s['status'] == 'finalized'])
    st.metric("🟢 Finalized", finalized_count)

with col4:
    st.metric("🔗 Shared with Me", len(shared_schedules))

st.divider()

# Filters and Search
col1, col2, col3 = st.columns([3, 2, 2])

with col1:
    search_query = st.text_input("🔍 Search schedules", placeholder="Search by title or description...")

with col2:
    status_filter = st.selectbox(
        "Filter by Status",
        ["All", "draft", "optimizing", "finalized"]
    )

with col3:
    view_filter = st.selectbox(
        "View",
        ["All Schedules", "My Schedules", "Shared with Me"]
    )

# Apply filters
filtered_schedules = schedules

# Search filter
if search_query:
    filtered_schedules = [
        s for s in filtered_schedules
        if search_query.lower() in s['title'].lower() 
        or search_query.lower() in s.get('description', '').lower()
    ]

# Status filter
if status_filter != "All":
    filtered_schedules = [s for s in filtered_schedules if s['status'] == status_filter]

# View filter
if view_filter == "My Schedules":
    filtered_schedules = [s for s in filtered_schedules if s['owner_id'] == user['id']]
elif view_filter == "Shared with Me":
    filtered_schedules = [s for s in filtered_schedules if s['owner_id'] != user['id']]

# Sort options
sort_by = st.radio(
    "Sort by:",
    ["Recent", "Oldest", "Title A-Z", "Title Z-A", "Most Entities"],
    horizontal=True
)

if sort_by == "Recent":
    filtered_schedules.sort(key=lambda x: x['updated_at'], reverse=True)
elif sort_by == "Oldest":
    filtered_schedules.sort(key=lambda x: x['updated_at'])
elif sort_by == "Title A-Z":
    filtered_schedules.sort(key=lambda x: x['title'])
elif sort_by == "Title Z-A":
    filtered_schedules.sort(key=lambda x: x['title'], reverse=True)
elif sort_by == "Most Entities":
    filtered_schedules.sort(key=lambda x: len(x.get('entities', [])), reverse=True)

st.markdown(f"**Showing {len(filtered_schedules)} schedule(s)**")
st.divider()

# Display schedules
if not filtered_schedules:
    st.info("📭 No schedules found. Create your first schedule to get started!")
    
    if st.button("➕ Create New Schedule", type="primary"):
        st.switch_page("pages/2_New_Schedule.py")
else:
    # View mode selection
    view_mode = st.radio("View Mode:", ["Grid View", "List View", "Table View"], horizontal=True)
    
    if view_mode == "Grid View":
        # Grid view with cards
        cols_per_row = 3
        for i in range(0, len(filtered_schedules), cols_per_row):
            cols = st.columns(cols_per_row)
            
            for j in range(cols_per_row):
                if i + j < len(filtered_schedules):
                    schedule = filtered_schedules[i + j]
                    
                    with cols[j]:
                        # Status color coding
                        status_colors = {
                            "draft": "🟡",
                            "optimizing": "🟠",
                            "finalized": "🟢"
                        }
                        
                        # Card container
                        with st.container():
                            st.markdown(f"### {status_colors.get(schedule['status'], '⚪')} {schedule['title']}")
                            
                            # Owner badge
                            if schedule['owner_id'] != user['id']:
                                st.caption("🔗 Shared with you")
                            
                            st.caption(schedule.get('description', 'No description')[:100] + 
                                     ('...' if len(schedule.get('description', '')) > 100 else ''))
                            
                            col_a, col_b = st.columns(2)
                            with col_a:
                                st.metric("Entities", len(schedule.get('entities', [])))
                            with col_b:
                                st.metric("Constraints", len(schedule.get('constraints', [])))
                            
                            st.caption(f"Updated: {schedule['updated_at'][:10]}")
                            
                            # Action buttons
                            col1, col2, col3 = st.columns(3)
                            with col1:
                                if st.button("👁️", key=f"view_{schedule['id']}", 
                                           help="View", use_container_width=True):
                                    st.session_state.current_schedule_id = schedule['id']
                                    st.switch_page("pages/3_Optimizer.py")
                            
                            with col2:
                                if st.button("✏️", key=f"edit_{schedule['id']}", 
                                           help="Edit", use_container_width=True):
                                    st.session_state.current_schedule_id = schedule['id']
                                    st.switch_page("pages/2_New_Schedule.py")
                            
                            with col3:
                                if schedule['owner_id'] == user['id']:
                                    if st.button("🗑️", key=f"del_{schedule['id']}", 
                                               help="Delete", use_container_width=True):
                                        db.delete_schedule(schedule['id'])
                                        clear_cache()
                                        st.rerun()
                            
                            st.divider()
    
    elif view_mode == "List View":
        # List view with expandable items
        for schedule in filtered_schedules:
            status_colors = {
                "draft": "🟡",
                "optimizing": "🟠",
                "finalized": "🟢"
            }
            
            with st.expander(f"{status_colors.get(schedule['status'], '⚪')} {schedule['title']}", expanded=False):
                col1, col2, col3 = st.columns([2, 1, 1])
                
                with col1:
                    st.markdown("**Description:**")
                    st.write(schedule.get('description', 'No description'))
                    
                    if schedule['owner_id'] != user['id']:
                        st.caption("🔗 Shared with you")
                
                with col2:
                    st.metric("Entities", len(schedule.get('entities', [])))
                    st.metric("Constraints", len(schedule.get('constraints', [])))
                    st.metric("Slots", len(schedule.get('slots', [])))
                
                with col3:
                    st.write(f"**Status:** {schedule['status']}")
                    st.write(f"**Created:** {schedule['created_at'][:10]}")
                    st.write(f"**Updated:** {schedule['updated_at'][:10]}")
                
                st.divider()
                
                # Actions
                col1, col2, col3, col4 = st.columns(4)
                
                with col1:
                    if st.button("👁️ View Details", key=f"view_{schedule['id']}", use_container_width=True):
                        st.session_state.current_schedule_id = schedule['id']
                        st.switch_page("pages/3_Optimizer.py")
                
                with col2:
                    if st.button("✏️ Edit", key=f"edit_{schedule['id']}", use_container_width=True):
                        st.session_state.current_schedule_id = schedule['id']
                        st.switch_page("pages/2_New_Schedule.py")
                
                with col3:
                    if st.button("👥 Share", key=f"share_{schedule['id']}", use_container_width=True):
                        st.session_state.current_schedule_id = schedule['id']
                        st.switch_page("pages/4_Collaborators.py")
                
                with col4:
                    if schedule['owner_id'] == user['id']:
                        if st.button("🗑️ Delete", key=f"del_{schedule['id']}", 
                                   type="secondary", use_container_width=True):
                            db.delete_schedule(schedule['id'])
                            clear_cache()
                            st.success("Schedule deleted!")
                            st.rerun()
    
    else:  # Table View
        # Prepare table data
        table_data = []
        for schedule in filtered_schedules:
            table_data.append({
                'Title': schedule['title'],
                'Status': schedule['status'],
                'Entities': len(schedule.get('entities', [])),
                'Constraints': len(schedule.get('constraints', [])),
                'Slots': len(schedule.get('slots', [])),
                'Updated': schedule['updated_at'][:10],
                'Owner': 'Me' if schedule['owner_id'] == user['id'] else 'Shared',
                'ID': schedule['id']
            })
        
        df = pd.DataFrame(table_data)
        
        # Display table without ID column
        display_df = df.drop('ID', axis=1)
        st.dataframe(display_df, use_container_width=True, hide_index=True)
        
        # Action selector
        st.markdown("### Quick Actions")
        selected_title = st.selectbox("Select schedule", df['Title'].tolist())
        
        if selected_title:
            selected_id = df[df['Title'] == selected_title]['ID'].values[0]
            
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                if st.button("👁️ View", use_container_width=True):
                    st.session_state.current_schedule_id = selected_id
                    st.switch_page("pages/3_Optimizer.py")
            
            with col2:
                if st.button("✏️ Edit", use_container_width=True):
                    st.session_state.current_schedule_id = selected_id
                    st.switch_page("pages/2_New_Schedule.py")
            
            with col3:
                if st.button("👥 Share", use_container_width=True):
                    st.session_state.current_schedule_id = selected_id
                    st.switch_page("pages/4_Collaborators.py")
            
            with col4:
                schedule = next((s for s in filtered_schedules if s['id'] == selected_id), None)
                if schedule and schedule['owner_id'] == user['id']:
                    if st.button("🗑️ Delete", type="secondary", use_container_width=True):
                        db.delete_schedule(selected_id)
                        clear_cache()
                        st.rerun()

# Analytics section
if schedules:
    st.divider()
    st.markdown("## 📈 Analytics")
    
    tab1, tab2, tab3 = st.tabs(["Status Distribution", "Timeline", "Activity"])
    
    with tab1:
        # Status distribution pie chart
        status_counts = {}
        for schedule in schedules:
            status = schedule['status']
            status_counts[status] = status_counts.get(status, 0) + 1
        
        fig = px.pie(
            values=list(status_counts.values()),
            names=list(status_counts.keys()),
            title="Schedule Status Distribution",
            color_discrete_map={
                'draft': '#FCD34D',
                'optimizing': '#FB923C',
                'finalized': '#4ADE80'
            }
        )
        st.plotly_chart(fig, use_container_width=True)
    
    with tab2:
        # Timeline of schedule creation
        timeline_data = []
        for schedule in schedules:
            timeline_data.append({
                'Date': schedule['created_at'][:10],
                'Title': schedule['title'],
                'Status': schedule['status']
            })
        
        if timeline_data:
            df_timeline = pd.DataFrame(timeline_data)
            df_timeline['Count'] = 1
            df_grouped = df_timeline.groupby('Date').sum().reset_index()
            
            fig = px.line(
                df_grouped,
                x='Date',
                y='Count',
                title='Schedules Created Over Time',
                markers=True
            )
            st.plotly_chart(fig, use_container_width=True)
    
    with tab3:
        # Entity and constraint statistics
        total_entities = sum(len(s.get('entities', [])) for s in schedules)
        total_constraints = sum(len(s.get('constraints', [])) for s in schedules)
        total_slots = sum(len(s.get('slots', [])) for s in schedules)
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Entities Scheduled", total_entities)
        with col2:
            st.metric("Total Constraints Applied", total_constraints)
        with col3:
            st.metric("Total Time Slots Allocated", total_slots)
        
        # Average metrics
        if schedules:
            avg_entities = total_entities / len(schedules)
            avg_constraints = total_constraints / len(schedules)
            
            col1, col2 = st.columns(2)
            with col1:
                st.metric("Avg Entities per Schedule", f"{avg_entities:.1f}")
            with col2:
                st.metric("Avg Constraints per Schedule", f"{avg_constraints:.1f}")

# Footer
st.divider()
col1, col2 = st.columns(2)
with col1:
    st.caption(f"Last refreshed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
with col2:
    st.caption(f"Showing data for user: {user['email']}")
