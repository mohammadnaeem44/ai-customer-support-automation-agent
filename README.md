# AI Customer Support Automation Agent

An AI-powered customer support backend built with FastAPI, Groq, retrieval-augmented generation (RAG), SQLite, and Docker.

## Features

- **Ticket management:** Create and retrieve support tickets through REST APIs.
- **AI classification:** Categorize messages by intent, sentiment, and priority.
- **Knowledge-base retrieval:** Generate support answers grounded in policy documents, with source references.
- **Order verification:** Check simulated order information against customer IDs.
- **Human-in-the-loop review:** Flag sensitive or uncertain requests for human review rather than automatically approving refunds or cancellations.
- **Persistent storage:** Store SQLite data outside the container using a Docker volume mount.
- **Automated tests:** Validate API endpoints, ticket operations, order verification, and RAG behavior.

## Technology Stack

Python · FastAPI · Groq · Sentence Transformers · scikit-learn · SQLite · pytest · Docker

## Local Setup

1. Clone the repository.
2. Create and activate a Python virtual environment.
3. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

4. Create a `.env` file containing your Groq API key:

   ```text
   GROQ_API_KEY=your_groq_api_key
   ```

5. Start the API:

   ```bash
   uvicorn main:app --reload
   ```

6. Open `http://127.0.0.1:8000/docs` to explore the API.

## Run Tests

```bash
python -m pytest tests/ -v
```

## Run with Docker

Build the image:

```bash
docker build -t customer-support-agent .
```

Run the container with environment variables and persistent SQLite storage:

```bash
docker run --name support-agent -p 8000:8000 --env-file .env -v "${PWD}/data:/app/data" customer-support-agent
```

On Windows PowerShell, run the Docker command from the project root.

## Important Limitations

- Order data is simulated for demonstration.
- Refunds and cancellations are not actually processed.
- Human review is represented by an application workflow, not a connected human support platform.
- Production use requires appropriate authentication, authorization, rate limiting, monitoring, and secure persistent storage.

## Future Improvements

- Deploy the API to a cloud platform.
- Add authentication and role-based access for reviewers.
- Integrate a real order-management system.
- Add structured evaluation of classification and retrieval quality.
