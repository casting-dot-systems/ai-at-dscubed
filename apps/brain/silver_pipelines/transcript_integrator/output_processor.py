import pandas as pd
import re
import openpyxl
from datetime import date
import psycopg2
from apps.brain.silver_pipelines.transcript_integrator.get_topic_id import get_topic_id
from sqlalchemy import create_engine



def output_processor(crsr, engine, meeting_summary: str, meeting_id, schema_name, topic_SQL_path):
    """
    Extracts topics and their descriptions from a structured meeting summary.
    
    Parameters:
    - crsr and engine are for the database 
    - meeting_summary (str): The full meeting summary as a string.
    - meeting_id
    - schema_name
    - topic_SQL_path - table name
    
    Returns:
    - pd.DataFrame: DataFrame with columns ['topic_name', 'topic_description']
    """

    crsr.execute(f'CREATE SCHEMA IF NOT EXISTS "{schema_name}";')
    conn.commit()
    
    sql_command=f"""
    CREATE TABLE IF NOT EXISTS "{schema_name}.{topic_SQL_path}" (
        "topic_id" SERIAL PRIMARY KEY,
        "topic_name" TEXT UNIQUE
    );
    """

    crsr.execute(sql_command)
    conn.commit()

    # assumes that each section is split by ---
    meeting_summary = meeting_summary.split("---")


    # Step 3: Clean and format entries
    data = []
    topic_id=get_topic_id(crsr, f"{schema_name}.{topic_SQL_path}","Meeting Info")

    data.append(
        {
            "topic_id":topic_id,
            "topic_name": 'Meeting Info',
            "topic_description": meeting_summary[0],
            "meeting_id": meeting_id,
            "ingestion_timestep": date.today()
        }
    )
    meeting_summary.pop(0)

    for content in meeting_summary:
        content=content.lstrip('\n')
        content=content.strip("###")
        content = content.split("\n",1)
        content[0] = re.sub(r"^\d+\.\s*", "", content[0].lstrip())
        content[0] = re.sub(r"\*", "", content[0])
        
        topic_id=get_topic_id(crsr, f"{schema_name}.{topic_SQL_path}",content[0])
        data.append({
            "topic_id":topic_id,
            "topic_name": content[0],
            "topic_description": content[1].lstrip('\n'),
            "meeting_id": meeting_id,
            "ingestion_timestep": date.today()
        })


        
    df_out=(pd.DataFrame(data))
    df_out.to_excel("output.xlsx", index=False)

    df_out.to_sql(
        name=topic_SQL_path,      # Table name (string)
        con=engine,               # SQLAlchemy engine
        schema=schema_name,       # Schema name (string)
        if_exists='append',       # Append to existing table
        index=False               # Don't write the DataFrame index
    )
    conn.commit()

    return df_out


## Connect to database
conn = psycopg2.connect(
    dbname="postgres",
    user="postgres",
    password="P0stgres",
    host="localhost",
    port="5432"
)
# cursor
crsr = conn.cursor()


# PostgreSQL URL format: postgresql+psycopg2://user:password@host:port/dbname
engine = create_engine('postgresql+psycopg2://postgres:P0stgres@localhost:5432/postgres')

file=open("summary2.txt", "r")
meeting_summary = file.read()
file.close()
output_processor(crsr, engine, meeting_summary, 10, "ai-at-dscubed-topic", "topics")









