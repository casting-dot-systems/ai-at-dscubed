

def topic_generator(content : str, client) -> str:
    prompt = f"""
    Return a heading for the topic of the string.
    Start and end with ***
    {content}
    """

    messages = [
        {"role": "user", "content": f"{prompt}"}
    ]

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=messages
    )

    return response.choices[0].message.content
