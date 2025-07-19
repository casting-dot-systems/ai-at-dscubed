from sentence_transformers import SentenceTransformer, util


def topic_shift_splitter(transcript: str) -> list[str]:
    model = SentenceTransformer('all-MiniLM-L6-v2')

    # Input processing
    transcript=transcript.replace("...","--")
    chunks=transcript.split(".")
    while "" in chunks:
        chunks.remove("")

    # Sentence transforming
    embeddings = model.encode(chunks)
    similarities = [util.cos_sim(embeddings[i], embeddings[i+1]).item() for i in range(len(embeddings)-1)]

    # Threshold-based detection
    threshold = 0.05
    topic_shifts = [i+1 for i, sim in enumerate(similarities) if sim < threshold]

    # Groups sentences based on topics
    result=[".".join(chunks[0:topic_shifts[0]])]
    for i in range(1,len(topic_shifts)):
        result.append(".".join(chunks[topic_shifts[i-1]:topic_shifts[i]]))
    result.append(".".join(chunks[topic_shifts[len(topic_shifts)-1]:]))

    # Write splitted sections to output file to test
    #file=open("samples/test_out.txt","w")
    #for content in result:
    #    file.write(content + '\n\n')

    return result