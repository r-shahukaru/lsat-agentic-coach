# LSAT Coach AI

An **Agentic AI System** for Intelligent MCQ Practice, Weakness Detection, and Adaptive Tutoring

⸻

### Overview

**LSAT Coach AI** is an end-to-end agentic AI application designed to help users practice multiple-choice questions (MCQs) more intelligently by identifying reasoning weaknesses, adapting practice material, and providing guided feedback.

The system ingests question screenshots, extracts and structures questions using OCR, categorizes them by logical subtype, and delivers personalized practice through an AI tutor. All user interactions and performance data are tracked to enable continuous improvement and targeted remediation.

The project is intentionally built using enterprise-grade Azure services and agentic AI best practices, with a strong focus on safety, observability, and scalability.

⸻

### Key Features
	•	Image-to-Question Pipeline
	•	Upload question screenshots
	•	OCR using Azure AI Vision (Read API)
	•	Structured MCQ extraction with schema validation
	•	Question Subtype Segregation
	•	Automatic classification into logical subtypes
	•	Enables weakness-based practice and analytics
	•	Stored as searchable metadata
	•	Agentic AI Architecture
	•	Modular agents for:
	•	OCR ingestion
	•	MCQ parsing
	•	Subtype classification
	•	Safe paraphrasing
	•	Tutoring & guidance
	•	Orchestrated using Azure Semantic Kernel
	•	Safe Question Paraphrasing
	•	Meaning-preserving paraphrase generation
	•	Validation layer to prevent semantic drift
	•	Fallback to original content if confidence is low
	•	Guided Practice & Tutoring
	•	Conversational AI tutor with an encouraging, corrective tone
	•	Probing questions to uncover reasoning gaps
	•	Grounded responses using stored question data
	•	Assessment & Performance Tracking
	•	Track user answers and written reasoning
	•	Identify persistent weaknesses by subtype
	•	Generate adaptive practice sets
	•	Analytics Dashboard
	•	Accuracy trends over time
	•	Performance by subtype
	•	Reasoning quality indicators

⸻

### Architecture Overview

**Frontend**
	•	Streamlit (rapid prototyping, clean UX)

**AI & Agent Layer**
	•	Azure OpenAI (chat + embeddings)
	•	Azure Semantic Kernel (agent orchestration, guardrails)

**Data & Storage**
	•	Azure Blob Storage
	•	Question images
	•	Structured MCQ metadata
	•	Azure AI Search
	•	Vector search for retrieval
	•	Metadata filtering by subtype

**Observability & Cost Awareness**
	•	Token usage tracking per agent
	•	Azure Monitor integration (configurable)
	•	Cost-aware design for agentic workflows

⸻

### Safety & Best Practices

This project explicitly follows agentic AI best practices:
	•	Input validation and schema enforcement
	•	Multi-stage output validation before user display
	•	Guardrails for hallucination reduction
	•	Clear separation between generation and evaluation
	•	Safe defaults and fail-closed behavior
	•	Enterprise-style logging and monitoring readiness

⸻

### Project Structure

```text
lsat-agentic-coach/
├── app/                     # Streamlit UI
├── core/                    # Schemas, settings, logging
├── services/                # OCR, parsing, storage, search
├── orchestration/           # Semantic Kernel pipelines & guardrails
├── scripts/                 # Indexing and ingestion utilities
├── data/                    # Local (gitignored) assets
├── README.md
├── pyproject.toml
└── .env
```

### Why This Project Matters

This project goes beyond simple LLM demos by addressing real-world challenges:
	•	Unstructured → structured data pipelines
	•	Agent orchestration instead of single prompts
	•	Evaluation, monitoring, and cost control
	•	User-centric adaptive learning systems
	•	Production-oriented Azure architecture

It is designed to reflect how modern AI systems are built and deployed in enterprise environments, especially in consulting and applied AI roles.

⸻

### Future Enhancements
	•	Speech-to-text reasoning input (voice explanations)
	•	Multi-user authentication and profiles
	•	FastAPI backend for service separation
	•	CI/CD and cloud deployment
	•	Automated evaluation metrics for reasoning quality

⸻

### Disclaimer

This project is for educational and research purposes only.
It does not provide official exam answers and is not affiliated with LSAC.
