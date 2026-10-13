# NECA Knowledge Bot

## About My Project
This project is part of my learning journey in the NECA ICT Academy / ITF Advanced AI Automation Engineer Programme.
For this assignment, I worked on a multi-AI agent system designed to answer questions about the Nigeria Employers' Consultative Association (NECA). Instead of having one general-purpose agent handle every question, I created separate agents to handle different areas of information.
The aim is to make it easier for users to find relevant information about NECA, its membership requirements and benefits, and the training programmes offered through the NECA ICT Academy.

## What the Project Does
The system includes three specialised agents:
- Membership Agent: Answers questions about membership requirements, benefits and joining NECA.
- Training & ICT Academy Agent: Handles questions about training programmes, courses and learning opportunities.
- NECA Information Agent: Answers general questions about NECA, its functions, history and office locations.
The system uses a retrieval-augmented generation (RAG) approach to retrieve relevant information from the available NECA documents and website content before generating responses.
I also included input and output guardrails to help validate user questions and generated answer

## Technologies Used
- Python
- FastAPI
- Groq API
- Supabase with pgvector
- Pydantic
- Uvicorn
- Render (Backend Hosting)
- Bolt (Frontend Application)

## Project Structure
- `api.py` — Provides the FastAPI endpoints for the frontend.
- `MultiAgent.py` — Classifies questions and routes them to the appropriate agent.
- `agent_guard.py` — Contains the agents, guardrails and usage tracking.
- `rag.py` — Handles retrieval of relevant information from the knowledge base.
- `requirements.txt` — Lists all Python dependencies needed for the project.
- `runtime.txt` — Specifies the Python version for deployment environments like Render.
- `neca_data.txt` — Contains scraped NECA website information used by the project.

## How It Works
1. A user submits a question through the frontend.
2. The backend parses and matches queries against the Supabase knowledge base.
3. Groq generates a precise response using retrieved context, custom guardrails, and the updated system prompt.
4. The API returns the structured response back to the frontend.

## Live Application
- **Frontend App:** [NECA Knowledge Assistant on Bolt](https://neca-ai-knowledge-as-j6og.bolt.host/)

## Running the Project Locally
1. Clone this repository.
2. Create and activate a Python virtual environment.
3. Install the required packages:
python -m pip install -r requirements.txt
Add the required environment variables to a .env file.
Start the FastAPI server:
Bash
python -m uvicorn api:app --reload
The API documentation  http://127.0.0.1:8000/docs.

## Environment Variables
Configure the following variables in your local .env file:
GROQ_API_KEY
SUPABASE_URL
SUPABASE_KEY

Never commit your .env file, API keys, or database secrets to GitHub.

## Learning Outcome
This project has helped me practise building role-based AI workflows, implementing strict RAG grounding and clean system prompts, connecting a vector pipeline to a language model, and preparing an API for full deployment.

This is a learning project developed as part of my AI automation training.