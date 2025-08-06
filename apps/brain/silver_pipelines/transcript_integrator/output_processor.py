import pandas as pd
import re
import openpyxl

def output_processor(meeting_summary: str):
    """
    Extracts topics and their descriptions from a structured meeting summary.
    
    Parameters:
    - meeting_summary (str): The full meeting summary as a string.
    
    Returns:
    - pd.DataFrame: DataFrame with columns ['topic_name', 'topic_description']
    """
    
    meeting_summary = meeting_summary.split("---")


    # Step 3: Clean and format entries
    data = []

    data.append(
        {
            "topic_name": "Meeting Info",
            "topic_description": meeting_summary[0]
        }
    )
    meeting_summary.pop(0)

    for content in meeting_summary:
        content=content.lstrip('\n')
        content = content.split("\n",1)
        data.append({
            "topic_name": content[0],
            "topic_description": content[1].lstrip('\n')
        })

        
    df_out=(pd.DataFrame(data))
    df_out.to_excel("output.xlsx", index=False)

    return df_out

file=open("summary.txt", "r")
meeting_summary = file.read()
file.close()
output_processor(meeting_summary)









