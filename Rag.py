from supabase import create_client
from sentence_transformers import SentenceTransformer
from groq import Groq
import os
from dotenv import load_dotenv

load_dotenv()

# Connect to Supabase
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_SERVICE_KEY = os.environ.get("SUPABASE_SERVICE_KEY")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")

supabase = create_client(
    SUPABASE_URL,
    SUPABASE_SERVICE_KEY
)

embedding_model = SentenceTransformer("all-MiniLM-L6-v2")
groq_client = Groq(api_key=GROQ_API_KEY)

print("System Initialized")
print("Connected to Supabase")
print("Embedding Model Loaded")
print("Groq Client Ready")


# Document Processing
def chunk_text(text, chunk_size=500, overlap=50):

    chunks = []
    start = 0

    while start < len(text):

        end = min(
            start + chunk_size,
            len(text)
        )

        if end < len(text):

            last_period = text.rfind(
                ".",
                start,
                end
            )

            if last_period > start + chunk_size // 2:
                end = last_period + 1

        chunk = text[start:end].strip()

        if len(chunk) > 20:
            chunks.append(chunk)

        new_start = end - overlap

        if new_start <= start:
            new_start = end

        start = new_start

    return chunks


# Load NECA scraped data
def load_neca_data():

    print()
    print("Loading NECA scraped data...")
    print("-" * 40)

    with open(
        "neca_data.txt",
        "r",
        encoding="utf-8"
    ) as file:

        text = file.read()

    print(
        "Loaded",
        len(text),
        "characters"
    )

    return text


# Separate scraped pages
def parse_pages(text):

    pages = []
    sections = text.split("=" * 80)

    current_organisation = ""
    current_page = ""

    for section in sections:
        lines = section.strip().splitlines()

        if not lines:
            continue

        content_lines = []

        for line in lines:
            if line.startswith("ORGANISATION:"):

                current_organisation = (
                    line.replace(
                        "ORGANISATION:",
                        ""
                    ).strip()
                )

            elif line.startswith("PAGE:"):

                current_page = (
                    line.replace(
                        "PAGE:",
                        ""
                    ).strip()
                )

            elif line.strip():

                content_lines.append(line.strip())

        content = "\n".join(content_lines).strip()

        if content and current_page:

            pages.append({
                "organisation": current_organisation,
                "page": current_page,
                "content": content
            })

    return pages


# Ingest NECA data
def ingest_neca_document():

    text = load_neca_data()

    print()
    print("Identifying scraped pages...")
    print("-" * 40)

    pages = parse_pages(text)

    print(
        "Found",
        len(pages),
        "scraped pages"
    )

    total_chunks = 0

    for page in pages:

        organisation = page["organisation"]
        source = page["page"]
        content = page["content"]

        print()
        print(
            "Processing:",
            organisation
        )

        print(
            "Source:",
            source
        )

        chunks = chunk_text(content)

        print(
            "Created",
            len(chunks),
            "chunks"
        )

        for i, chunk in enumerate(chunks):

            embedding = (
                embedding_model
                .encode(chunk)
                .tolist()
            )

            supabase.table(
                "neca_documents"
            ).insert({

                "title": organisation,

                "content": chunk,

                "source": source,

                "page_number": i + 1,

                "embedding": embedding

            }).execute()

            total_chunks += 1

    print()
    print(
        "Stored",
        total_chunks,
        "chunks in Supabase"
    )

    return total_chunks


# RAG Search
def rag_search(question, top_k=5):

    query_embedding = (
        embedding_model
        .encode(question)
        .tolist()
    )

    # Vector similarity search
    results = supabase.rpc(
        "match_neca_documents",
        {
            "query_embedding": query_embedding,
            "match_threshold": 0.30,
            "match_count": top_k
        }
    ).execute()

    vector_results = results.data or []

    # Keyword-based source matching
    question_lower = question.lower()

    source_keywords = {

        "membership requirements": [
            "membership-requirements"
        ],

        "becoming a neca member": [
            "membership-requirements"
        ],

        "requirements for becoming": [
            "membership-requirements"
        ],

        "benefits of membership": [
            "benefits-of-membership"
        ],

        "membership fees": [
            "membership-fees"
        ],

        "abuja office": [
            "contacts"
        ],

        "abuja address": [
            "contacts"
        ],

        "contact neca": [
            "contacts"
        ],

        "neca courses": [
            "necaictacademy.org/courses"
        ],

        "courses offered": [
            "necaictacademy.org/courses"
        ],

        "courses are offered": [
            "necaictacademy.org/courses"
        ],

        "ict academy courses": [
            "necaictacademy.org/courses"
        ],
        
        "lagos office": [
            "contacts"
        ],
        "lagos address": [
            "contacts"
        ],
        "neca lagos office": [
            "contacts"
        ],
        "head office": [
            "contacts"
        ],

        "where is neca located": [
            "contacts"
        ],
    }

    matching_sources = []

    for keyword, sources in source_keywords.items():

        if keyword in question_lower:

            matching_sources.extend(
                sources
            )

   
    # Retrieve relevant chunks from matching source pages
    keyword_results = []

    for source in matching_sources:
        source_query = (
            supabase
            .table("neca_documents")
            .select(
                "id,title,content,source,page_number"
            )
            .ilike(
                "source",
                f"%{source}%"
            )
            .limit(20)
            .execute()
        )

        if source_query.data:
            keyword_results.extend(
                source_query.data
            )

    # Prioritize chunks containing the requested location
    if any(
        keyword in question_lower
        for keyword in [
            "lagos office",
            "lagos address",
            "neca lagos",
            "head office"
        ]
    ):
        keyword_results.sort(
            key=lambda doc: (
                "lagos" in doc["content"].lower()
                or "ikeja" in doc["content"].lower()
            ),
            reverse=True
        )

    # Combine vector and keyword results
    combined = []

    seen_ids = set()

    for doc in vector_results:

        if doc["id"] not in seen_ids:

            combined.append(doc)

            seen_ids.add(doc["id"])

    for doc in keyword_results:

        if doc["id"] not in seen_ids:

            doc["similarity"] = 1.0

            combined.append(doc)

            seen_ids.add(doc["id"])

    # Sort by relevance
    combined = sorted(
        combined,
        key=lambda x: x.get(
            "similarity",
            0
        ),
        reverse=True
    )

    return combined[:top_k]



# RAG Generate
def rag_generate(question, documents):

    context = ""

    for i, doc in enumerate(documents):

        context += (
            "Organisation: "
            + doc["title"]
            + "\n"
        )

        context += (
            "Source: "
            + doc["source"]
            + "\n"
        )

        context += (
            "Content:\n"
            + doc["content"]
            + "\n"
        )

        if i < len(documents) - 1:
            context += "\n---\n"

    response = groq_client.chat.completions.create(

        model="openai/gpt-oss-120b",

        messages=[

            {
                "role": "system",

                "content": """
You are a NECA Knowledge Assistant.

Answer questions ONLY using information
contained in the provided NECA documents.

Do not use outside knowledge.

Do not make up information.

If the provided documents do not contain
enough information to answer the question,
say exactly:

"I don't have enough information in the
provided NECA documents."

When answering, identify the relevant
organisation and source page.

Use this format:

[Source: organisation - page URL]

Keep answers clear and concise.
"""
            },

            {
                "role": "user",

                "content":
                    "Documents:\n"
                    + context
                    + "\n\nQuestion: "
                    + question
            }

        ],

        temperature=0.2
    )

    return response.choices[0].message.content


# Full RAG
def full_rag(question):

    print()
    print("Question:", question)
    print("-" * 50)

    print(
        "Searching for relevant NECA information..."
    )

    documents = rag_search(question)

    if not documents:

        print("No relevant documents found.")

        return {
            "answer":
                "I don't have enough information "
                "in the provided NECA documents.",
            "sources": []
        }

    print(
        "Found",
        len(documents),
        "relevant chunks"
    )

    for doc in documents:

        print(
            "-",
            doc["title"],
            "|",
            doc["source"],
            "| similarity:",
            round(
                doc["similarity"],
                3
            )
        )

    print()
    print("Generating answer...")

    answer = rag_generate(
        question,
        documents
    )

    print()
    print("Answer:")
    print(answer)

    print()
    print("Sources:")

    sources = []

    for doc in documents:

        source = {
            "organisation": doc["title"],
            "source": doc["source"],
            "chunk": doc["page_number"],
            "similarity": round(
                doc["similarity"],
                3
            )
        }

        sources.append(source)

        print(
            "-",
            source["organisation"],
            "|",
            source["source"],
            "| chunk",
            source["chunk"],
            "| similarity:",
            source["similarity"]
        )

    return {
        "answer": answer,
        "sources": sources
    }


# Store NECA documents
#print()
#print("=" * 50)
#print("NECA DOCUMENT INGESTION")
#print("=" * 50)
#ingest_neca_document()


# RAG Tests
print()
print("=" * 50)
print("NECA RAG TESTS")
print("=" * 50)


full_rag("What is NECA and when was it established?")
full_rag("What are the benefits of NECA membership?")
full_rag("What are the requirements for becoming a NECA member?")
full_rag("What training and learning development services does NECA provide?")
full_rag("Where is the NECA Abuja office located?")
full_rag("Where is the NECA Lagos office located?")
full_rag("What courses are offered by the NECA ICT Academy?")
full_rag("What hospital in Abuja provides free antenatal care?")