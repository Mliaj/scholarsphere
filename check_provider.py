import sqlite3
conn = sqlite3.connect('instance/scholarsphere.db')
cur = conn.cursor()
cur.execute("SELECT id, first_name, last_name, email, role, organization, LENGTH(password_hash) FROM users WHERE email=?", ('gayo@uc.edu',))
print(cur.fetchone())
