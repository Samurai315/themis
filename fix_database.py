import sqlite3
import os
import shutil
from datetime import datetime

def backup_database():
    """Create backup of existing database"""
    db_path = "themis.db"
    if os.path.exists(db_path):
        backup_path = f"themis_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
        shutil.copy2(db_path, backup_path)
        print(f"✅ Backup created: {backup_path}")
        return True
    return False

def fix_schedules_table():
    """Fix schedules table schema"""
    db_path = "themis.db"
    
    if not os.path.exists(db_path):
        print("❌ Database not found!")
        return
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        print("\n🔧 Checking schedules table schema...")
        
        # Get current columns
        cursor.execute("PRAGMA table_info(schedules)")
        columns = {col[1]: col[2] for col in cursor.fetchall()}
        
        print(f"Current columns: {list(columns.keys())}")
        
        # Define required columns
        required_columns = {
            'semester': 'INTEGER',
            'academic_year': 'TEXT',
            'optimization_config': "TEXT DEFAULT '{}'",
            'optimization_history': "TEXT DEFAULT '[]'"
        }
        
        # Add missing columns
        for col_name, col_type in required_columns.items():
            if col_name not in columns:
                try:
                    cursor.execute(f"ALTER TABLE schedules ADD COLUMN {col_name} {col_type}")
                    print(f"✅ Added column: {col_name} ({col_type})")
                except Exception as e:
                    print(f"⚠️ Could not add {col_name}: {e}")
        
        conn.commit()
        
        # Verify final schema
        print("\n📋 Final schedules table schema:")
        cursor.execute("PRAGMA table_info(schedules)")
        for col in cursor.fetchall():
            print(f"  - {col[1]} ({col[2]})")
        
        print("\n✅ Database schema fixed successfully!")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    print("=" * 60)
    print("DATABASE SCHEMA FIX TOOL")
    print("=" * 60)
    
    # Create backup
    backup_database()
    
    # Fix schema
    fix_schedules_table()
    
    print("\n" + "=" * 60)
    print("You can now restart your Streamlit app!")
    print("=" * 60)
