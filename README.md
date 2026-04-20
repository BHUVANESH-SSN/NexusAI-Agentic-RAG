# NexusAI-Agentic-RAG

NexusAI-Agentic-RAG is an enterprise-grade multi-agent Retrieval-Augmented Generation (RAG) system. It features a custom LangChain-based Supervisor that intelligentally routes user queries to specialized agents, enabling complex capabilities like unstructured document retrieval, structured SQL database queries, and executing external tool requests (e.g. sending emails).

## Features

- **Multi-Agent Architecture**: Uses a custom Python-based supervisor router for dispatching queries.
- **RAG for Unstructured Data**: Retrieve insights from company documents, policies, and PDFs.
- **SQL Database Agent**: Fetch and analyze structured data (e.g., employee directories or sales records).
- **Tool Agents**: Extend capabilities with external actions such as sending emails.
- **Validation Agent**: Enforces grounding to prevent LLM hallucinations.
- **Redis Session Memory**: Remembers conversational context across multiple turns.
- **Next.js Knowledge Base Frontend**: A dynamic, professional frontend UI for interacting with the chatbot, managing settings, and uploading documents.

## Tech Stack

- **Backend**: FastAPI
- **AI Framework**: LangChain, OpenAI
- **Frontend**: Next.js, TypeScript, Tailwind CSS
- **Databases**: SQLite (for app data/settings), Vector Store (FAISS/ChromaDB for document embeddings)
- **Caching & Memory**: Redis

## Setup & Installation

### 1. Prerequisites

- Python 3.10+
- Node.js 18+
- Redis (Running locally or via cloud)

### 2. Backend Setup

1. Clone the repository and navigate to the root directory.
2. Create and activate a virtual environment:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Copy the environment variables template and configure it:
   ```bash
   cp .env.example .env
   ```
   *(Ensure you fill out `OPENAI_API_KEY` and the `REDIS_URL` in the `.env` file.)*
5. Start the FastAPI server:
   ```bash
   fastapi dev app.py
   ```
   *(Or use `uvicorn app:app --reload`)*

### 3. Frontend Setup

1. Navigate to the frontend directory:
   ```bash
   cd frontend
   ```
2. Install dependencies:
   ```bash
   npm install
   ```
3. Start the Next.js development server:
   ```bash
   npm run dev
   ```

## Architecture Diagram Overview

1. User sends message -> FastAPI `/chat` endpoint.
2. Memory looks up the User/Session context from Redis.
3. Supervisor Agent analyzes input intent (Retriever, DB, Tool, or Chat).
4. Specifically routed agent executes task.
5. Validation Agent checks the response against context/grounding.
6. Response is streamed/returned back to the Next.js UI.
