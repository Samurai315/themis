import streamlit as st
from lib.database import get_database
import bcrypt
from datetime import datetime, timedelta
import time

# Page configuration
st.set_page_config(
    page_title="Themis - AI Schedule Optimizer",
    page_icon="⚖️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize database with caching
db = get_database()

# Session state initialization
def init_session_state():
    """Initialize all session state variables"""
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False
    if "user" not in st.session_state:
        st.session_state.user = None
    if "login_attempts" not in st.session_state:
        st.session_state.login_attempts = 0
    if "last_activity" not in st.session_state:
        st.session_state.last_activity = datetime.now()
    if "session_id" not in st.session_state:
        st.session_state.session_id = None
    if "cache_timestamp" not in st.session_state:
        st.session_state.cache_timestamp = datetime.now()

init_session_state()

# Session timeout configuration
SESSION_TIMEOUT_MINUTES = 30

# Cached user data
@st.cache_data(ttl=300)  # Cache for 5 minutes
def get_cached_user_schedules(user_id, cache_key):
    """Get user schedules with caching"""
    return db.get_user_schedules(user_id)

@st.cache_data(ttl=600)  # Cache for 10 minutes
def get_cached_schedule(schedule_id, cache_key):
    """Get specific schedule with caching"""
    return db.get_schedule(schedule_id)

@st.cache_data(ttl=3600)  # Cache for 1 hour
def get_system_stats(cache_key):
    """Get system statistics with caching"""
    with db.get_connection() as conn:
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(*) as count FROM users")
        total_users = cursor.fetchone()['count']
        
        cursor.execute("SELECT COUNT(*) as count FROM schedules")
        total_schedules = cursor.fetchone()['count']
        
        cursor.execute("SELECT COUNT(*) as count FROM schedules WHERE status='finalized'")
        finalized_schedules = cursor.fetchone()['count']
        
        cursor.execute("SELECT COUNT(*) as count FROM share_permissions")
        total_shares = cursor.fetchone()['count']
        
        return {
            'total_users': total_users,
            'total_schedules': total_schedules,
            'finalized_schedules': finalized_schedules,
            'total_shares': total_shares
        }

def clear_user_cache():
    """Clear user-specific cache"""
    st.session_state.cache_timestamp = datetime.now()

def check_session_timeout():
    """Check if session has timed out"""
    if st.session_state.authenticated:
        time_elapsed = datetime.now() - st.session_state.last_activity
        if time_elapsed > timedelta(minutes=SESSION_TIMEOUT_MINUTES):
            logout()
            st.warning(f"Session timed out after {SESSION_TIMEOUT_MINUTES} minutes of inactivity")
            return True
    return False

def update_activity():
    """Update last activity timestamp"""
    st.session_state.last_activity = datetime.now()

def authenticate(email, password):
    """Authenticate user with rate limiting"""
    # Rate limiting
    if st.session_state.login_attempts >= 5:
        st.error("Too many login attempts. Please wait 5 minutes.")
        return False
    
    user = db.get_user_by_email(email)
    if user and bcrypt.checkpw(password.encode('utf-8'), user['password'].encode('utf-8')):
        st.session_state.authenticated = True
        st.session_state.user = user
        st.session_state.login_attempts = 0
        st.session_state.session_id = f"session_{user['id']}_{int(time.time())}"
        update_activity()
        return True
    else:
        st.session_state.login_attempts += 1
        return False

def logout():
    """Logout user and clear session"""
    st.session_state.authenticated = False
    st.session_state.user = None
    st.session_state.session_id = None
    clear_user_cache()

def create_admin_user_if_not_exists():
    """Create default admin user from secrets"""
    admin_email = st.secrets["app"]["admin_email"]
    admin_password = st.secrets["app"]["admin_password"]
    
    if not db.get_user_by_email(admin_email):
        db.create_user("Admin", admin_email, admin_password, role="admin")

# Create admin user on startup
create_admin_user_if_not_exists()

# Check session timeout
if not check_session_timeout():
    update_activity()

# Custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #3B82F6;
        text-align: center;
        margin-bottom: 1rem;
    }
    .sub-header {
        font-size: 1.2rem;
        color: #6B7280;
        text-align: center;
        margin-bottom: 2rem;
    }
    .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 1.5rem;
        border-radius: 10px;
        color: white;
        text-align: center;
    }
    .user-badge {
        background: #3B82F6;
        color: white;
        padding: 0.5rem 1rem;
        border-radius: 20px;
        display: inline-block;
        margin-bottom: 1rem;
    }
    .admin-badge {
        background: #DC2626;
        color: white;
        padding: 0.3rem 0.8rem;
        border-radius: 15px;
        font-size: 0.8rem;
        margin-left: 0.5rem;
    }
</style>
""", unsafe_allow_html=True)

# ==================== AUTHENTICATION PAGE ====================
if not st.session_state.authenticated:
    st.markdown('<div class="main-header">⚖️ Themis</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">AI-Powered Hybrid Scheduling System</div>', unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        tab1, tab2 = st.tabs(["🔐 Sign In", "📝 Sign Up"])
        
        with tab1:
            st.markdown("### Welcome Back!")
            with st.form("login_form", clear_on_submit=False):
                email = st.text_input("Email", placeholder="your@email.com")
                password = st.text_input("Password", type="password", placeholder="••••••••")
                
                col_a, col_b = st.columns(2)
                with col_a:
                    submit = st.form_submit_button("Sign In", use_container_width=True, type="primary")
                with col_b:
                    if st.form_submit_button("Demo Login", use_container_width=True):
                        email = st.secrets["app"]["admin_email"]
                        password = st.secrets["app"]["admin_password"]
                        submit = True
                
                if submit:
                    if not email or not password:
                        st.error("Please fill in all fields")
                    elif authenticate(email, password):
                        st.success("✅ Logged in successfully!")
                        time.sleep(0.5)
                        st.rerun()
                    else:
                        st.error("❌ Invalid credentials")
                        st.info(f"Remaining attempts: {5 - st.session_state.login_attempts}")
        
        with tab2:
            st.markdown("### Create Account")
            with st.form("signup_form", clear_on_submit=True):
                username = st.text_input("Username", placeholder="John Doe")
                email = st.text_input("Email", placeholder="john@example.com")
                password = st.text_input("Password", type="password", placeholder="••••••••")
                confirm = st.text_input("Confirm Password", type="password", placeholder="••••••••")
                
                submit = st.form_submit_button("Create Account", use_container_width=True, type="primary")
                
                if submit:
                    if not username or not email or not password:
                        st.error("Please fill in all fields")
                    elif len(password) < 6:
                        st.error("Password must be at least 6 characters")
                    elif password != confirm:
                        st.error("Passwords don't match")
                    elif db.get_user_by_email(email):
                        st.error("Email already exists")
                    else:
                        db.create_user(username, email, password, role="editor")
                        st.success("✅ Account created! Please sign in.")
                        st.balloons()
    
    # Footer
    st.divider()
    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown("🤖 **AI-Powered**")
        st.caption("Gemini + Genetic Algorithm")
    with col2:
        st.markdown("📊 **Real-time Viz**")
        st.caption("Interactive charts & analytics")
    with col3:
        st.markdown("👥 **Collaboration**")
        st.caption("Share & work together")

# ==================== AUTHENTICATED USER INTERFACE ====================
else:
    user = st.session_state.user
    
    # Sidebar
    with st.sidebar:
        st.markdown(f'<div class="user-badge">👤 {user["username"]}</div>', unsafe_allow_html=True)
        if user['role'] == 'admin':
            st.markdown('<span class="admin-badge">ADMIN</span>', unsafe_allow_html=True)
        
        st.caption(f"Role: {user['role'].title()}")
        st.caption(f"Session: {st.session_state.session_id[:20]}...")
        
        st.divider()
        
        # Navigation
        st.markdown("### 📍 Navigation")
        
        # User module
        if st.button("👤 My Profile", use_container_width=True):
            st.session_state.page = "profile"
            st.rerun()
        
        # Admin module
        if user['role'] == 'admin':
            if st.button("🔧 Admin Panel", use_container_width=True):
                st.session_state.page = "admin"
                st.rerun()
        
        st.divider()
        
        # Quick actions
        st.markdown("### ⚡ Quick Actions")
        if st.button("➕ New Schedule", use_container_width=True):
            st.switch_page("pages/2_New_Schedule.py")
        
        if st.button("📊 My Dashboard", use_container_width=True):
            st.switch_page("pages/1_Dashboard.py")
        
        st.divider()
        
        # System info
        with st.expander("ℹ️ System Info"):
            st.caption(f"Version: 1.0.0")
            st.caption(f"Database: SQLite")
            st.caption(f"Session timeout: {SESSION_TIMEOUT_MINUTES}m")
            st.caption(f"Last activity: {st.session_state.last_activity.strftime('%H:%M:%S')}")
        
        st.divider()
        
        # Logout
        if st.button("🚪 Logout", use_container_width=True, type="secondary"):
            logout()
            st.rerun()
    
    # ==================== ADMIN PANEL ====================
    if user['role'] == 'admin' and st.session_state.get('page') == 'admin':
        st.title("🔧 Admin Panel")
        st.markdown("### System Administration Dashboard")
        
        # System statistics
        stats = get_system_stats(st.session_state.cache_timestamp)
        
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("👥 Total Users", stats['total_users'])
        with col2:
            st.metric("📅 Total Schedules", stats['total_schedules'])
        with col3:
            st.metric("✅ Finalized", stats['finalized_schedules'])
        with col4:
            st.metric("🔗 Shares", stats['total_shares'])
        
        st.divider()
        
        tab1, tab2, tab3 = st.tabs(["👥 User Management", "📊 System Stats", "⚙️ Settings"])
        
        # ===== USER MANAGEMENT =====
        with tab1:
            st.markdown("### User Management")
            
            col1, col2 = st.columns([2, 1])
            
            with col1:
                search_user = st.text_input("🔍 Search users by email")
            
            with col2:
                if st.button("🔄 Refresh Data", use_container_width=True):
                    clear_user_cache()
                    st.rerun()
            
            # Fetch all users
            with db.get_connection() as conn:
                cursor = conn.cursor()
                if search_user:
                    cursor.execute("SELECT * FROM users WHERE email LIKE ? OR username LIKE ?", 
                                 (f"%{search_user}%", f"%{search_user}%"))
                else:
                    cursor.execute("SELECT * FROM users ORDER BY created_at DESC LIMIT 50")
                users = cursor.fetchall()
            
            st.markdown(f"**Found {len(users)} users**")
            
            for user_row in users:
                user_data = dict(user_row)
                
                with st.expander(f"👤 {user_data['username']} ({user_data['email']})"):
                    col1, col2, col3 = st.columns(3)
                    
                    with col1:
                        st.write(f"**ID:** {user_data['id']}")
                        st.write(f"**Role:** {user_data['role']}")
                    with col2:
                        st.write(f"**Created:** {user_data['created_at']}")
                        schedules = db.get_user_schedules(user_data['id'])
                        st.write(f"**Schedules:** {len(schedules)}")
                    with col3:
                        # Role management
                        new_role = st.selectbox(
                            "Change Role",
                            ["admin", "editor", "viewer"],
                            index=["admin", "editor", "viewer"].index(user_data['role']),
                            key=f"role_{user_data['id']}"
                        )
                        
                        if new_role != user_data['role']:
                            if st.button("Update Role", key=f"update_{user_data['id']}"):
                                with db.get_connection() as conn:
                                    cursor = conn.cursor()
                                    cursor.execute("UPDATE users SET role=? WHERE id=?",
                                                 (new_role, user_data['id']))
                                st.success(f"Role updated to {new_role}")
                                time.sleep(1)
                                st.rerun()
                    
                    # Delete user (except self)
                    if user_data['id'] != user['id']:
                        if st.button(f"🗑️ Delete User", key=f"delete_{user_data['id']}", type="secondary"):
                            with db.get_connection() as conn:
                                cursor = conn.cursor()
                                # Delete user's schedules first
                                cursor.execute("DELETE FROM schedules WHERE owner_id=?", (user_data['id'],))
                                cursor.execute("DELETE FROM users WHERE id=?", (user_data['id'],))
                            st.success("User deleted")
                            clear_user_cache()
                            time.sleep(1)
                            st.rerun()
        
        # ===== SYSTEM STATISTICS =====
        with tab2:
            st.markdown("### System Statistics")
            
            # Activity over time
            with db.get_connection() as conn:
                cursor = conn.cursor()
                
                # Schedules created per day (last 30 days)
                cursor.execute("""
                    SELECT DATE(created_at) as date, COUNT(*) as count
                    FROM schedules
                    WHERE created_at >= DATE('now', '-30 days')
                    GROUP BY DATE(created_at)
                    ORDER BY date DESC
                """)
                schedule_activity = cursor.fetchall()
                
                if schedule_activity:
                    import pandas as pd
                    import plotly.express as px
                    
                    df = pd.DataFrame([dict(row) for row in schedule_activity])
                    fig = px.bar(df, x='date', y='count', 
                               title='Schedules Created (Last 30 Days)',
                               labels={'date': 'Date', 'count': 'Number of Schedules'})
                    st.plotly_chart(fig, use_container_width=True)
                
                # Top users by schedule count
                cursor.execute("""
                    SELECT u.username, u.email, COUNT(s.id) as schedule_count
                    FROM users u
                    LEFT JOIN schedules s ON u.id = s.owner_id
                    GROUP BY u.id
                    ORDER BY schedule_count DESC
                    LIMIT 10
                """)
                top_users = cursor.fetchall()
                
                st.markdown("#### 🏆 Top Users by Schedule Count")
                for idx, user_row in enumerate(top_users, 1):
                    col1, col2, col3 = st.columns([1, 3, 1])
                    with col1:
                        st.markdown(f"**#{idx}**")
                    with col2:
                        st.markdown(f"{user_row['username']} ({user_row['email']})")
                    with col3:
                        st.markdown(f"**{user_row['schedule_count']}** schedules")
        
        # ===== SETTINGS =====
        with tab3:
            st.markdown("### System Settings")
            
            st.markdown("#### 🗄️ Database Management")
            
            col1, col2 = st.columns(2)
            
            with col1:
                if st.button("🔄 Vacuum Database", use_container_width=True):
                    with db.get_connection() as conn:
                        conn.execute("VACUUM")
                    st.success("Database optimized!")
            
            with col2:
                if st.button("📊 Get DB Size", use_container_width=True):
                    import os
                    db_size = os.path.getsize(db.db_path) / (1024 * 1024)  # MB
                    st.info(f"Database size: {db_size:.2f} MB")
            
            st.divider()
            
            st.markdown("#### 🧹 Cache Management")
            if st.button("Clear All Caches", use_container_width=True):
                st.cache_data.clear()
                st.cache_resource.clear()
                clear_user_cache()
                st.success("All caches cleared!")
    
    # ==================== USER PROFILE ====================
    elif st.session_state.get('page') == 'profile':
        st.title("👤 My Profile")
        
        col1, col2 = st.columns([1, 2])
        
        with col1:
            st.markdown("### User Information")
            st.write(f"**Username:** {user['username']}")
            st.write(f"**Email:** {user['email']}")
            st.write(f"**Role:** {user['role'].title()}")
            st.write(f"**Member Since:** {user['created_at'][:10]}")
            
            # User statistics
            schedules = get_cached_user_schedules(user['id'], st.session_state.cache_timestamp)
            st.metric("My Schedules", len(schedules))
            
            finalized = len([s for s in schedules if s['status'] == 'finalized'])
            st.metric("Finalized", finalized)
        
        with col2:
            st.markdown("### Update Profile")
            
            with st.form("update_profile"):
                new_username = st.text_input("Username", value=user['username'])
                new_email = st.text_input("Email", value=user['email'])
                
                st.markdown("#### Change Password")
                current_password = st.text_input("Current Password", type="password")
                new_password = st.text_input("New Password", type="password")
                confirm_password = st.text_input("Confirm New Password", type="password")
                
                submit = st.form_submit_button("Update Profile", type="primary")
                
                if submit:
                    # Verify current password if changing password
                    if new_password:
                        if not current_password:
                            st.error("Enter current password to change password")
                        elif not bcrypt.checkpw(current_password.encode('utf-8'), 
                                               user['password'].encode('utf-8')):
                            st.error("Current password is incorrect")
                        elif new_password != confirm_password:
                            st.error("New passwords don't match")
                        elif len(new_password) < 6:
                            st.error("Password must be at least 6 characters")
                        else:
                            # Update password
                            hashed = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt())
                            with db.get_connection() as conn:
                                cursor = conn.cursor()
                                cursor.execute("UPDATE users SET password=? WHERE id=?",
                                             (hashed.decode('utf-8'), user['id']))
                            st.success("Password updated!")
                            clear_user_cache()
                    
                    # Update username/email
                    if new_username != user['username'] or new_email != user['email']:
                        with db.get_connection() as conn:
                            cursor = conn.cursor()
                            cursor.execute("UPDATE users SET username=?, email=? WHERE id=?",
                                         (new_username, new_email, user['id']))
                        st.success("Profile updated!")
                        
                        # Update session
                        st.session_state.user['username'] = new_username
                        st.session_state.user['email'] = new_email
                        clear_user_cache()
                        time.sleep(1)
                        st.rerun()
            
            st.divider()
            
            # Delete account
            with st.expander("⚠️ Danger Zone"):
                st.warning("**Delete Account** - This action cannot be undone!")
                
                confirm_delete = st.text_input("Type your email to confirm deletion")
                if st.button("Delete My Account", type="secondary"):
                    if confirm_delete == user['email']:
                        # Delete user's data
                        with db.get_connection() as conn:
                            cursor = conn.cursor()
                            cursor.execute("DELETE FROM schedules WHERE owner_id=?", (user['id'],))
                            cursor.execute("DELETE FROM share_permissions WHERE user_id=?", (user['id'],))
                            cursor.execute("DELETE FROM users WHERE id=?", (user['id'],))
                        
                        st.success("Account deleted. Goodbye! 👋")
                        logout()
                        time.sleep(2)
                        st.rerun()
                    else:
                        st.error("Email confirmation doesn't match")
    
    # ==================== HOME PAGE ====================
    else:
        st.session_state.page = None
        
        st.title("⚖️ Themis Schedule Optimizer")
        st.markdown("### Welcome back, " + user['username'] + "! 👋")
        
        # Quick stats
        schedules = get_cached_user_schedules(user['id'], st.session_state.cache_timestamp)
        
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("📅 Total Schedules", len(schedules))
        with col2:
            active = len([s for s in schedules if s['status'] == 'draft'])
            st.metric("🟡 Active", active)
        with col3:
            finalized = len([s for s in schedules if s['status'] == 'finalized'])
            st.metric("🟢 Finalized", finalized)
        with col4:
            # Count shared schedules
            shared = len([s for s in schedules if s['owner_id'] != user['id']])
            st.metric("🔗 Shared with me", shared)
        
        st.divider()
        
        # Getting started guide
        col1, col2 = st.columns([2, 1])
        
        with col1:
            st.markdown("### 🚀 Getting Started")
            st.markdown("""
            1. **📊 Dashboard** - View and manage all your schedules
            2. **✨ New Schedule** - Create a new scheduling project with entities and constraints
            3. **🔧 Optimizer** - Run AI + GA optimization on your schedules
            4. **👥 Collaborators** - Share schedules and manage permissions
            """)
            
            col_a, col_b = st.columns(2)
            with col_a:
                if st.button("➕ Create New Schedule", use_container_width=True, type="primary"):
                    st.switch_page("pages/2_New_Schedule.py")
            with col_b:
                if st.button("📊 View Dashboard", use_container_width=True):
                    st.switch_page("pages/1_Dashboard.py")
        
        with col2:
            st.markdown("### 💡 Quick Tips")
            st.info("""
            **Hybrid Mode** combines AI intelligence with genetic evolution for best results.
            
            **Cache** is refreshed every 5 minutes automatically.
            
            **Export** your schedules to PDF, Excel, or JSON.
            """)
        
        st.divider()
        
        # Recent schedules
        if schedules:
            st.markdown("### 📋 Recent Schedules")
            
            for schedule in schedules[:5]:
                with st.expander(f"📅 {schedule['title']} - {schedule['status']}"):
                    col1, col2, col3 = st.columns(3)
                    
                    with col1:
                        st.write(f"**Description:** {schedule.get('description', 'No description')}")
                        st.write(f"**Status:** {schedule['status']}")
                    with col2:
                        st.write(f"**Entities:** {len(schedule.get('entities', []))}")
                        st.write(f"**Constraints:** {len(schedule.get('constraints', []))}")
                    with col3:
                        st.write(f"**Created:** {schedule['created_at'][:10]}")
                        st.write(f"**Updated:** {schedule['updated_at'][:10]}")
                    
                    if st.button(f"Open Schedule", key=f"open_{schedule['id']}"):
                        st.session_state.current_schedule_id = schedule['id']
                        st.switch_page("pages/3_Optimizer.py")
        else:
            st.info("No schedules yet. Create your first one to get started!")
