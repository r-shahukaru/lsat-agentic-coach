# 🧠 LSAT Agentic Coach

**An Agentic AI System for LSAT Logical Reasoning Practice**

---

## Overview

**LSAT Agentic Coach** is an end-to-end, production-style **agentic AI pipeline** designed to help students practice and improve LSAT Logical Reasoning.

The system ingests LSAT questions from images, parses them into structured MCQs, classifies question subtypes with guardrails, paraphrases questions safely, and provides **guided tutoring feedback** grounded in LSAT strategy using **Retrieval-Augmented Generation (RAG)**.

This project demonstrates best practices in:

* Agentic AI design
* Guardrailed LLM workflows
* Hybrid deterministic + LLM pipelines
* Educational AI systems
* Azure-based AI infrastructure

---

## Key Features

### ✅ OCR → Structured MCQ Ingestion

* Upload question screenshots
* Azure Computer Vision OCR extracts text
* Deterministic parsing converts OCR text into:

  * Question stem
  * Options (A–E)
* Stored as structured JSON in Azure Blob Storage

---

### 🧠 Subtype Classification (with Guardrails)

* Classifies LSAT Logical Reasoning question subtypes (e.g., Strengthen, Weaken, Flaw)
* Uses:

  * LLM reasoning
  * Rule-based stem analysis
  * Judge model for validation
* Prevents taxonomy errors (e.g., EXCEPT ≠ Cannot Be True)

---

### 🔁 Safe Paraphrasing Agent

* Generates **light paraphrases** to prevent memorization
* Meaning-preserving by design
* Second LLM acts as a **paraphrase judge**
* Rejects paraphrases that alter logic or difficulty

---

### 🎓 Guided Tutoring Agent

* Analyzes the student’s selected answer and reasoning
* Diagnoses logical gaps (not just correctness)
* Responds with:

  * Encouraging tone
  * Subtype-specific advice
  * Actionable reasoning guidance
* Stores each attempt for longitudinal learning analysis

---

### 📚 RAG-Powered Strategy Grounding

* LSAT strategy texts embedded into a vector index
* Used during:

  * Subtype classification
  * Tutoring feedback
* Grounds LLM reasoning in:

  * LSAT question-type strategies
  * Logical reasoning heuristics
* Prevents hallucinations and improves pedagogical accuracy

---

## High-Level Architecture

```text
Image Upload
    ↓
Azure Vision OCR
    ↓
Deterministic MCQ Parsing
    ↓
Subtype Classification
    ├─ LLM Reasoner
    ├─ Rule-Based Guardrails
    └─ Judge Model
    ↓
Safe Paraphrasing Agent
    ├─ Generator
    └─ Meaning Judge
    ↓
Guided Tutoring Agent
    ├─ Student Reasoning Analysis
    ├─ RAG Strategy Retrieval
    └─ Feedback Generation
    ↓
Azure Blob Storage (Structured JSON)
```

---

## Tech Stack

**Language**

* Python 3.12

**AI / ML**

* Azure OpenAI (chat + embeddings)
* Azure Computer Vision OCR
* Retrieval-Augmented Generation (RAG)

**Storage**

* Azure Blob Storage (MCQs, attempts, artifacts)

**Architecture Patterns**

* Agentic pipelines
* Deterministic-first, LLM-second
* Guardrails + judges
* Structured JSON outputs

---

## Repository Structure

```text
lsat-agentic-coach/
├── core/
│   ├── models.py              # Shared data models
│   └── __init__.py
│
├── services/
│   ├── ocr_azure.py           # Azure OCR wrapper
│   ├── mcq_parser.py          # Deterministic MCQ parsing
│   ├── subtype_classifier.py  # Guardrailed subtype logic
│   ├── paraphraser.py         # Safe paraphrasing agent
│   ├── tutor_agent.py         # Guided tutoring agent
│   ├── vector_search.py       # RAG abstraction layer
│   ├── mcq_repair_llm.py      # Repair agent for bad OCR
│   └── __init__.py
│
├── scripts/
│   ├── upload_one_image.py
│   ├── ocr_one_blob_bytes.py
│   ├── ingest_one_blob_to_mcq.py
│   ├── ingest_rag_corpus.py
│   ├── paraphrase_one_mcq.py
│   ├── run_pipeline_batch.py
│   ├── run_tutor_once.py
│   └── audit_subtypes_from_blobs.py
│
├── .env.example               # Environment variable template
├── .gitignore
└── README.md
```

---

## Environment Setup

Create a `.env` file (not committed):

```env
AZURE_OPENAI_ENDPOINT=...
AZURE_OPENAI_API_KEY=...
AZURE_OPENAI_CHAT_DEPLOYMENT=lsat-chat
AZURE_OPENAI_API_VERSION=2024-02-15-preview

AZURE_STORAGE_ACCOUNT=...
AZURE_STORAGE_KEY=...
```

---

## Example Pipeline Usage

### Upload + OCR + Ingest

```bash
python -m scripts.upload_one_image --file data/local_images/q1.png
python -m scripts.ocr_one_blob_bytes --blob_name user01/uploads/q1.png
python -m scripts.ingest_one_blob_to_mcq --blob_name user01/uploads/q1.png
```

### Paraphrase Safely

```bash
python -m scripts.paraphrase_one_mcq --mcq_blob user01/mcqs/<id>.json
```

### Tutor Feedback

```bash
python -m scripts.run_tutor_once
```

---

## Design Philosophy

* **Deterministic first**: Parsing, stem rules, and structure before LLM calls
* **LLMs as reasoning modules**, not magic oracles
* **Judges over blind trust**
* **Pedagogical correctness > raw accuracy**
* **Grounding via RAG**, not prompt stuffing

---

## Why This Project Matters

This system goes beyond basic “LLM apps” by demonstrating:

* Real agent coordination
* Robust failure handling
* Educational theory alignment
* Production-style AI design

It is suitable as:

* A **portfolio project**
* An **interview deep-dive**
* A foundation for a real LSAT tutoring product

---

## Future Work

* Streamlit UI for guided practice
* Full Azure AI Search RAG integration
* Student analytics dashboard
* Voice-based reasoning input
* Adaptive test generation

---

## License

MIT (or update as needed)

---