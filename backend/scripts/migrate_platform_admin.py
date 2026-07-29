import sqlite3
import os

# the rent.db is in app/app/database/rent.db actually wait, no, final_schema.py says DB_PATH = os.environ.get("RENT_DB_PATH", "/code/storage/database/rent.db")
# But in development, where is it? 
# Let me check where the current rent.db is. In the file list, there's `app\app\database\rent.db`.
DB_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'storage', 'database', 'rent.db'))

def migrate():
    print(f"Connecting to database: {DB_PATH}")
    if not os.path.exists(DB_PATH):
        print("Database not found. Exiting.")
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    try:
        # Check if the column already exists
        cursor.execute("PRAGMA table_info(admins)")
        columns = [col[1] for col in cursor.fetchall()]
        
        if "is_platform_admin" not in columns:
            print("Adding is_platform_admin column to admins table...")
            cursor.execute("ALTER TABLE admins ADD COLUMN is_platform_admin INTEGER NOT NULL DEFAULT 0")
            
            # Set the default admin to be a platform admin
            print("Setting 'admin' as platform admin...")
            cursor.execute("UPDATE admins SET is_platform_admin = 1 WHERE username = 'admin'")
            
            conn.commit()
            print("Migration successful.")
        else:
            print("Column is_platform_admin already exists. Skipping migration.")
            
    except Exception as e:
        print(f"Migration failed: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    migrate()
