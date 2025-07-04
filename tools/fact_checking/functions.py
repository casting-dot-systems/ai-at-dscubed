from typing import List

from llmgine.bus.bus import MessageBus
from llmgine.ui.cli.components import SelectPromptCommand
from tools.database.database import DatabaseEngine, set_user_fact, get_user_fact, delete_fact

def create_fact(discord_id: str, fact: str) -> str:
    """This function creates a fact in the database.
    
    Args:
        discord_id: The discord id of the user to create the fact for
        fact: The fact to create

    Returns:
        A message indicating that the fact was created or an error message
    """
    try:
        db = DatabaseEngine.get_engine()
        set_user_fact(discord_id, fact, db)
        return f"Created fact: {fact}"
    except Exception as e:
        return f"Error creating fact: {e}"


def delete_facts(discord_id: str, fact_id: str) -> str:
    """This function deletes a fact from the database.
    
    Args:
        discord_id: The discord id of the user to delete the facts for
        fact_id: The fact ID to delete

    Returns:
        A message indicating that the facts were deleted
    """
    try:
        db = DatabaseEngine.get_engine()
        delete_fact(discord_id, fact_id, db)
        return f"Deleted fact with ID: {fact_id}"
    except Exception as e:
        return f"Error deleting facts: {e}"

def get_all_facts(discord_id: str) -> str:
    """This function gets similar facts from the database.

    Args:
        discord_id: The discord id of the user to get the similar facts for
        keywords: A couple of keywords that are most representative of the fact, separated by spaces

    Returns:
        A message indicating that the fact was retrieved
    """

    db = DatabaseEngine.get_engine()
    facts = get_user_fact(discord_id, db)

    parsed_facts = []
    for fact in facts:
        parsed_facts.append({'fact_id':fact['fact_id'], 'fact_text':fact['fact_text']})

    if len(parsed_facts) == 0:
        return "No facts found"
    else:
        return f"All facts are: {parsed_facts}"

# Message bus and session id are hidden from the llm, we will insert them manually
async def send_to_judge(discord_id: str, new_fact: str, old_facts: list[str], old_fact_ids: list[str], session_id: str) -> str:
    """This function sends a fact to the judge.
    
    Args:
        discord_id: The discord id of the user creating the fact
        new_fact: The new fact to send
        old_facts: A list of existing facts to compare to, separated by '&'
        old_fact_ids: A list of existing fact ids to compare to, separated by '&'
        
    Returns:
        A message indicating that the fact was sent to the judge
    """

    old_facts_list = old_facts.split("&")
    old_fact_ids_list = old_fact_ids.split("&")
    old_facts_list = [f'{old_fact_ids_list[i]}: {old_facts_list[i]}' for i in range(len(old_facts_list))]
    old_facts_string = "\n".join(old_facts_list)

    message_bus = MessageBus()
    commandResult = await message_bus.execute(
        SelectPromptCommand(
            prompt=f'New fact: \n"{new_fact}"\n\nFacts to replace: \n"{old_facts_string}"\n\nSelect -1 to cancel.\nSelect 0 to create the fact.',
            title="Judge",
            session_id=session_id,
        )
    )
    result = commandResult.result
    if result == -1:
        return "The new fact should not be created."
    elif result == 0:
        create_fact(discord_id, new_fact)
        return f"Created {new_fact}"
    else:
        delete_facts(discord_id, result)
        create_fact(discord_id, new_fact)
        return f"Replaced with {new_fact}"

async def deletion_confirmation(discord_id: str, target_fact: str, similar_facts: list[str], similar_fact_ids: list[str], session_id: str) -> str:
    """This function gets a deletion confirmation from the user.
    
    Args:
        discord_id: The discord id of the user to delete the fact for
        target_fact: The fact to delete
        similar_facts: A list of similar facts to compare to, separated by '&'
        similar_fact_ids: A list of similar fact ids to compare to, separated by '&'

    Returns:
        A subset of similar_facts that the user wants to delete. 
    """

    similar_facts_list = similar_facts.split("&")
    similar_fact_ids_list = similar_fact_ids.split("&")
    similar_facts_list = [f'{similar_fact_ids_list[i]}: {similar_facts_list[i]}' for i in range(len(similar_facts_list))]
    similar_facts_string = "\n".join(similar_facts_list)

    message_bus = MessageBus()
    commandResult = await message_bus.execute(
        SelectPromptCommand(
            prompt=f'Target fact: \n"{target_fact}"\n\nSimilar facts: \n"{similar_facts_string}"\n\nSelect 0 to cancel.',
            title="Deletion Confirmation",
            session_id=session_id,
        )
    )
    result = commandResult.result
    if result == 0:
        return "No fact is deleted as the user cancelled the deletion."
    else:
        # Delete the fact from the database
        delete_facts(discord_id, result)
        return f"Deleted the fact"
    
def main():
    print(get_similar_facts("774065995508744232", ["color", "enjoy"]))

if __name__ == "__main__":
    main()

