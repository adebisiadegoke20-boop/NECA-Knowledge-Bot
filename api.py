from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from httpx import request
from pydantic import BaseModel, Field
from dotenv import load_dotenv
import os

from MultiAgent import handle_user_message

load_dotenv()

app = FastAPI(title="NECA Knowledge Bot API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"]
)

print("NECA API Client Ready")


# API REQUEST MODEL
class CustomerMessage(BaseModel):
    message: str = Field(
        ...,
        min_length=1,
        max_length=2000,
        description="Question about NECA"
    )
# SUPPORT ENDPOINT

@app.post("/support")
def handle_customer_message(request: CustomerMessage):
    try:
        message = request.message.strip()

        if not message:
            raise HTTPException(
                status_code=400,
                detail="Please enter a question."
            )

        # Send the question to the existing multi-agent system.
        # This system performs input validation, routing,
        # RAG retrieval, agent execution and output validation.
        result = handle_user_message(message)

        status = result.get("status", "error")

        return {
            "success": status == "success",
            "status": status,
            "category": result.get("category"),
            "agent": result.get("agent"),
            "reply": result.get(
                "reply",
                "The system could not generate a response."
            )
        }

    except HTTPException:
        raise

    except Exception as e:
        print("API Error:", str(e))

        raise HTTPException(
            status_code=500,
            detail="An unexpected error occurred while processing your question."
        )

# ROOT / HEALTH CHECK

@app.get("/")
def root():
    return {
        "status": "NECA Multi-Agent Knowledge Bot API is running.",
        "agents": [
            "Membership Agent",
            "Training & ICT Academy Agent",
            "NECA Information Agent"
        ],
        "endpoint": "/support",
        "method": "POST"
    }


# API INFORMATION

@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "service": "NECA Multi-Agent Knowledge Bot"
    }