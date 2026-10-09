# NECA Knowledge Bot

## About My Project

This project is part of my learning journey in the NECA ICT Academy / ITF Advanced AI Automation Engineer Programme.

For this assignment, I worked on a multi-AI agent system designed to answer questions about the Nigeria Employers' Consultative Association (NECA). Instead of having one general-purpose agent handle every question, I created separate agents to handle different areas of information.

The aim is to make it easier for users to find relevant information about NECA, its membership requirements and benefits, and the training programmes offered through the NECA ICT Academy.

## What the Project Does

The system includes three specialised agents:

* **Membership Agent:** Answers questions about membership requirements, benefits and joining NECA.
* **Training & ICT Academy Agent:** Handles questions about training programmes, courses and learning opportunities.
* **NECA Information Agent:** Answers general questions about NECA, its functions, history and office locations.

The system uses a retrieval-augmented generation (RAG) approach to retrieve relevant information from the available NECA documents and website content before generating responses.

I also included input and output guardrails to help validate user questions and generated answers.

## Technologies Used

* Python
* FastAPI
* Groq API
* Supabase with pgvector
* Sentence Transformers (`all-MiniLM-L6-v2`)
* Pydantic
* Uvicorn
* Render for backend hosting
* Lovable for the frontend

## Project Structure

* `api.py` — Provides the FastAPI endpoints for the frontend.
* `MultiAgent.py` — Classifies questions and routes them to the appropriate agent.
* `agent_guard.py` — Contains the agents, guardrails and usage tracking.
* `rag.py` — Handles retrieval of relevant information from the knowledge base.
* `neca_data.txt` — Contains scraped NECA website information used by the project.

## How It Works

1. A user submits a question through the frontend.
2. The backend validates the question and identifies the appropriate agent.
3. The selected agent retrieves relevant information from the knowledge base.
4. Groq generates a response using the retrieved context and the agent's instructions.
5. The API returns the response to the frontend.

## Running the Project Locally

1. Clone this repository.
2. Create and activate a Python virtual environment.
3. Install the required packages.
4. Add the required environment variables to a `.env` file.
5. Start the FastAPI server.

Example:

```bash
python -m pip install fastapi "uvicorn[standard]" groq python-dotenv httpx pydantic supabase sentence-transformers
python -m uvicorn api:app --reload
```

The API documentation will be available at `http://127.0.0.1:8000/docs`.

## Environment Variables

Configure the following variables in your local `.env` file:

* `GROQ_API_KEY`
* `SUPABASE_URL`
* `SUPABASE_KEY`

Use the exact Supabase variable names expected by your `rag.py` configuration. Never commit your `.env` file, API keys or database secrets to GitHub.

## Deployment

The backend is intended to be deployed on Render, with the frontend built in Lovable. Once deployment is complete, the public API URL will be connected to the Lovable frontend so users can interact with the knowledge bot.

## Learning Outcome

This project has helped me practise building role-based AI agents, implementing guardrails, connecting a RAG pipeline to a language model, and preparing an API for deployment.

This is a learning project developed as part of my AI automation training.
