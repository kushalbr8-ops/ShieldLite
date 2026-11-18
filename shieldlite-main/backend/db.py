import sqlite3
import time

conn = sqlite3.connect("shieldlite.db")
c = conn.cursor()

c.execute("""
CREATE TABLE IF NOT EXISTS attacks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp INTEGER,
    ip TEXT,
    payload TEXT,
    attack_type TEXT,
    blocked INTEGER
)
""")
conn.commit()

def log_attack(ip, payload, attack_type, blocked):
    c.execute("INSERT INTO attacks VALUES (NULL, ?, ?, ?, ?, ?)",
              (int(time.time()), ip, payload, attack_type, blocked))
    conn.commit()