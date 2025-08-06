import psycopg2

def get_topic_id(crsr, table_name, topic):
    sql_command=f"""
    INSERT INTO "{table_name}" (topic_name)
    VALUES 
    ('{topic}')
    ON CONFLICT (topic_name) DO NOTHING;
    """
    crsr.execute(sql_command)
    
    sql_command=f"""
    SELECT topic_id FROM "{table_name}" WHERE topic_name = '{topic}'
    """
    crsr.execute(sql_command)
    topic_id = crsr.fetchone()[0]
    
    return topic_id
