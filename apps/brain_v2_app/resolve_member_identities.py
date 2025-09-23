# resolve_identities.py
import os, sys
import psycopg
from psycopg.rows import dict_row
from dotenv import load_dotenv
load_dotenv()

PG_DSN = os.getenv("DATABASE_URL")
ORG_ID = os.getenv("ORG_ID", "AI@DSCubed")

HELP = """
Type the FULL NAME to link identity → member.
- If the member exists, we will link this identity to that member_id.
- If not found, you'll be prompted again.
- Type '>>' to skip this identity for now.
- Type ':q' to quit.
"""

def find_member(conn, full_name: str):
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute("""
          select member_id, full_name from catalog.members
          where org_id=%s and full_name ilike %s
          order by updated_at desc
        """, (ORG_ID, full_name))
        return cur.fetchall()

def link_identity(conn, member_id, system, external_id):
    with conn.cursor() as cur:
        cur.execute("""
          update catalog.member_identities
          set member_id=%s
          where system=%s and external_id=%s
        """, (member_id, system, external_id))
    conn.commit()

def main():
    print("Identity Resolver — AI@DSCubed")
    print(HELP)
    with psycopg.connect(PG_DSN, row_factory=dict_row) as conn:
        while True:
            with conn.cursor(row_factory=dict_row) as cur:
                cur.execute("""
                  select system, external_id
                  from catalog.member_identities
                  where member_id is null
                  order by system, external_id
                  limit 1
                """)
                row = cur.fetchone()
            if not row:
                print("✅ No unresolved identities.")
                break

            system = row["system"]
            ext_id = row["external_id"]
            prompt = f'null member for identity: "{ext_id}", system: "{system}". Enter Full Name to assign member_id: '
            full_name = input(prompt).strip()
            if full_name == ":q":
                print("Exiting.")
                break
            if full_name == ">>":
                continue
            if not full_name:
                continue

            matches = find_member(conn, full_name)
            if not matches:
                print(f'  ❌ No member with full_name like "{full_name}". Try again or create the member first.')
                continue
            if len(matches) > 1:
                print("  Multiple matches:")
                for i, m in enumerate(matches, 1):
                    print(f"   {i}. {m['full_name']} ({m['member_id']})")
                sel = input("Select number to link, or '>>' to skip: ").strip()
                if sel == ">>":
                    continue
                try:
                    idx = int(sel) - 1
                    member_id = matches[idx]["member_id"]
                except Exception:
                    print("  Invalid selection.")
                    continue
            else:
                member_id = matches[0]["member_id"]

            link_identity(conn, member_id, system, ext_id)
            print(f"  ✅ Linked {system}:{ext_id} → {member_id}")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nInterrupted.")
        sys.exit(1)
