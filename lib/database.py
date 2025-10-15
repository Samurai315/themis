import sqlite3
import json
import bcrypt
import streamlit as st
from datetime import datetime
from contextlib import contextmanager
import threading

class Database:
    """Enhanced SQLite database for College Timetable Scheduling"""
    
    _lock = threading.Lock()
    
    def __init__(self):
        self.db_path = st.secrets.get("database", {}).get("path", "themis.db")
        self._initialize_database()
    
    @contextmanager
    def get_connection(self):
        """Thread-safe database connection"""
        with self._lock:
            conn = sqlite3.connect(self.db_path, check_same_thread=False)
            conn.row_factory = sqlite3.Row
            try:
                yield conn
                conn.commit()
            except Exception as e:
                conn.rollback()
                raise e
            finally:
                conn.close()
    
    def _initialize_database(self):
        """Create all tables for college timetable system"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # ============ USER MANAGEMENT ============
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT NOT NULL,
                    email TEXT UNIQUE NOT NULL,
                    password TEXT NOT NULL,
                    role TEXT DEFAULT 'editor',
                    preferences TEXT DEFAULT '{}',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # ============ COLLEGE PROFILE ============
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS college_profile (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    college_name TEXT NOT NULL,
                    academic_year TEXT,
                    semester TEXT,
                    working_days TEXT DEFAULT '["Monday","Tuesday","Wednesday","Thursday","Friday","Saturday"]',
                    time_slots TEXT DEFAULT '["09:00","10:00","11:00","12:00","13:00","14:00","15:00","16:00"]',
                    slot_duration INTEGER DEFAULT 60,
                    max_periods_per_day INTEGER DEFAULT 8,
                    created_by INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (created_by) REFERENCES users (id)
                )
            ''')
            
            # ============ DEPARTMENTS ============
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS departments (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    dept_code TEXT UNIQUE NOT NULL,
                    dept_name TEXT NOT NULL,
                    hod_name TEXT,
                    description TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # ============ INFRASTRUCTURE (ROOMS & LABS) ============
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS infrastructure (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    room_code TEXT UNIQUE NOT NULL,
                    room_name TEXT NOT NULL,
                    room_type TEXT NOT NULL,
                    capacity INTEGER NOT NULL,
                    floor INTEGER,
                    building TEXT,
                    facilities TEXT DEFAULT '[]',
                    availability TEXT DEFAULT '{}',
                    is_active BOOLEAN DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # ============ FACULTY ============
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS faculty (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    faculty_code TEXT UNIQUE NOT NULL,
                    faculty_name TEXT NOT NULL,
                    department_id INTEGER,
                    designation TEXT,
                    email TEXT,
                    phone TEXT,
                    max_hours_per_week INTEGER DEFAULT 18,
                    max_hours_per_day INTEGER DEFAULT 6,
                    preferred_days TEXT DEFAULT '[]',
                    preferred_times TEXT DEFAULT '[]',
                    unavailable_slots TEXT DEFAULT '[]',
                    is_active BOOLEAN DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (department_id) REFERENCES departments (id)
                )
            ''')
            
            # ============ PROGRAMS ============
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS programs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    program_code TEXT UNIQUE NOT NULL,
                    program_name TEXT NOT NULL,
                    duration_years INTEGER NOT NULL,
                    department_id INTEGER,
                    description TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (department_id) REFERENCES departments (id)
                )
            ''')
            
            # ============ BATCHES/CLASSES ============
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS batches (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    batch_code TEXT UNIQUE NOT NULL,
                    batch_name TEXT NOT NULL,
                    program_id INTEGER NOT NULL,
                    year INTEGER NOT NULL,
                    section TEXT,
                    num_students INTEGER NOT NULL,
                    semester INTEGER,
                    is_active BOOLEAN DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (program_id) REFERENCES programs (id)
                )
            ''')
            
            # ============ SUBJECTS/COURSES ============
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS subjects (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    subject_code TEXT UNIQUE NOT NULL,
                    subject_name TEXT NOT NULL,
                    subject_type TEXT NOT NULL,
                    credits INTEGER,
                    theory_hours INTEGER DEFAULT 0,
                    lab_hours INTEGER DEFAULT 0,
                    tutorial_hours INTEGER DEFAULT 0,
                    total_hours_per_week INTEGER NOT NULL,
                    requires_lab BOOLEAN DEFAULT 0,
                    preferred_lab_id INTEGER,
                    consecutive_hours BOOLEAN DEFAULT 0,
                    department_id INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (preferred_lab_id) REFERENCES infrastructure (id),
                    FOREIGN KEY (department_id) REFERENCES departments (id)
                )
            ''')
            
            # ============ SUBJECT ALLOCATION ============
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS subject_allocation (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    subject_id INTEGER NOT NULL,
                    batch_id INTEGER NOT NULL,
                    faculty_id INTEGER NOT NULL,
                    semester INTEGER,
                    academic_year TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (subject_id) REFERENCES subjects (id),
                    FOREIGN KEY (batch_id) REFERENCES batches (id),
                    FOREIGN KEY (faculty_id) REFERENCES faculty (id),
                    UNIQUE(subject_id, batch_id, semester, academic_year)
                )
            ''')
            
            # ============ HOLIDAYS ============
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS holidays (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    holiday_date DATE NOT NULL,
                    holiday_name TEXT NOT NULL,
                    holiday_type TEXT,
                    description TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # ============ TIMETABLE SESSIONS ============
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS timetable_sessions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    schedule_id INTEGER,
                    subject_id INTEGER NOT NULL,
                    batch_id INTEGER NOT NULL,
                    faculty_id INTEGER NOT NULL,
                    room_id INTEGER NOT NULL,
                    day_of_week TEXT NOT NULL,
                    time_slot TEXT NOT NULL,
                    duration INTEGER DEFAULT 1,
                    session_type TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (subject_id) REFERENCES subjects (id),
                    FOREIGN KEY (batch_id) REFERENCES batches (id),
                    FOREIGN KEY (faculty_id) REFERENCES faculty (id),
                    FOREIGN KEY (room_id) REFERENCES infrastructure (id)
                )
            ''')
            
            # ============ SCHEDULES (MAIN CONTAINER) ============
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS schedules (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    description TEXT,
                    semester INTEGER,
                    academic_year TEXT,
                    owner_id INTEGER NOT NULL,
                    status TEXT DEFAULT 'draft',
                    optimization_config TEXT DEFAULT '{}',
                    optimization_history TEXT DEFAULT '[]',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (owner_id) REFERENCES users (id)
                )
            ''')
            
            # ============ FACULTY LEAVES ============
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS faculty_leaves (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    faculty_id INTEGER NOT NULL,
                    leave_date DATE NOT NULL,
                    leave_type TEXT,
                    reason TEXT,
                    substitute_faculty_id INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (faculty_id) REFERENCES faculty (id),
                    FOREIGN KEY (substitute_faculty_id) REFERENCES faculty (id)
                )
            ''')
            
            # ============ EVENTS/MEETINGS ============
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    event_name TEXT NOT NULL,
                    event_date DATE NOT NULL,
                    start_time TEXT NOT NULL,
                    end_time TEXT NOT NULL,
                    event_type TEXT,
                    affected_batches TEXT DEFAULT '[]',
                    affected_faculty TEXT DEFAULT '[]',
                    rooms_blocked TEXT DEFAULT '[]',
                    description TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # ============ SHARE PERMISSIONS ============
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS share_permissions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    schedule_id INTEGER NOT NULL,
                    user_id INTEGER NOT NULL,
                    permission TEXT DEFAULT 'view',
                    shared_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (schedule_id) REFERENCES schedules (id),
                    FOREIGN KEY (user_id) REFERENCES users (id),
                    UNIQUE(schedule_id, user_id)
                )
            ''')
            
            conn.commit()
    
    # ==================== HELPER METHODS ====================
    
    def _parse_json_field(self, data, field):
        """Parse JSON string field to Python object"""
        if field in data and isinstance(data[field], str):
            try:
                data[field] = json.loads(data[field])
            except:
                data[field] = [] if field.endswith('s') or field == 'facilities' else {}
        return data
    
    # ==================== USER OPERATIONS ====================
    
    def create_user(self, username, email, password, role="editor"):
        """Create new user"""
        hashed = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO users (username, email, password, role)
                VALUES (?, ?, ?, ?)
            ''', (username, email, hashed.decode('utf-8'), role))
            return cursor.lastrowid
    
    def get_user_by_email(self, email):
        """Get user by email"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM users WHERE email = ?', (email,))
            row = cursor.fetchone()
            return dict(row) if row else None
    
    def get_user_by_id(self, user_id):
        """Get user by ID"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM users WHERE id = ?', (user_id,))
            row = cursor.fetchone()
            return dict(row) if row else None
    
    # ==================== COLLEGE PROFILE ====================
    
    def create_or_update_college_profile(self, data, user_id):
        """Create or update college profile"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Check if profile exists
            cursor.execute('SELECT id FROM college_profile LIMIT 1')
            existing = cursor.fetchone()
            
            if existing:
                cursor.execute('''
                    UPDATE college_profile SET
                        college_name = ?,
                        academic_year = ?,
                        semester = ?,
                        working_days = ?,
                        time_slots = ?,
                        slot_duration = ?,
                        max_periods_per_day = ?,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                ''', (
                    data['college_name'],
                    data['academic_year'],
                    data['semester'],
                    json.dumps(data['working_days']),
                    json.dumps(data['time_slots']),
                    data['slot_duration'],
                    data['max_periods_per_day'],
                    existing['id']
                ))
                return existing['id']
            else:
                cursor.execute('''
                    INSERT INTO college_profile 
                    (college_name, academic_year, semester, working_days, time_slots, 
                     slot_duration, max_periods_per_day, created_by)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    data['college_name'],
                    data['academic_year'],
                    data['semester'],
                    json.dumps(data['working_days']),
                    json.dumps(data['time_slots']),
                    data['slot_duration'],
                    data['max_periods_per_day'],
                    user_id
                ))
                return cursor.lastrowid
    
    def get_college_profile(self):
        """Get college profile"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM college_profile LIMIT 1')
            row = cursor.fetchone()
            if row:
                data = dict(row)
                data = self._parse_json_field(data, 'working_days')
                data = self._parse_json_field(data, 'time_slots')
                return data
            return None
    
    # ==================== DEPARTMENT OPERATIONS ====================
    
    def create_department(self, dept_code, dept_name, hod_name=None, description=None):
        """Create department"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO departments (dept_code, dept_name, hod_name, description)
                VALUES (?, ?, ?, ?)
            ''', (dept_code, dept_name, hod_name, description))
            return cursor.lastrowid
    
    def get_all_departments(self):
        """Get all departments"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM departments ORDER BY dept_name')
            return [dict(row) for row in cursor.fetchall()]
    
    def get_department(self, dept_id):
        """Get department by ID"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM departments WHERE id = ?', (dept_id,))
            row = cursor.fetchone()
            return dict(row) if row else None
    
    # ==================== INFRASTRUCTURE OPERATIONS ====================
    
    def create_infrastructure(self, data):
        """Create classroom or lab"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO infrastructure 
                (room_code, room_name, room_type, capacity, floor, building, facilities)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                data['room_code'],
                data['room_name'],
                data['room_type'],
                data['capacity'],
                data.get('floor'),
                data.get('building'),
                json.dumps(data.get('facilities', []))
            ))
            return cursor.lastrowid
    
    def get_all_infrastructure(self, room_type=None):
        """Get all rooms/labs"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            if room_type:
                cursor.execute('SELECT * FROM infrastructure WHERE room_type = ? AND is_active = 1', (room_type,))
            else:
                cursor.execute('SELECT * FROM infrastructure WHERE is_active = 1')
            
            results = []
            for row in cursor.fetchall():
                data = dict(row)
                data = self._parse_json_field(data, 'facilities')
                results.append(data)
            return results
    
    # ==================== FACULTY OPERATIONS ====================
    
    def create_faculty(self, data):
        """Create faculty member"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO faculty 
                (faculty_code, faculty_name, department_id, designation, email, phone,
                 max_hours_per_week, max_hours_per_day, preferred_days, preferred_times, unavailable_slots)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                data['faculty_code'],
                data['faculty_name'],
                data.get('department_id'),
                data.get('designation'),
                data.get('email'),
                data.get('phone'),
                data.get('max_hours_per_week', 18),
                data.get('max_hours_per_day', 6),
                json.dumps(data.get('preferred_days', [])),
                json.dumps(data.get('preferred_times', [])),
                json.dumps(data.get('unavailable_slots', []))
            ))
            return cursor.lastrowid
    
    def get_all_faculty(self, department_id=None):
        """Get all faculty"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            if department_id:
                cursor.execute('SELECT * FROM faculty WHERE department_id = ? AND is_active = 1', (department_id,))
            else:
                cursor.execute('SELECT * FROM faculty WHERE is_active = 1')
            
            results = []
            for row in cursor.fetchall():
                data = dict(row)
                data = self._parse_json_field(data, 'preferred_days')
                data = self._parse_json_field(data, 'preferred_times')
                data = self._parse_json_field(data, 'unavailable_slots')
                results.append(data)
            return results
    
        # ==================== PROGRAM OPERATIONS ====================
    
    def create_program(self, data):
        """Create academic program"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO programs 
                (program_code, program_name, duration_years, department_id, description)
                VALUES (?, ?, ?, ?, ?)
            ''', (
                data['program_code'],
                data['program_name'],
                data['duration_years'],
                data.get('department_id'),
                data.get('description')
            ))
            return cursor.lastrowid
    
    def get_all_programs(self, department_id=None):
        """Get all programs"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            if department_id:
                cursor.execute('SELECT * FROM programs WHERE department_id = ?', (department_id,))
            else:
                cursor.execute('SELECT * FROM programs ORDER BY program_name')
            return [dict(row) for row in cursor.fetchall()]
    
    def get_program(self, program_id):
        """Get program by ID"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM programs WHERE id = ?', (program_id,))
            row = cursor.fetchone()
            return dict(row) if row else None
    
    # ==================== BATCH OPERATIONS ====================
    
    def create_batch(self, data):
        """Create batch/class"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO batches 
                (batch_code, batch_name, program_id, year, section, num_students, semester)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                data['batch_code'],
                data['batch_name'],
                data['program_id'],
                data['year'],
                data.get('section'),
                data['num_students'],
                data.get('semester')
            ))
            return cursor.lastrowid
    
    def get_all_batches(self, program_id=None, year=None):
        """Get all batches"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            if program_id and year:
                cursor.execute('SELECT * FROM batches WHERE program_id = ? AND year = ? AND is_active = 1', 
                             (program_id, year))
            elif program_id:
                cursor.execute('SELECT * FROM batches WHERE program_id = ? AND is_active = 1', (program_id,))
            elif year:
                cursor.execute('SELECT * FROM batches WHERE year = ? AND is_active = 1', (year,))
            else:
                cursor.execute('SELECT * FROM batches WHERE is_active = 1 ORDER BY program_id, year, section')
            
            return [dict(row) for row in cursor.fetchall()]
    
    def get_batch(self, batch_id):
        """Get batch by ID"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM batches WHERE id = ?', (batch_id,))
            row = cursor.fetchone()
            return dict(row) if row else None
    
    def get_batch_with_details(self, batch_id):
        """Get batch with program details"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT b.*, p.program_name, p.program_code
                FROM batches b
                JOIN programs p ON b.program_id = p.id
                WHERE b.id = ?
            ''', (batch_id,))
            row = cursor.fetchone()
            return dict(row) if row else None
    
    # ==================== SUBJECT OPERATIONS ====================
    
    def create_subject(self, data):
        """Create subject/course"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO subjects 
                (subject_code, subject_name, subject_type, credits, theory_hours, lab_hours, 
                 tutorial_hours, total_hours_per_week, requires_lab, preferred_lab_id, 
                 consecutive_hours, department_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                data['subject_code'],
                data['subject_name'],
                data['subject_type'],
                data.get('credits'),
                data.get('theory_hours', 0),
                data.get('lab_hours', 0),
                data.get('tutorial_hours', 0),
                data['total_hours_per_week'],
                data.get('requires_lab', 0),
                data.get('preferred_lab_id'),
                data.get('consecutive_hours', 0),
                data.get('department_id')
            ))
            return cursor.lastrowid
    
    def get_all_subjects(self, department_id=None):
        """Get all subjects"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            if department_id:
                cursor.execute('SELECT * FROM subjects WHERE department_id = ?', (department_id,))
            else:
                cursor.execute('SELECT * FROM subjects ORDER BY subject_name')
            return [dict(row) for row in cursor.fetchall()]
    
    def get_subject(self, subject_id):
        """Get subject by ID"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM subjects WHERE id = ?', (subject_id,))
            row = cursor.fetchone()
            return dict(row) if row else None
    
    def get_subject_with_lab(self, subject_id):
        """Get subject with lab details"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT s.*, i.room_name as lab_name, i.capacity as lab_capacity
                FROM subjects s
                LEFT JOIN infrastructure i ON s.preferred_lab_id = i.id
                WHERE s.id = ?
            ''', (subject_id,))
            row = cursor.fetchone()
            return dict(row) if row else None
    
    # ==================== SUBJECT ALLOCATION ====================
    
    def create_subject_allocation(self, data):
        """Allocate subject to batch with faculty"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO subject_allocation 
                (subject_id, batch_id, faculty_id, semester, academic_year)
                VALUES (?, ?, ?, ?, ?)
            ''', (
                data['subject_id'],
                data['batch_id'],
                data['faculty_id'],
                data.get('semester'),
                data.get('academic_year')
            ))
            return cursor.lastrowid
    
    def get_allocations_by_batch(self, batch_id, semester=None):
        """Get all subject allocations for a batch"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            query = '''
                SELECT sa.*, 
                       s.subject_name, s.subject_code, s.total_hours_per_week, 
                       s.theory_hours, s.lab_hours, s.requires_lab,
                       f.faculty_name, f.faculty_code,
                       b.batch_name
                FROM subject_allocation sa
                JOIN subjects s ON sa.subject_id = s.id
                JOIN faculty f ON sa.faculty_id = f.id
                JOIN batches b ON sa.batch_id = b.id
                WHERE sa.batch_id = ?
            '''
            
            params = [batch_id]
            if semester:
                query += ' AND sa.semester = ?'
                params.append(semester)
            
            cursor.execute(query, params)
            return [dict(row) for row in cursor.fetchall()]
    
    def get_allocations_by_faculty(self, faculty_id, semester=None):
        """Get all allocations for a faculty"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            query = '''
                SELECT sa.*, 
                       s.subject_name, s.subject_code, s.total_hours_per_week,
                       b.batch_name, b.num_students
                FROM subject_allocation sa
                JOIN subjects s ON sa.subject_id = s.id
                JOIN batches b ON sa.batch_id = b.id
                WHERE sa.faculty_id = ?
            '''
            
            params = [faculty_id]
            if semester:
                query += ' AND sa.semester = ?'
                params.append(semester)
            
            cursor.execute(query, params)
            return [dict(row) for row in cursor.fetchall()]
    
    def calculate_faculty_workload(self, faculty_id, semester=None):
        """Calculate total teaching hours for faculty"""
        allocations = self.get_allocations_by_faculty(faculty_id, semester)
        total_hours = sum(alloc['total_hours_per_week'] for alloc in allocations)
        return {
            'faculty_id': faculty_id,
            'total_hours': total_hours,
            'num_subjects': len(allocations),
            'allocations': allocations
        }
    
    # ==================== HOLIDAY OPERATIONS ====================
    
    def create_holiday(self, holiday_date, holiday_name, holiday_type=None, description=None):
        """Create holiday entry"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO holidays (holiday_date, holiday_name, holiday_type, description)
                VALUES (?, ?, ?, ?)
            ''', (holiday_date, holiday_name, holiday_type, description))
            return cursor.lastrowid
    
    def get_all_holidays(self, year=None, month=None):
        """Get holidays"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            if year and month:
                cursor.execute('''
                    SELECT * FROM holidays 
                    WHERE strftime('%Y', holiday_date) = ? AND strftime('%m', holiday_date) = ?
                    ORDER BY holiday_date
                ''', (str(year), f'{month:02d}'))
            elif year:
                cursor.execute('''
                    SELECT * FROM holidays 
                    WHERE strftime('%Y', holiday_date) = ?
                    ORDER BY holiday_date
                ''', (str(year),))
            else:
                cursor.execute('SELECT * FROM holidays ORDER BY holiday_date')
            
            return [dict(row) for row in cursor.fetchall()]
    
    def delete_holiday(self, holiday_id):
        """Delete holiday"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM holidays WHERE id = ?', (holiday_id,))
            return cursor.rowcount
    
    def is_holiday(self, date):
        """Check if date is a holiday"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM holidays WHERE holiday_date = ?', (date,))
            return cursor.fetchone() is not None
    
    # ==================== FACULTY LEAVE OPERATIONS ====================
    
    def create_faculty_leave(self, data):
        """Create faculty leave entry"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO faculty_leaves 
                (faculty_id, leave_date, leave_type, reason, substitute_faculty_id)
                VALUES (?, ?, ?, ?, ?)
            ''', (
                data['faculty_id'],
                data['leave_date'],
                data.get('leave_type'),
                data.get('reason'),
                data.get('substitute_faculty_id')
            ))
            return cursor.lastrowid
    
    def get_faculty_leaves(self, faculty_id=None, date=None):
        """Get faculty leaves"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            if faculty_id and date:
                cursor.execute('''
                    SELECT fl.*, f.faculty_name
                    FROM faculty_leaves fl
                    JOIN faculty f ON fl.faculty_id = f.id
                    WHERE fl.faculty_id = ? AND fl.leave_date = ?
                ''', (faculty_id, date))
            elif faculty_id:
                cursor.execute('''
                    SELECT fl.*, f.faculty_name
                    FROM faculty_leaves fl
                    JOIN faculty f ON fl.faculty_id = f.id
                    WHERE fl.faculty_id = ?
                    ORDER BY fl.leave_date DESC
                ''', (faculty_id,))
            elif date:
                cursor.execute('''
                    SELECT fl.*, f.faculty_name
                    FROM faculty_leaves fl
                    JOIN faculty f ON fl.faculty_id = f.id
                    WHERE fl.leave_date = ?
                ''', (date,))
            else:
                cursor.execute('''
                    SELECT fl.*, f.faculty_name
                    FROM faculty_leaves fl
                    JOIN faculty f ON fl.faculty_id = f.id
                    ORDER BY fl.leave_date DESC
                ''')
            
            return [dict(row) for row in cursor.fetchall()]
    
    def is_faculty_on_leave(self, faculty_id, date):
        """Check if faculty is on leave"""
        leaves = self.get_faculty_leaves(faculty_id, date)
        return len(leaves) > 0
    
    # ==================== EVENT OPERATIONS ====================
    
    def create_event(self, data):
        """Create event/meeting"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO events 
                (event_name, event_date, start_time, end_time, event_type,
                 affected_batches, affected_faculty, rooms_blocked, description)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                data['event_name'],
                data['event_date'],
                data['start_time'],
                data['end_time'],
                data.get('event_type'),
                json.dumps(data.get('affected_batches', [])),
                json.dumps(data.get('affected_faculty', [])),
                json.dumps(data.get('rooms_blocked', [])),
                data.get('description')
            ))
            return cursor.lastrowid
    
    def get_events(self, date=None):
        """Get events"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            if date:
                cursor.execute('SELECT * FROM events WHERE event_date = ?', (date,))
            else:
                cursor.execute('SELECT * FROM events ORDER BY event_date DESC')
            
            results = []
            for row in cursor.fetchall():
                data = dict(row)
                data = self._parse_json_field(data, 'affected_batches')
                data = self._parse_json_field(data, 'affected_faculty')
                data = self._parse_json_field(data, 'rooms_blocked')
                results.append(data)
            return results
    
    # ==================== TIMETABLE SESSION OPERATIONS ====================
    
    def create_timetable_session(self, data):
        """Create timetable session"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO timetable_sessions 
                (schedule_id, subject_id, batch_id, faculty_id, room_id,
                 day_of_week, time_slot, duration, session_type)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                data.get('schedule_id'),
                data['subject_id'],
                data['batch_id'],
                data['faculty_id'],
                data['room_id'],
                data['day_of_week'],
                data['time_slot'],
                data.get('duration', 1),
                data['session_type']
            ))
            return cursor.lastrowid
    
    def get_timetable_sessions(self, schedule_id=None, batch_id=None, faculty_id=None):
        """Get timetable sessions"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            query = '''
                SELECT ts.*,
                       s.subject_name, s.subject_code,
                       b.batch_name,
                       f.faculty_name,
                       i.room_name, i.room_code
                FROM timetable_sessions ts
                JOIN subjects s ON ts.subject_id = s.id
                JOIN batches b ON ts.batch_id = b.id
                JOIN faculty f ON ts.faculty_id = f.id
                JOIN infrastructure i ON ts.room_id = i.id
                WHERE 1=1
            '''
            
            params = []
            if schedule_id:
                query += ' AND ts.schedule_id = ?'
                params.append(schedule_id)
            if batch_id:
                query += ' AND ts.batch_id = ?'
                params.append(batch_id)
            if faculty_id:
                query += ' AND ts.faculty_id = ?'
                params.append(faculty_id)
            
            query += ' ORDER BY ts.day_of_week, ts.time_slot'
            
            cursor.execute(query, params)
            return [dict(row) for row in cursor.fetchall()]
    
    def delete_timetable_sessions_by_schedule(self, schedule_id):
        """Delete all sessions for a schedule"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM timetable_sessions WHERE schedule_id = ?', (schedule_id,))
            return cursor.rowcount
    
    def check_session_conflicts(self, session_data):
        """Check for scheduling conflicts"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            conflicts = []
            
            # Check faculty conflict
            cursor.execute('''
                SELECT * FROM timetable_sessions
                WHERE faculty_id = ? AND day_of_week = ? AND time_slot = ?
                AND id != ?
            ''', (
                session_data['faculty_id'],
                session_data['day_of_week'],
                session_data['time_slot'],
                session_data.get('id', 0)
            ))
            
            if cursor.fetchone():
                conflicts.append({
                    'type': 'faculty_conflict',
                    'message': 'Faculty already has a class at this time'
                })
            
            # Check room conflict
            cursor.execute('''
                SELECT * FROM timetable_sessions
                WHERE room_id = ? AND day_of_week = ? AND time_slot = ?
                AND id != ?
            ''', (
                session_data['room_id'],
                session_data['day_of_week'],
                session_data['time_slot'],
                session_data.get('id', 0)
            ))
            
            if cursor.fetchone():
                conflicts.append({
                    'type': 'room_conflict',
                    'message': 'Room already occupied at this time'
                })
            
            # Check batch conflict
            cursor.execute('''
                SELECT * FROM timetable_sessions
                WHERE batch_id = ? AND day_of_week = ? AND time_slot = ?
                AND id != ?
            ''', (
                session_data['batch_id'],
                session_data['day_of_week'],
                session_data['time_slot'],
                session_data.get('id', 0)
            ))
            
            if cursor.fetchone():
                conflicts.append({
                    'type': 'batch_conflict',
                    'message': 'Batch already has a class at this time'
                })
            
            return conflicts
    
    # ==================== SCHEDULE OPERATIONS ====================
    
    def create_schedule(self, owner_id, title, description="", semester=None, academic_year=None, num_weeks=16, start_date=None, end_date=None):
        """Create new schedule container with semester info"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Store additional semester info in description or new fields
            metadata = {
                'num_weeks': num_weeks,
                'start_date': str(start_date) if start_date else None,
                'end_date': str(end_date) if end_date else None,
                'recurring_weekly': True
            }
            
            description_with_meta = f"{description}\n[META]{json.dumps(metadata)}[/META]"
            
            cursor.execute('''
                INSERT INTO schedules (title, description, owner_id, semester, academic_year)
                VALUES (?, ?, ?, ?, ?)
            ''', (title, description_with_meta, owner_id, semester, academic_year))
            return cursor.lastrowid
    
    def get_user_schedules(self, user_id):
        """Get all schedules for user"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Owned schedules
            cursor.execute('''
                SELECT * FROM schedules WHERE owner_id = ?
                ORDER BY updated_at DESC
            ''', (user_id,))
            owned = [dict(row) for row in cursor.fetchall()]
            
            # Shared schedules
            cursor.execute('''
                SELECT s.* FROM schedules s
                JOIN share_permissions sp ON s.id = sp.schedule_id
                WHERE sp.user_id = ?
                ORDER BY s.updated_at DESC
            ''', (user_id,))
            shared = [dict(row) for row in cursor.fetchall()]
            
            return owned + shared
    
    def get_schedule(self, schedule_id):
        """Get schedule by ID"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM schedules WHERE id = ?', (schedule_id,))
            row = cursor.fetchone()
            if row:
                data = dict(row)
                data = self._parse_json_field(data, 'optimization_config')
                data = self._parse_json_field(data, 'optimization_history')
                return data
            return None
    
    def update_schedule(self, schedule_id, updates):
        """Update schedule"""
        updates['updated_at'] = datetime.now().isoformat()
        
        # Convert dicts/lists to JSON
        for key in ['optimization_config', 'optimization_history']:
            if key in updates and isinstance(updates[key], (dict, list)):
                updates[key] = json.dumps(updates[key])
        
        set_clause = ', '.join([f"{key} = ?" for key in updates.keys()])
        values = list(updates.values()) + [schedule_id]
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(f'UPDATE schedules SET {set_clause} WHERE id = ?', values)
            return cursor.rowcount
    
    def delete_schedule(self, schedule_id):
        """Delete schedule and all sessions"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Delete sessions first
            cursor.execute('DELETE FROM timetable_sessions WHERE schedule_id = ?', (schedule_id,))
            
            # Delete shares
            cursor.execute('DELETE FROM share_permissions WHERE schedule_id = ?', (schedule_id,))
            
            # Delete schedule
            cursor.execute('DELETE FROM schedules WHERE id = ?', (schedule_id,))
            
            return cursor.rowcount
    
    # ==================== SHARING OPERATIONS ====================
    
    def share_schedule(self, schedule_id, user_id, permission="view"):
        """Share schedule"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT OR REPLACE INTO share_permissions (schedule_id, user_id, permission)
                VALUES (?, ?, ?)
            ''', (schedule_id, user_id, permission))
            return cursor.lastrowid
    
    def get_schedule_permissions(self, schedule_id, user_id):
        """Get user permission for schedule"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT permission FROM share_permissions
                WHERE schedule_id = ? AND user_id = ?
            ''', (schedule_id, user_id))
            row = cursor.fetchone()
            return row['permission'] if row else None
    
    def get_schedule_collaborators(self, schedule_id):
        """Get all collaborators for schedule"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT u.id, u.username, u.email, sp.permission, sp.shared_at
                FROM users u
                JOIN share_permissions sp ON u.id = sp.user_id
                WHERE sp.schedule_id = ?
            ''', (schedule_id,))
            return [dict(row) for row in cursor.fetchall()]



# Cache database instance
@st.cache_resource
def get_database():
    """Get cached database instance"""
    return Database()
