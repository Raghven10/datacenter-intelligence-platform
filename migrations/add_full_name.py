from sqlalchemy import create_engine, text
import sys
import os

# Ensure app is in path
sys.path.append(os.getcwd())

from app.db.session import DATABASE_URL

def migrate():
    engine = create_engine(DATABASE_URL)
    with engine.connect() as conn:
        print("Checking for full_name column...")
        # Check if column exists (Postgres specific)
        result = conn.execute(text("SELECT column_name FROM information_schema.columns WHERE table_name='users' AND column_name='full_name';"))
        if result.fetchone():
            print("Column 'full_name' already exists.")
        else:
            print("Adding 'full_name' column...")
            conn.execute(text("ALTER TABLE users ADD COLUMN full_name VARCHAR(100);"))
            print("Column added.")
            
        print("Backfilling full_name with username...")
        conn.execute(text("UPDATE users SET full_name = username WHERE full_name IS NULL;"))
        conn.commit()
        print("Migration complete.")

if __name__ == "__main__":
    migrate()
