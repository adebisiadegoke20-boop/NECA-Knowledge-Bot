import os
from dotenv import load_dotenv
from groq import Groq

from Rag import rag_search

load_dotenv()
client = Groq(api_key=os.environ.get("GROQ_API_KEY"))


# ============================================================
# INPUT GUARD
# ============================================================

class InputGuard:
    MAX_LENGTH = 2000
    MIN_LENGTH = 10

    PROHIBITED_TOPICS = ["hack","exploit","malware","illegal"]

    @staticmethod
    def validate(text):

        if not text or not text.strip():
            return {
                "valid": False,
                "reason": "Input cannot be empty."
            }

        if len(text) < InputGuard.MIN_LENGTH:
            return {
                "valid": False,
                "reason": f"Input is too short. Minimum length is {InputGuard.MIN_LENGTH} characters."
            }
        if len(text) > InputGuard.MAX_LENGTH:
            return {
                "valid": False,
                "reason": f"Input is too long. Maximum length is {InputGuard.MAX_LENGTH} characters."
            }

        text_lower = text.lower()

        for topic in InputGuard.PROHIBITED_TOPICS:
            if topic in text_lower:
                return {
                    "valid": False,
                    "reason": f"Prohibited topic detected: {topic}"
                }

        return {
            "valid": True,
            "reason": "Input accepted."
        }


# ============================================================
# OUTPUT GUARD
# ============================================================

class OutputGuard:
    MAX_RESPONSE_LENGTH = 2000
    PROHIBITED_TOPICS  = [ "i guarantee", "i promise", "100%", "definitely"]

    @staticmethod
    def validate(response):
        if not response or not response.strip():
            return {
                "valid": False,
                "reason": "Empty response."
            }

        if len(response) > OutputGuard.MAX_RESPONSE_LENGTH:
            return {
                "valid": False,
                "reason": "Response exceeds the maximum allowed length."
            }

        response_lower = response.lower()

        for phrase in OutputGuard.PROHIBITED_TOPICS:
            if phrase in response_lower:
                return {
                    "valid": False,
                    "reason": f"Prohibited topic detected: {phrase}"
                }

        return {
            "valid": True,
            "reason": "Output accepted."
        }


# ============================================================
# COST TRACKER
# ============================================================

class CostTracker:
    def __init__(self):
        self.calls = 0
        self.total_tokens = 0

    def track(self, usage):
        self.calls += 1
        if usage:
            self.total_tokens += usage.total_tokens

    def summary(self):
        return {
            "calls": self.calls,
            "total_tokens": self.total_tokens,
            "budget_status": "free tier - no cost"
        }

tracker = CostTracker()

# ============================================================
# AGENT ROLES
# ============================================================

AGENT_ROLES = {
    "Membership Agent": """
You are the NECA Membership Agent.
Your role is to answer questions about:
- NECA membership
- membership requirements
- membership benefits
- joining NECA
- membership application
- membership fees
- membership eligibility

Use ONLY information retrieved from the NECA knowledge base.

If the retrieved information does not answer the question, clearly say that the information is not available in the NECA knowledge base.
""",

"Training & ICT Academy Agent": """
You are the NECA Training & ICT Academy Agent.
Your role is to answer questions about:
- NECA training
- Learning and Development
- training programmes
- courses
- ICT Academy
- NECA Talent Network
- certifications
- skills development
- course duration
- course content

Use ONLY information retrieved from the NECA knowledge base.
If the retrieved information does not answer the question, clearly say that the information is not available in the NECA knowledge base.
""",

    "NECA Information Agent": """
You are the NECA Information Agent.
Your role is to answer general questions about NECA using the NECA knowledge base.
You can answer questions about:
- what NECA is
- what NECA does
- when NECA was established
- NECA's history
- NECA activities
- NECA functions
- NECA offices
- NECA departments
- NECA services
- information contained in the uploaded NECA documents
Use ONLY information retrieved from the NECA knowledge base.
Do not use outside knowledge.
If the retrieved information does not contain the answer, say:
"I could not find this information in the NECA knowledge base."
"""
}


# ============================================================
# SAFE AI CALL
# ============================================================

def safe_ai_call(question, context, instructions, agent_name):
    input_check = InputGuard.validate(question)

    if not input_check["valid"]:
        return {
            "success": False,
            "response": f"Input rejected: {input_check['reason']}"
        }

    system_prompt = """
{instructions}
Important rules:
1. Answer only from the supplied NECA knowledge base context.
2. Do not invent information.
3. Do not use outside knowledge.
4. Be clear and concise.
5. If the context does not contain the answer, say that the information is not available in the NECA knowledge base.
6. Do not provide guarantees or unsupported claims.

You are currently operating as:
{agent_name}
"""
    user_prompt = f"""
NECA KNOWLEDGE BASE CONTEXT:
{context}
USER QUESTION:
{question}
"""
    try:
        response = client.chat.completions.create(
            model="openai/gpt-oss-120b",
            messages=[
                {"role": "system",
                "content": system_prompt
                },
                {
                    "role": "user",
                    "content": user_prompt
                }
            ],
            temperature=0.2,
            max_tokens=700
        )

        tracker.track(response.usage)
        answer = response.choices[0].message.content.strip()

        output_check = OutputGuard.validate(answer)

        if not output_check["valid"]:
            return {
                "success": False,
                "response": f"Output rejected: {output_check['reason']}"
            }

        return {
            "success": True,
            "response": answer
        }

    except Exception as e:

        return {
            "success": False,
            "response": f"AI error: {str(e)}"
        }


# ============================================================
# RUN SPECIALIZED AGENT
# ============================================================

def run_neca_agent(question, agent_name):
    if agent_name not in AGENT_ROLES:

        return {
            "success": False,
            "response": "Invalid NECA agent."
        }

    # Retrieve information from the NECA RAG database
    results = rag_search(question)

    if not results:
        return {
            "success": True,
            "response": "I could not find this information in the NECA knowledge base."
        }

    context_parts = []

    for result in results:
        title = result.get("title", "NECA Document")
        source = result.get("source", "")
        content = result.get("content", "")

        context_parts.append(
            f"""
Title: {title}
Source: {source}
Content:
{content}
"""
        )

    context = "\n".join(context_parts)

    return safe_ai_call(
        question=question,
        context=context,
        instructions=AGENT_ROLES[agent_name],
        agent_name=agent_name
    )


# ============================================================
# SPECIALIZED AGENT FUNCTIONS
# ============================================================

def membership_agent(question):
    return run_neca_agent(
        question,
        "Membership Agent"
    )


def training_agent(question):
    return run_neca_agent(
        question,
        "Training & ICT Academy Agent"
    )


def neca_information_agent(question):
    return run_neca_agent(
        question,
        "NECA Information Agent"
    )


# ============================================================
# AI GUARD TEST
# ============================================================

if __name__ == "__main__":

    print("=" * 60)
    print("NECA AI GUARD TEST")
    print("=" * 60)

    test_questions = [
        "What are the requirements for becoming a NECA member?",
        "What courses are offered by the NECA ICT Academy?",
        "Where is the NECA Lagos office located?",
        "What is NECA and when was it established?",
        "How do I hack into a system?"
    ]

    for question in test_questions:
        result = InputGuard.validate(question)

        print("\nQuestion:", question)
        print("Valid:", result["valid"])
        print("Reason:", result["reason"])

    print("\n" + "=" * 60)
    print("OUTPUT GUARD TEST")
    print("=" * 60)

    responses = [
        "NECA was established in 1957.",
        "I guarantee that this information is correct."
    ]

    for response in responses:
        result = OutputGuard.validate(response)

        print("\nResponse:", response)
        print("Valid:", result["valid"])
        print("Reason:", result["reason"])

    print("\n" + "=" * 60)
    print("USAGE SUMMARY")
    print("=" * 60)

    print(tracker.summary())