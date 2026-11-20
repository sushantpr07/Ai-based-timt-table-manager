"""
Fix script: institution_id mismatch + verify DB state
Run from project root.
"""
import sqlite3, os, sys

DAYLEAF_INST_ID = "5abab4d0d8bb4e22b160237de3bcd0e6"
USER_EMAIL = "sushantprakash2003@gmail.com"

dbs = ["campusflow-local.db", "apps/api/campusflow-local.db"]

for db_path in dbs:
    if not os.path.exists(db_path):
        print(f"SKIP (not found): {db_path}")
        continue
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    # Show current state
    cur.execute("SELECT email, institution_id, role FROM users WHERE email=?", (USER_EMAIL,))
    row = cur.fetchone()
    print(f"\n[{db_path}] BEFORE: {row}")

    # Fix institution_id
    cur.execute(
        "UPDATE users SET institution_id=? WHERE email=?",
        (DAYLEAF_INST_ID, USER_EMAIL)
    )
    conn.commit()

    cur.execute("SELECT email, institution_id, role FROM users WHERE email=?", (USER_EMAIL,))
    row = cur.fetchone()
    print(f"[{db_path}] AFTER:  {row}")

    # Verify institutions
    cur.execute("SELECT id, name FROM institutions")
    insts = cur.fetchall()
    print(f"[{db_path}] Institutions: {insts}")

    # Verify departments under Dayleaf
    cur.execute("SELECT name FROM departments WHERE institution_id=?", (DAYLEAF_INST_ID,))
    depts = [r[0] for r in cur.fetchall()]
    print(f"[{db_path}] Departments under Dayleaf: {depts}")

    # Verify terms
    cur.execute("SELECT name FROM academic_terms WHERE institution_id=?", (DAYLEAF_INST_ID,))
    terms = [r[0] for r in cur.fetchall()]
    print(f"[{db_path}] Terms under Dayleaf: {terms}")

    conn.close()

print("\nDone! Now restart the API and sign out + sign in again.")
