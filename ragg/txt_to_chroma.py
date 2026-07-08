import chromadb
from langchain_text_splitters import RecursiveCharacterTextSplitter

# 1. Load your text
with open("public.md", "r", encoding="utf-8") as f:
    text = f.read()

# 2. Split into chunks
splitter = RecursiveCharacterTextSplitter(
    chunk_size=1000,      # characters per chunk
    chunk_overlap=200,    # overlap so context isn't lost at boundaries
    separators=["\n\n", "\n", ". ", " ", ""]  # tries paragraphs first, then sentences
)
chunks = splitter.split_text(text)
print(f"Split into {len(chunks)} chunks")

# 3. Set up persistent Chroma client (saves to disk, survives restarts)
client = chromadb.PersistentClient(path="./chroma_db")
collection = client.get_or_create_collection(name="public")

# 4. Add chunks in batches (Chroma auto-embeds using its default embedding function)
batch_size = 100
for i in range(0, len(chunks), batch_size):
    batch = chunks[i:i + batch_size]
    collection.add(
        documents=batch,
        ids=[f"chunk_{j}" for j in range(i, i + len(batch))],
        metadatas=[{"source": "public.txt", "chunk_index": j} for j in range(i, i + len(batch))]
    )

print("Done! Collection count:", collection.count())

# 5. Query it
results = collection.query(
    query_texts=["what  is social finance?"],
    n_results=3
)
for doc in results["documents"][0]:
    print(doc[:200], "\n---")
