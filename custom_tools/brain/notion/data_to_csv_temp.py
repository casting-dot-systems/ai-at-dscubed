import csv

from data import USER_LIST

# Assuming UserData is already defined
# and notion_user_id_type / discord_user_id_type return plain strings


class UserData:
    def __init__(self, name: str, role: str, notion_id: str, discord_id: str):
        self.name = name
        self.role = role
        self.notion_id = notion_id
        self.discord_id = discord_id


# Your example list

# Writing to CSV
with open("user_list.csv", mode="w", newline="", encoding="utf-8") as csvfile:
    fieldnames = ["name", "role", "notion_id", "discord_id"]
    writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

    writer.writeheader()
    for user in USER_LIST:
        writer.writerow({
            "name": user.name,
            "role": user.role,
            "notion_id": user.notion_id,
            "discord_id": user.discord_id,
        })

print("CSV file 'user_list.csv' written successfully.")
