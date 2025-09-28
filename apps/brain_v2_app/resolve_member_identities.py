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
          where full_name=%s
        """, (full_name))
        return cur.fetchall()

def link_identity(conn, member_id, system, external_id):
    with conn.cursor() as cur:
        cur.execute("""
          update catalog.member_identities
          set member_id=%s
          where system=%s and external_id=%s
        """, (member_id, system, external_id))
    conn.commit()

def search_by_username(conn, system: str, username: str):
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute("""
          select mi.system, mi.external_id, mi.external_username,
                 m.member_id, m.full_name
          from catalog.member_identities mi
          left join catalog.members m on m.member_id = mi.member_id
          where mi.system=%s and mi.external_username ilike %s
          order by m.full_name nulls last, mi.external_username
          limit 20
        """, (system, f"%{username}%"))
        return cur.fetchall()


def main():
    print("Identity Resolver — AI@DSCubed")
    print(HELP)
    with psycopg.connect(PG_DSN, row_factory=dict_row) as conn:
        while True:
            with conn.cursor(row_factory=dict_row) as cur:
                cur.execute("""
                  select system, external_id, external_username
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
            ext_username = row["external_username"]
            prompt = (
                f'null member for identity: "{ext_id}"'
                f'{f" (username: {ext_username})" if ext_username else ""}, system: "{system}". '  # <<< fix var name
                f'Enter Full Name to assign member_id (or type /u <username> to search, ">>" to skip, ":q" to quit): '
            )
            full_name = input(prompt).strip()
            if full_name == ":q":
                print("Exiting.")
                return
            if full_name == ">>":
                continue
            if full_name.startswith("/u "):
                q = full_name[3:].strip()
                hits = search_by_username(conn, system, q)
                if not hits:
                    print("  (no matches by username)")
                else:
                    for h in hits:
                        owner = h["full_name"] or "UNASSIGNED"
                        print(f'  - {h["external_username"]} [{h["external_id"]}] → {owner}')
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
