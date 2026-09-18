# Confidence-Aware RAG for Noisy OCR-Based Documents

[![Frontend (Vercel)](https://img.shields.io/badge/Frontend-Vercel%20Live-black?style=for-the-badge&logo=vercel)](https://confidence-aware-rag.vercel.app/)
[![Backend (Render)](https://img.shields.io/badge/Backend-Render%20Live-46E3B7?style=for-the-badge&logo=render&logoColor=black)](https://confidence-aware-rag-backend.onrender.com/docs)
[![Python 3.12](https://img.shields.io/badge/Python-3.12-green.svg)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688.svg)](https://fastapi.tiangolo.com)
[![MongoDB Atlas](https://img.shields.io/badge/MongoDB-Atlas%20Ready-green.svg)](https://www.mongodb.com/atlas)
[![React 19](https://img.shields.io/badge/React-19-61DAFB.svg)](https://react.dev)
[![Vite](https://img.shields.io/badge/Vite-6.0+-646CFF.svg)](https://vitejs.dev)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

> 🌐 **Live Web Application**: [https://confidence-aware-rag.vercel.app](https://confidence-aware-rag.vercel.app/)  
> ⚡ **Live Backend API & Swagger Docs**: [https://confidence-aware-rag-backend.onrender.com/docs](https://confidence-aware-rag-backend.onrender.com/docs)

An end-to-end, production-grade **Retrieval-Augmented Generation (RAG)** platform engineered for scanned legal, administrative, and technical documents (RTI replies, court orders, gazette notifications, resumes, and complex multi-page reports).

Unlike conventional RAG systems that treat extracted text as infallible ground truth, this platform extracts, preserves, and propagates **token/word-level OCR confidence** throughout every stage of the pipeline:

$$\text{PDF} \xrightarrow{} \text{OCR + Word Conf} \xrightarrow{} \text{MongoDB Persistence} \xrightarrow{} \text{Confidence Chunking} \xrightarrow{} \text{Hybrid Retrieval \& Reranking} \xrightarrow{} \text{Evidence Analysis} \xrightarrow{} \text{Interactive Workspace}$$

---

## 🌟 Key Features

### 1. 🔍 Token-Level Confidence Propagation & Reranking
- **OCR Engine Support**: Seamless auto-fallback across PyMuPDF Digital Engine, Tesseract OCR, and PaddleOCR.
- **Calibrated OCR Scoring**: Eliminates digit penalties on clean scans (`HTML5`, `Python 3.12`, `2026`) and whitelists standard typography (`•`, `–`, `“`, `”`, `₹`, `$`) for accurate **99.0% OCR Quality**.
- **Composite Reranker**: Reranks vector candidates by balancing semantic similarity and optical character reliability:
  $$\text{Final Score} = \text{Similarity} \times (w_s + w_c \times \text{Confidence})$$

### 2. 📊 Multi-Metric Score Breakdown
Every query output displays 4 separated, actionable metrics:
- **Semantic Match %**: Dense vector and lexical similarity between query and retrieved document chunks.
- **OCR Quality %**: Optical clarity score from the OCR engine across supporting evidence.
- **Overall Reliability %**: Calibrated composite reliability score.
- **Risk Level**: Dynamic classification (`LOW_RISK`, `MEDIUM_RISK`, `HIGH_RISK`) with explicit token-level degradation warnings.

### 3. 🎯 High-Precision Evidence Grounding & Highlighting
- **Targeted Evidence Selection**: Filters out filler sentences to isolate only the top 1–2 key lines directly answering the question.
- **Visual PDF Overlays**: Bounding boxes on the original scanned PDF image highlight exact supporting phrases with color-coded confidence indicators (Green $\ge 85\%$, Amber $70-85\%$, Red $< 70\%$).
- **No Highlight Flooding**: Eliminates full-page highlight clutter so users see only the exact lines of proof.

### 4. 🗂️ Flexible & Customizable Workspace Layout
- **4 View Presets**:
  - `Standard (3-Col)`: Balanced sidebar, viewer, and chat panel.
  - `PDF Focus (Wide Reader)`: Maximized PDF reading area.
  - `Chat Focus (Wide Answer)`: Maximized answer and evidence pane.
  - `Zen View (Full-Screen)`: Edge-to-edge document exploration.
- **Collapsible Sidebar Dock**: Minimizes document list to a sleek 56px dock with document badges.
- **Swap Panels**: Instant 1-click toggle between `PDF Left ↔ Answer Right`.
- **Collapsible Top Stats**: Toggle summary metric cards on and off.
- **Persistent Preferences**: Saves all layout choices in `localStorage`.

### 5. 🤖 Structured LLM Inference with Flagship Models
- **Groq Cloud Integration**: Prioritizes ultra-fast, high-reasoning models (`openai/gpt-oss-120b`, `qwen/qwen3.8-27b`, `openai/gpt-oss-20b`).
- **OpenAI Integration**: Native support for `gpt-4o-mini` and `gpt-4o`.
- **Deterministic Mock Fallback**: Built-in offline mock provider for local development without API keys.
- **Direct & Structured Answers**: Formats responses in clean Markdown (categorized bullet points, bold headers, and exact `[Page X]` provenance citations).

---

## 🎯 System Architecture

```text
React 19 Frontend Dashboard
       │ (REST API / CORS)
       ▼
FastAPI Backend
       │
       ├── MongoDB Atlas (Persistent Document & OCR Store)
       │    ├── documents    (Metadata, filename, page count, average confidence)
       │    ├── pages        (Dimensions, rendered image paths, page confidence)
       │    ├── ocr_tokens   (Word-level tokens, confidence, bounding boxes [x0, y0, x1, y1])
       │    ├── chunks       (Confidence-aware text chunks, token mappings, min confidence)
       │    ├── queries      (Query history, LLM answers, latency, risk levels)
       │    ├── evidence     (Supporting evidence sentences, token bounding boxes, risk tags)
       │    └── evaluations  (Benchmark comparison metrics, hallucination suppression rates)
       │
       └── FAISS / Vector Store (chunk_id ↔ 384-dim Dense Embeddings)
              │
              ▼
       Semantic Retrieval + Confidence Reranker
              │
              ▼
       Evidence Quality Analysis (Traceability: Chunk → OCR Tokens → Bounding Boxes)
              │
              ▼
       Confidence-Aware LLM Generation (Groq / OpenAI / Mock)
              │
              ▼
       Live Interactive Viewer (High-Res Page Scan + Precision Marker Overlays)
```

---

## 🍃 MongoDB Atlas Configuration

The application uses **MongoDB Atlas** (or local MongoDB) as its primary persistent store.

### 1. MongoDB Connection Setup
Add your connection string to `.env` in the project root:

```env
# MongoDB Atlas Database Configuration
MONGODB_URI=mongodb+srv://<username>:<password>@cluster0.xxxxx.mongodb.net/?retryWrites=true&w=majority
MONGODB_DATABASE=confidence_rag
MONGODB_MAX_POOL_SIZE=50
MONGODB_TIMEOUT_MS=5000

# Local MongoDB Alternative:
# MONGODB_URI=mongodb://localhost:27017
# MONGODB_DATABASE=confidence_rag
```

### 2. Optional: Migrate Existing Local Data
If you have previous local document cache files, import them into MongoDB Atlas:

```bash
python backend/scripts/migrate_existing_data.py
```

---

## 📊 Empirical Evaluation Benchmark

Evaluated across **32 Indian legal and administrative queries** spanning 4 optical noise degradation tiers:

| Noise Tier | Degradation Artifacts | Baseline Naive Accuracy | Proposed Accuracy | Baseline Warning Rate | Proposed Warning Rate | Unchecked Hallucination (Baseline) | Unchecked Hallucination (Ours) |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **Clean** | 0% noise | 95.8% | **95.8%** | 0.0% | **87.5%** | 0.0% | **0.0%** |
| **Low** | 10% Gaussian blur & salt noise | 84.4% | **84.4%** | 0.0% | **100.0%** | 25.0% | **0.0%** |
| **Medium** | 25% noise, contrast fade, blur | 52.1% | **52.1%** | 0.0% | **100.0%** | 50.0% | **0.0%** |
| **High** | 40% heavy compression & skew | 27.1% | **27.1%** | 0.0% | **100.0%** | **75.0%** | **0.0%** |

> **Key Finding**: While Baseline Naive RAG suffers a **75.0% silent hallucination rate** under heavy scan degradation, our Confidence-Aware RAG achieves a **100.0% warning detection rate** and **0.0% unchecked hallucination rate**, with zero penalty on clean documents.

---

## 🚀 Quickstart Guide

### Option 1: Unified Launcher (Recommended)
```bash
# 1. Install Backend Dependencies
pip install -r backend/requirements.txt

# 2. Install Frontend Dependencies
cd frontend && npm install && cd ..

# 3. Launch Backend & Frontend Concurrently
python run_system.py
```
- **React Frontend**: [http://localhost:5173](http://localhost:5173)
- **FastAPI Backend & Swagger API Docs**: [http://localhost:8000/docs](http://localhost:8000/docs)

---

### Option 2: Docker Compose
```bash
docker-compose up --build
```
- **Frontend**: [http://localhost:3000](http://localhost:3000)
- **Backend API**: [http://localhost:8000](http://localhost:8000)

---

### Option 3: Manual Launch

#### Start Backend
```bash
# Windows
set PYTHONPATH=%CD%\backend
python -m uvicorn app.main:app --app-dir backend --host 0.0.0.0 --port 8000 --reload

# Linux / macOS
export PYTHONPATH=$PWD/backend
python -m uvicorn app.main:app --app-dir backend --host 0.0.0.0 --port 8000 --reload
```

#### Start Frontend
```bash
cd frontend
npm install
npm run dev
```

---

## 🧪 Testing & Verification

```bash
# Run all 34 automated unit, repository, MongoDB, and integration tests
pytest backend/tests -v

# Run the 4-tier synthetic degradation evaluation benchmark
python evaluation/evaluate.py
```

---

## 📁 Repository Structure

```text
Confidence-Aware RAG System/
├── backend/
│   ├── app/
│   │   ├── api/v1/endpoints/  # REST endpoints (health, ingest, query, compare, documents)
│   │   ├── core/              # Config, settings, logging
│   │   ├── database/          # MongoDB Atlas manager, collections, compound indexes
│   │   ├── repositories/      # Repositories (Document, Page, OCRToken, Chunk, Query, Evidence)
│   │   ├── schemas/           # Pydantic v2 validation models
│   │   ├── services/          # OCR, chunking, embeddings, reranker, evidence, LLM
│   │   └── main.py            # FastAPI factory with lifespan connection
│   ├── scripts/
│   │   └── migrate_existing_data.py # Data migration utility
│   ├── tests/                 # 34 automated tests
│   ├── requirements.txt       # Python dependencies
│   └── Dockerfile
├── frontend/                  # React 19 + TypeScript + Vite web application
│   ├── src/
│   │   ├── components/        # DocSageDashboard, PDFPageViewer, AnswerPanel, UploadModal
│   │   ├── api.ts             # REST client
│   │   ├── types.ts           # Shared TypeScript interfaces
│   │   ├── index.css          # Design system (Dark/Light mode, Glassmorphism, Layouts)
│   │   └── App.tsx            # Main application root
│   └── Dockerfile
├── evaluation/
│   ├── degrade_document.py    # Synthetic optical noise engine
│   ├── evaluate.py            # 4-tier empirical evaluation runner
│   ├── questions.json         # Ground-truth QA dataset
│   └── results/               # Evaluation outputs & benchmark figures
├── ARCHITECTURE.md            # In-depth architectural & mathematical documentation
├── VIVA_DEFENSE_GUIDE.md      # Academic viva defense cheatsheet
├── docker-compose.yml         # Containerized production deployment
├── run_system.py              # Cross-platform runner
├── .env.example               # Environment variables template
└── README.md
```

---

## ⚖️ License
This project is licensed under the MIT License.