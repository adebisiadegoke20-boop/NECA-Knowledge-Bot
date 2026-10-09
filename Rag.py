
from supabase import create_client
from sentence_transformers import SentenceTransformer
from groq import Groq, RateLimitError
from dotenv import load_dotenv
import os
import re
import time

load_dotenv()

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_SERVICE_KEY = os.environ.get("SUPABASE_SERVICE_KEY")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")

if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
    raise ValueError("Check SUPABASE_URL and SUPABASE_SERVICE_KEY in .env")

if not GROQ_API_KEY:
    raise ValueError("Check GROQ_API_KEY in .env")

supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
groq_client = Groq(api_key=GROQ_API_KEY)
embedding_model = None


FEE_TERMS = [
    "membership fee", "membership fees", "membership cost",
    "cost of membership", "how much", "entrance fee",
    "annual subscription", "subscription fee", "erpf",
    "enterprise resource planning fund", "turnover band", "fee schedule"
]

REQUIREMENT_TERMS = [
    "membership requirements", "requirements for becoming",
    "become a neca member", "becoming a neca member",
    "minimum workforce", "minimum workers", "minimum employees",
    "eligibility", "eligible", "qualify", "membership application",
    "apply for membership", "join neca"
]

BENEFIT_TERMS = [
    "benefits of membership", "benefits of neca membership",
    "benefits of being a member", "advantages of membership", "why join neca"
]

CONTACT_TERMS = [
    "abuja office", "abuja address", "abuja branch", "lagos office",
    "lagos address", "lagos branch", "head office", "headquarters",
    "contact neca", "contact details", "where is neca located",
    "office address", "phone number", "email address"
]

ACADEMY_TERMS = [
    "ict academy", "neca ict", "ict academy courses",
    "academy courses", "courses at the academy"
]

TRAINING_TERMS = [
    "training courses", "training and learning", "learning and development",
    "vocational training", "professional training", "skills training",
    "courses offered by neca", "training programmes", "training programs"
]

HISTORY_TERMS = [
    "what is neca", "meaning of neca", "full meaning of neca",
    "when was neca established", "when was neca formed",
    "history of neca", "about neca", "neca founded"
]

TALENT_TERMS = [
    "talent network", "neca talent network", "talent management", "recruitment"
]

SOURCE_GROUPS = [
    (FEE_TERMS, ["membership-fees"]),
    (REQUIREMENT_TERMS, ["membership-requirements"]),
    (BENEFIT_TERMS, ["benefits-of-membership"]),
    (CONTACT_TERMS, ["contacts"]),
    (ACADEMY_TERMS, ["necaictacademy.org/courses"]),
    (TRAINING_TERMS, ["learning-and-development-department"]),
    (HISTORY_TERMS, ["who-we-are", "faq"]),
    (TALENT_TERMS, ["neca-talent-network"])
]


def get_embedding_model():
    global embedding_model

    if embedding_model is None:
        print("Loading embedding model...")
        embedding_model = SentenceTransformer("all-MiniLM-L6-v2")

    return embedding_model


print("System Initialized")
print("Connected to Supabase")
print("Embedding model will load when needed")
print("Groq Client Ready")


def chunk_text(text, chunk_size=500, overlap=50):
    if chunk_size <= overlap:
        raise ValueError("chunk_size must be greater than overlap")

    text = (text or "").strip()
    chunks = []
    start = 0

    while start < len(text):
        end = min(start + chunk_size, len(text))

        if end < len(text):
            split_at = text.rfind(" ", start + chunk_size // 2, end)

            if split_at > start:
                end = split_at

        chunk = text[start:end].strip()

        if len(chunk) > 20:
            chunks.append(chunk)

        if end >= len(text):
            break

        start = max(end - overlap, start + 1)

    return chunks


def load_neca_data():
    with open("neca_data.txt", "r", encoding="utf-8") as file:
        return file.read()


def parse_pages(text):
    pages = []

    for section in text.split("=" * 80):
        lines = section.strip().splitlines()

        if not lines:
            continue

        organisation = "NECA"
        page_url = ""
        content_lines = []

        for line in lines:
            line = line.strip()

            if line.startswith("ORGANISATION:"):
                organisation = line.split(":", 1)[1].strip()

            elif line.startswith("PAGE:"):
                page_url = line.split(":", 1)[1].strip()

            elif line:
                content_lines.append(line)

        content = "\n".join(content_lines).strip()

        if content and page_url:
            pages.append({
                "organisation": organisation,
                "page": page_url,
                "content": content
            })

    return pages


# Run manually only when adding new scraped pages.
# Running this again inserts duplicate chunks.
def ingest_neca_document():
    pages = parse_pages(load_neca_data())
    model = get_embedding_model()
    total_chunks = 0

    print("Found", len(pages), "pages")

    for page in pages:
        chunks = chunk_text(page["content"])
        print("Processing:", page["page"], "| chunks:", len(chunks))

        for index, chunk in enumerate(chunks, start=1):
            embedding = model.encode(chunk).tolist()

            supabase.table("neca_documents").insert({
                "title": page["organisation"],
                "content": chunk,
                "source": page["page"],
                "page_number": index,
                "embedding": embedding
            }).execute()

            total_chunks += 1

    print("Stored", total_chunks, "chunks")
    return total_chunks


def normalize_text(text):
    text = str(text or "").lower()
    text = re.sub(r"[^a-z0-9₦./\-\s]", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def question_has_any(question, phrases):
    question = normalize_text(question)

    for phrase in phrases:
        phrase = normalize_text(phrase)

        if phrase and re.search(
            r"(?<![a-z0-9])" + re.escape(phrase) + r"(?![a-z0-9])",
            question
        ):
            return True

    return False


def identify_relevant_sources(question):
    sources = []

    for terms, matching_sources in SOURCE_GROUPS:
        if question_has_any(question, terms):
            sources.extend(matching_sources)

    return list(dict.fromkeys(sources))


def keyword_relevance(doc, question):
    q = normalize_text(question)
    content = normalize_text(doc.get("content", ""))
    source = normalize_text(doc.get("source", ""))
    score = 0

    if question_has_any(q, FEE_TERMS):
        if "membership-fees" in source:
            score += 70

        if "membership-requirements" in source:
            score -= 25

        if "turnover" in q and "turnover" in content:
            score += 12

        if "entrance fee" in q and "entrance fee" in content:
            score += 12

        if question_has_any(q, ["annual subscription", "subscription fee"]):
            if "subscription" in content:
                score += 12

        if question_has_any(q, ["erpf", "enterprise resource planning fund"]):
            if "erpf" in content or "enterprise resource planning fund" in content:
                score += 12

    if (
        question_has_any(q, REQUIREMENT_TERMS)
        and not question_has_any(q, FEE_TERMS)
    ):
        if "membership-requirements" in source:
            score += 65

        if "membership-fees" in source:
            score -= 20

        if question_has_any(q, [
            "minimum workforce", "minimum workers", "minimum employees"
        ]):
            if any(term in content for term in [
                "minimum of 5 workers", "5 employees",
                "five employees", "5 workers"
            ]):
                score += 15

    if question_has_any(q, BENEFIT_TERMS):
        if "benefits-of-membership" in source:
            score += 60

    if question_has_any(q, CONTACT_TERMS):
        if "contacts" in source:
            score += 60

        if "abuja" in q and "abuja" in content:
            score += 15

        if "lagos" in q and ("lagos" in content or "ikeja" in content):
            score += 15

    if question_has_any(q, ACADEMY_TERMS):
        if "necaictacademy.org/courses" in source:
            score += 70

        if "learning-and-development-department" in source:
            score -= 25

    if (
        question_has_any(q, TRAINING_TERMS)
        and not question_has_any(q, ACADEMY_TERMS)
    ):
        if "learning-and-development-department" in source:
            score += 60

        if "necaictacademy.org/courses" in source:
            score -= 20

    if question_has_any(q, HISTORY_TERMS):
        if "who-we-are" in source or "faq" in source:
            score += 45

    if question_has_any(q, TALENT_TERMS):
        if "neca-talent-network" in source:
            score += 60

    stop_words = {
        "what", "when", "where", "which", "does", "have", "with",
        "from", "that", "this", "how", "can", "the", "and", "for",
        "are", "was", "who", "my", "is", "a", "of", "to", "in",
        "on", "it", "by"
    }

    terms = {
        word for word in q.split()
        if len(word) > 3 and word not in stop_words
    }

    score += min(sum(1 for word in terms if word in content), 10)

    return score


def _doc_key(doc):
    doc_id = doc.get("id")

    if doc_id is not None:
        return "id:" + str(doc_id)

    source = str(doc.get("source", ""))
    page_number = str(doc.get("page_number", ""))
    content = normalize_text(doc.get("content", ""))

    return "text:" + source + "|" + page_number + "|" + content[:250]


def rag_search(question, top_k=5):
    if not question or not question.strip():
        return []

    print("Searching for relevant NECA information...")

    model = get_embedding_model()
    query_embedding = model.encode(question).tolist()
    combined = {}

    try:
        response = supabase.rpc(
            "match_neca_documents",
            {
                "query_embedding": query_embedding,
                "match_threshold": 0.30,
                "match_count": max(top_k * 3, 15)
            }
        ).execute()

        for raw_doc in response.data or []:
            doc = dict(raw_doc)
            similarity = doc.get("similarity")

            if similarity is None:
                similarity = doc.get("similarity_score")

            doc["similarity"] = (
                float(similarity) if similarity is not None else None
            )

            combined[_doc_key(doc)] = doc

    except Exception as exc:
        print("Vector search failed:", exc)

    for source_name in identify_relevant_sources(question):
        try:
            response = (
                supabase.table("neca_documents")
                .select("id,title,content,source,page_number")
                .ilike("source", "%" + source_name + "%")
                .limit(30)
                .execute()
            )

            for raw_doc in response.data or []:
                doc = dict(raw_doc)
                key = _doc_key(doc)

                if key in combined:
                    doc["similarity"] = combined[key].get("similarity")
                else:
                    doc["similarity"] = None

                combined[key] = doc

        except Exception as exc:
            print("Could not search source", source_name, ":", exc)

    documents = list(combined.values())

    for doc in documents:
        doc["keyword_score"] = keyword_relevance(doc, question)
        doc["combined_score"] = doc["keyword_score"]

        similarity = doc.get("similarity")

        if similarity is not None:
            doc["combined_score"] += similarity * 20

    documents.sort(
        key=lambda doc: doc.get("combined_score", 0),
        reverse=True
    )

    targeted_sources = identify_relevant_sources(question)

    if targeted_sources:
        matching = [
            doc for doc in documents
            if any(
                source_name in normalize_text(doc.get("source", ""))
                for source_name in targeted_sources
            )
        ]

        other_vector_results = [
            doc for doc in documents
            if doc not in matching and doc.get("similarity") is not None
        ]

        documents = matching + other_vector_results

    selected = []
    seen_chunks = set()
    per_source_count = {}

    for doc in documents:
        content_key = normalize_text(doc.get("content", ""))

        if not content_key or content_key in seen_chunks:
            continue

        source = str(doc.get("source", "Unknown source"))
        source_count = per_source_count.get(source, 0)

        # Prevent one page from taking up all the available context.
        if source_count >= 3:
            continue

        seen_chunks.add(content_key)
        per_source_count[source] = source_count + 1
        selected.append(doc)

        if len(selected) >= top_k:
            break

    print("Found", len(selected), "relevant chunks")

    for doc in selected:
        similarity = doc.get("similarity")

        if similarity is None:
            match_info = "keyword/source match"
        else:
            match_info = "similarity: " + str(round(similarity, 3))

        print(
            "-",
            doc.get("title", "NECA"),
            "|",
            doc.get("source", "Unknown source"),
            "|",
            match_info,
            "| keyword score:",
            doc.get("keyword_score", 0)
        )

    return selected


def rag_generate(question, documents):
    if not documents:
        return "I don't have enough information in the provided NECA documents."

    context_parts = []

    for doc in documents:
        context_parts.append(
            "Organisation: " + str(doc.get("title", "NECA")) + "\n"
            + "Source: " + str(doc.get("source", "Unknown source")) + "\n"
            + "Content:\n" + str(doc.get("content", "")) + "\n"
        )

    context = "\n---\n".join(context_parts)

    system_prompt = """
You are a NECA Knowledge Assistant.

Answer using only the supplied document excerpts. Do not use outside knowledge
or invent dates, prices, addresses, requirements, contact details or course names.

For membership fees, report only figures and turnover bands actually present
in the excerpts. If the fee information is incomplete or conflicting, say so.
Do not fill in missing amounts or imply that a partial table is complete.

Keep NECA Learning and Development programmes separate from NECA ICT Academy
courses.

If the documents do not contain enough information, say:
"I don't have enough information in the provided NECA documents."

Give a clear, direct answer. Include relevant source URLs when available.
Do not use a source to support a claim unless its excerpt supports that claim.
"""

    for attempt in range(3):
        try:
            response = groq_client.chat.completions.create(
                model="openai/gpt-oss-120b",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {
                        "role": "user",
                        "content": "Document excerpts:\n" + context
                        + "\nQuestion: " + question
                    }
                ],
                temperature=0.1,
                max_tokens=800
            )

            answer = response.choices[0].message.content

            if answer:
                return answer.strip()

            return "I don't have enough information in the provided NECA documents."

        except RateLimitError as exc:
            if attempt < 2:
                wait_time = 2 ** (attempt + 1)
                print("Rate limit reached. Retrying in", wait_time, "seconds.")
                time.sleep(wait_time)
            else:
                print("Groq rate limit error:", exc)
                return (
                    "The answer service is temporarily rate-limited. "
                    "Please wait and try again."
                )

        except Exception as exc:
            print("Answer generation failed:", exc)
            return "I couldn't generate an answer right now. Please try again."

    return "The answer service is temporarily unavailable."


def full_rag(question):
    print()
    print("Question:", question)
    print("-" * 50)

    documents = rag_search(question)

    if not documents:
        answer = "I don't have enough information in the provided NECA documents."
        print(answer)
        return {"answer": answer, "sources": []}

    print()
    print("Generating answer...")

    answer = rag_generate(question, documents)

    print()
    print("Answer:")
    print(answer)
    print()
    print("Sources:")

    sources = []
    seen_sources = set()

    for doc in documents:
        source_url = doc.get("source", "Unknown source")
        chunk_number = doc.get("page_number", "Unknown")
        key = (source_url, str(chunk_number))

        if key in seen_sources:
            continue

        seen_sources.add(key)
        similarity = doc.get("similarity")

        source_info = {
            "organisation": doc.get("title", "NECA"),
            "source": source_url,
            "chunk": chunk_number,
            "similarity": (
                round(similarity, 3) if similarity is not None else None
            ),
            "match_type": (
                "vector match" if similarity is not None
                else "source/keyword match"
            )
        }

        sources.append(source_info)

        score_text = (
            "similarity: " + str(round(similarity, 3))
            if similarity is not None
            else "source/keyword match"
        )

        print(
            "-",
            source_info["organisation"],
            "|",
            source_url,
            "| chunk",
            chunk_number,
            "|",
            score_text
        )

    return {"answer": answer, "sources": sources}


if __name__ == "__main__":
    print()
    print("=" * 50)
    print("NECA RAG TESTS")
    print("=" * 50)

    test_questions = [
        "What is NECA and when was it established?",
        "What are the benefits of NECA membership?",
        "What are the requirements for becoming a NECA member?",
        "What is the minimum workforce required for membership?",
        "How much does NECA membership cost?",
        "What training and learning development services does NECA provide?",
        "Where is the NECA Abuja office located?",
        "Where is the NECA Lagos office located?",
        "What courses are offered by the NECA ICT Academy?",
        "What hospital in Abuja provides free antenatal care?"
    ]

    for index, question in enumerate(test_questions):
        full_rag(question)

        if index < len(test_questions) - 1:
            time.sleep(3)
