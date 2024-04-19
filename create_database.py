import sqlite3

conn = sqlite3.connect('weight_progress.db')
cursor = conn.cursor()

try:
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS weight_measurements (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date DATE,
            fat_percentage FLOAT,
            muscle_percentage FLOAT,
            water_percentage FLOAT,
            weight FLOAT,
            age INTEGER,
            fat_mass FLOAT DEFAULT 0,
            muscle_mass FLOAT DEFAULT 0
        )
    ''')
    conn.commit()
finally:
    conn.close()