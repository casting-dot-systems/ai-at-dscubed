# test database tool
import os
from dotenv import load_dotenv
from postgres import (DatabaseEngine,
                      set_initial_committee_personal_checkup,
                      get_latest_personal_checkup,
                      get_checkups_for_discord_id,
                      set_committee_personal_checkup,
                      set_personal_description)

load_dotenv()

engine = DatabaseEngine.get_engine()

# test database tool
if __name__ == "__main__":
    # set_initial_committee_personal_checkup(engine)
    # set_committee_personal_checkup(373796704450772992, "I am a test", '2025-07-05 12:00:00', engine)
    set_personal_description(373796704450772992, "I am a test personal description 2", engine)
    print(get_checkups_for_discord_id(373796704450772992, engine))
