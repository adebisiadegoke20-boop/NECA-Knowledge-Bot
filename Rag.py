import os
import re
import time
from dotenv import load_dotenv
from groq import Groq, RateLimitError
from supabase import create_client

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

# Term Lists
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

VENUE_TERMS = [
    "venue rental", "venue rentals", "neca house", "auditorium",
    "bauchi hall", "kano hall", "event centre", "halls", "booking contact",
    "pricing", "rates", "lagos venue", "abuja room", "enugu room"
]

# Combined Source Groups
SOURCE_GROUPS = [
    (FEE_TERMS, ["membership-fees"]),
    (REQUIREMENT_TERMS, ["membership-requirements"]),
    (BENEFIT_TERMS, ["benefits-of-membership"]),
    (CONTACT_TERMS, ["contacts"]),
    (ACADEMY_TERMS, ["necaictacademy.org/courses"]),
    (TRAINING_TERMS, ["learning-and-development-department"]),
    (HISTORY_TERMS, ["who-we-are", "faq"]),
    (TALENT_TERMS, ["neca-talent-network"]),
    (VENUE_TERMS, ["eventcentre.neca.org.ng/detailed-pricing", "event-centre"])
]

print("System Initialized")
print("Connected to Supabase")
print("Groq Client Ready")

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
        if question_has_any(q, ["minimum workforce", "minimum workers", "minimum employees"]):
            if any(term in content for term in ["minimum of 5 workers", "5 employees", "five employees", "5 workers"]):
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

    if question_has_any(q, VENUE_TERMS):
        if any(term in source for term in ["eventcentre", "event-centre"]):
            score += 80
        if any(term in content for term in ["auditorium", "bauchi hall", "kano hall", "event centre"]):
            score += 20

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
    combined = {}

    # Target specific source groups
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
                doc["similarity"] = None
                combined[key] = doc

        except Exception as exc:
            print("Could not search source", source_name, ":", exc)

    # General search fallback if no targeted source was matched
    if not combined:
        try:
            response = (
                supabase.table("neca_documents")
                .select("id,title,content,source,page_number")
                .limit(50)
                .execute()
            )
            for raw_doc in response.data or []:
                doc = dict(raw_doc)
                combined[_doc_key(doc)] = doc
        except Exception as exc:
            print("Fallback query failed:", exc)

    documents = list(combined.values())

    for doc in documents:
        doc["keyword_score"] = keyword_relevance(doc, question)
        doc["combined_score"] = doc["keyword_score"]

    documents.sort(
        key=lambda doc: doc.get("combined_score", 0),
        reverse=True
    )

    selected = []
    seen_chunks = set()
    per_source_count = {}

    for doc in documents:
        content_key = normalize_text(doc.get("content", ""))
        if not content_key or content_key in seen_chunks:
            continue

        source = str(doc.get("source", "Unknown source"))
        source_count = per_source_count.get(source, 0)

        if source_count >= 3:
            continue

        seen_chunks.add(content_key)
        per_source_count[source] = source_count + 1
        selected.append(doc)

        if len(selected) >= top_k:
            break

    print("Found", len(selected), "relevant chunks")
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

"If the user specifies a particular location (such as Lagos), 
only report the venues and details relevant to that location."

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
        return {"answer": answer, "sources": []}

    answer = rag_generate(question, documents)

    sources = []
    seen_sources = set()

    for doc in documents:
        source_url = doc.get("source", "Unknown source")
        chunk_number = doc.get("page_number", "Unknown")
        key = (source_url, str(chunk_number))

        if key in seen_sources:
            continue

        seen_sources.add(key)
        source_info = {
            "organisation": doc.get("title", "NECA"),
            "source": source_url,
            "chunk": chunk_number,
            "match_type": "source/keyword match"
        }
        sources.append(source_info)

    return {"answer": answer, "sources": sources}


# --- INGESTION HELPER FUNCTION ---
def ingest_txt_file(file_path="neca_data.txt"):
    """Reads the scraped text file and upserts pages directly into Supabase."""
    if not os.path.exists(file_path):
        print(f"Error: {file_path} not found. Run your scraper first!")
        return {"status": "error", "message": f"{file_path} not found."}

    print(f"Reading {file_path} for ingestion...")
    with open(file_path, "r", encoding="utf-8") as f:
        full_text = f.read()

    # Split the file by the ORGANISATION marker to cleanly isolate each page block
    blocks = full_text.split("ORGANISATION:")
    success_count = 0
    
    for block in blocks:
        block = block.strip()
        if not block:
            continue
            
        lines = block.splitlines()
        org_name = lines[0].strip() if lines else "NECA"
        page_url = "Unknown Source"
        content_lines = []
        
        # Look through the block lines to find the PAGE: header and separate content
        is_content = False
        for line in lines[1:]:
            line_str = line.strip()
            if line_str.startswith("PAGE:"):
                page_url = line_str.replace("PAGE:", "").strip()
                continue
            if "================================================================================" in line_str:
                is_content = True
                continue
            if is_content:
                content_lines.append(line)

        content_text = "\n".join(content_lines).strip()
        if not content_text:
            # Fallback if block structure differs slightly
            content_text = "\n".join(lines[2:]).strip()
            if not content_text:
                continue

        doc_data = {
            "title": f"{org_name} - Page Content",
            "content": content_text,
            "source": page_url,
            "page_number": 1
        }

        try:
            # Clear old records for this URL to prevent duplicates
            supabase.table("neca_documents").delete().eq("source", page_url).execute()
            
            # Insert fresh content
            supabase.table("neca_documents").insert(doc_data).execute()
            print(f"Successfully ingested: {page_url}")
            success_count += 1
        except Exception as e:
            print(f"Failed to ingest {page_url}: {e}")

    print(f"\nIngestion complete! Successfully added {success_count} pages to Supabase.")
    return {"status": "success", "ingested_count": success_count}

if __name__ == "__main__":
    # Optional: Run ingestion when executing rag.py directly
    ingest_txt_file()