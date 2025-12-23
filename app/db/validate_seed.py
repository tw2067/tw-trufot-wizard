from app.db.database import get_conn

def main():
    conn = get_conn()
    cur = conn.cursor()

    checks = {
        "patients": "SELECT COUNT(*) FROM patients",
        "medications": "SELECT COUNT(*) FROM medications",
        "inventory": "SELECT COUNT(*) FROM inventory",
        "prescriptions": "SELECT COUNT(*) FROM prescriptions",
        "interaction_rules": "SELECT COUNT(*) FROM interaction_rules",
    }

    for name, q in checks.items():
        n = cur.execute(q).fetchone()[0]
        print(f"{name}: {n}")

    # critical demo checks
    med001 = cur.execute(
        "SELECT qty_on_hand FROM inventory WHERE med_id='MED001'"
    ).fetchone()[0]
    med002 = cur.execute(
        "SELECT qty_on_hand FROM inventory WHERE med_id='MED002'"
    ).fetchone()[0]

    print("MED001 qty:", med001)
    print("MED002 qty:", med002)

    conn.close()

if __name__ == "__main__":
    main()