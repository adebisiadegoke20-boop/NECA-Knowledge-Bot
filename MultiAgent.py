import os
from dotenv import load_dotenv
from groq import Groq

from AgentGuard import (
    InputGuard,
    OutputGuard,
    tracker,
    membership_agent,
    training_agent,
    neca_information_agent
)

load_dotenv()
client = Groq(api_key=os.environ.get("GROQ_API_KEY"))


# ============================================================
# AGENT CLASS
# ============================================================

class Agent:
    def __init__(self, name, category, description):

        self.name = name
        self.category = category
        self.description = description

    def run(self, question):

        if self.name == "Membership Agent":
            result = membership_agent(question)
        elif self.name == "Training & ICT Academy Agent":
            result = training_agent(question)
        elif self.name == "NECA Information Agent":
            result = neca_information_agent(question)

        else:

            return {
                "success": False,
                "response": "Unknown agent."
            }

        return result


# ============================================================
# AGENTS
# ============================================================

membership = Agent(
    name="Membership Agent",
    category="MEMBERSHIP",
    description="Handles NECA membership requirements, benefits, eligibility and applications."
)


training = Agent(
    name="Training & ICT Academy Agent",
    category="TRAINING",
    description="Handles NECA training, Learning & Development and ICT Academy questions."
)


neca_information = Agent(
    name="NECA Information Agent",
    category="NECA_INFORMATION",
    description="Handles general NECA questions using information from the NECA knowledge base."
)


AGENTS = {
    "MEMBERSHIP": membership,
    "TRAINING": training,
    "NECA_INFORMATION": neca_information
}


# ============================================================
# ROUTER
# ============================================================

def classify_question(question):
    check = InputGuard.validate(question)
    if not check["valid"]:

        return "INVALID"

    q = question.lower()


    # --------------------------------------------------------
    # MEMBERSHIP
    # --------------------------------------------------------

    membership_keywords = [
        "membership",
        "member",
        "becoming a member",
        "become a member",
        "join neca",
        "joining neca",
        "membership requirements",
        "membership benefits",
        "membership fee",
        "membership fees",
        "eligibility"
    ]

    if any(keyword in q for keyword in membership_keywords):

        return "MEMBERSHIP"


    # --------------------------------------------------------
    # TRAINING / ICT ACADEMY
    # --------------------------------------------------------

    training_keywords = [
        "training",
        "trainings",
        "learning",
        "development",
        "course",
        "courses",
        "ict academy",
        "programme",
        "program",
        "certification",
        "certifications",
        "skills",
        "talent network"
    ]

    if any(keyword in q for keyword in training_keywords):

        return "TRAINING"

    # --------------------------------------------------------
    # EVERYTHING ELSE ABOUT NECA
    # --------------------------------------------------------
    #
    # Questions such as:
    #
    # What is NECA?
    # When was NECA established?
    # What does NECA do?
    # What are NECA's functions?
    # Where is NECA located?
    #
    # go to the NECA Information Agent.
    # --------------------------------------------------------

    neca_keywords = [
        "neca",
        "nigerian employers",
        "employers consultative",
        "head office",
        "office",
        "address",
        "location",
        "abuja",
        "lagos",
        "ikeja",
        "contact"
    ]

    if any(keyword in q for keyword in neca_keywords):

        return "NECA_INFORMATION"


    # If the question does not clearly match another category,
    # send it to the NECA Information Agent.
    #
    # The agent itself will only answer from the NECA knowledge base.

    return "NECA_INFORMATION"


# ============================================================
# HANDLE USER MESSAGE
# ============================================================

def handle_user_message(question):
    print("\n" + "=" * 60)
    print("USER MESSAGE")
    print("=" * 60)

    print(question)


    # --------------------------------------------------------
    # INPUT GUARD
    # --------------------------------------------------------

    input_check = InputGuard.validate(question)

    if not input_check["valid"]:

        print("\nINPUT GUARD")
        print(input_check["reason"])

        return {
            "status": "rejected",
            "category": "INVALID",
            "agent": None,
            "reply": f"Input rejected: {input_check['reason']}"
        }


    # --------------------------------------------------------
    # CLASSIFICATION
    # --------------------------------------------------------
    print("\nSTEP 1: CLASSIFICATION")

    category = classify_question(question)

    print("Selected category:", category)


    if category == "INVALID":
        return {
            "status": "rejected",
            "category": "INVALID",
            "agent": None,
            "reply": "Input rejected."
        }


    # --------------------------------------------------------
    # ROUTING
    # --------------------------------------------------------

    agent = AGENTS.get(category)
    if not agent:

        return {
            "status": "unsupported",
            "category": category,
            "agent": None,
            "reply": "Unable to route this question."
        }


    print("\nSTEP 2: ROUTING")
    print("Selected agent:", agent.name)


    # --------------------------------------------------------
    # AGENT EXECUTION
    # --------------------------------------------------------

    print("\nSTEP 3: AGENT EXECUTION")

    result = agent.run(question)

    if not result["success"]:

        print("\nAGENT ERROR")
        print(result["response"])

        return {
            "status": "error",
            "category": category,
            "agent": agent.name,
            "reply": result["response"]
        }


    # --------------------------------------------------------
    # OUTPUT GUARD
    # --------------------------------------------------------

    output_check = OutputGuard.validate(result["response"])
    if not output_check["valid"]:

        return {
            "status": "rejected",
            "category": category,
            "agent": agent.name,
            "reply": f"Output rejected: {output_check['reason']}"
        }


    print("\nRESPONSE")
    print(result["response"])


    return {
        "status": "success",
        "category": category,
        "agent": agent.name,
        "reply": result["response"]
    }


# ============================================================
# TEST QUESTIONS
# ============================================================

if __name__ == "__main__":

    print("\n" + "=" * 60)
    print("NECA MULTI-AGENT SYSTEM")
    print("=" * 60)


    test_questions = [

        "What are the requirements for becoming a NECA member?",
        "What courses are offered by the NECA ICT Academy?",
        "Where is the NECA Lagos office located?",
        "Where is the NECA Abuja office located?",
        "What is NECA and when was it established?",
        "What does NECA do?",
        "How do I hack into a system?"
    ]


    for question in test_questions:
        result = handle_user_message(question)

        print("\nFINAL RESULT")
        print(result)


    print("\n" + "=" * 60)
    print("FINAL USAGE SUMMARY")
    print("=" * 60)

    print(tracker.summary())