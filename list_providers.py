import sqlite3, json
conn = sqlite3.connect('instance/scholarsphere.db')
conn.row_factory = sqlite3.Row
rows = conn.execute("SELECT id, first_name, last_name, email, organization, role FROM users WHERE role='provider' ORDER BY id").fetchall()
print(json.dumps([dict(r) for r in rows], indent=2))
