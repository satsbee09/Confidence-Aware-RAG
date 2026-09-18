# Academic Viva Defense & Examination Guide: Confidence-Aware RAG

> **Project Title**: Confidence-Aware Retrieval-Augmented Generation for Noisy OCR-Based Indian Legal and Government Documents  
> **Degree**: Bachelor of Technology (B.Tech) Final Year Project  
> **Key Domains**: Natural Language Processing, Information Retrieval, Document Intelligence, Applied Machine Learning, LLM Safety

---

## 10 Master Viva Questions & Model Defense Answers

### Q1. What is the core problem and research gap your project addresses?
- **Examiner Intent**: Checking if you understand why standard RAG fails in Indian government/legal domains.
- **Model Answer**: 
  > "Standard RAG systems assume the ingested text is ground truth. In Indian legal documents (court orders, gazettes, RTI replies, land records), documents are often decades old, poorly scanned, stamped, or blurred. OCR engines introduce character-level corruptions in critical figures (penalties, limitation periods, sections).
  > Naive RAG embeds these distorted tokens, retrieves them based on semantic similarity, and feeds them to an LLM without uncertainty context. The LLM generates confident but factually wrong answers—a failure mode we term **Silent OCR Hallucination**. Our project solves this by extracting token-level OCR confidence and propagating it through chunking, reranking, evidence analysis, and generation."

---

### Q2. How do you propagate OCR confidence through chunking without losing granularity?
- **Examiner Intent**: Checking mathematical rigor and algorithmic contribution in chunk construction.
- **Model Answer**:
  > "Instead of simple word averaging which hides bad tokens behind high-confidence common words, we implement a **Weakest-Link Penalty formulation**:
  > $$\text{Conf}(C) = \max\left(0.0, \, \mu_{\text{conf}}(C) - 0.15 \times (1.0 - \min_{w \in C} c(w))\right)$$
  > If a 60-word chunk has an average confidence of 92%, but contains a critical corrupted penalty figure with only 25% confidence, the penalty subtracts $0.15 \times (1 - 0.25) = 0.1125$, reducing the chunk score to $\approx 80.7\%$ and flagging the specific corrupted word for UI token highlighting."

---

### Q3. Explain your Retrieval Reranking mathematical formula. Why not just hard-filter noisy chunks?
- **Examiner Intent**: Testing retrieval design trade-offs between filtering vs scoring.
- **Model Answer**:
  > "We use a blended scoring function:
  > $$S(q, c) = \alpha \cdot \text{Sim}_{\text{Cosine}}(q, c) + \beta \cdot \text{Conf}(c)$$
  > with $\alpha=0.50$ and $\beta=0.50$.
  > We chose blended scoring over hard threshold filtering because in legal archives, an old noisy scan might be the **only available record** answering the query. Hard-filtering would result in complete retrieval failure (false negative). Blended reranking allows the system to retrieve the evidence if necessary, but triggers our evidence risk classifier to inject legal warnings."

---

### Q4. How does your Evidence Quality Analyzer detect and flag hallucinations before LLM generation?
- **Examiner Intent**: Understanding the pre-generation safety layer.
- **Model Answer**:
  > "Before the prompt is assembled, the `EvidenceService` scans all retrieved chunks at the sentence and token level. If any chunk contains tokens with confidence $< 0.50$, or if the mean evidence confidence is $< 0.80$, the query is classified as `HIGH_RISK` or `MEDIUM_RISK`.
  > We inject a structured cautionary system directive into the LLM prompt:
  > `[CRITICAL OCR UNCERTAINTY DETECTED: The supporting document text contains degraded tokens. You MUST advise the user to inspect the physical scanned document.]`
  > This guarantees the LLM explicitly hedges the output rather than asserting a degraded number as fact."

---

### Q5. What was your methodology for synthetic document degradation and evaluation?
- **Examiner Intent**: Checking experimental validity and benchmarking protocol.
- **Model Answer**:
  > "We constructed a multi-stage synthetic degradation engine implementing 5 realistic optical artifact transforms:
  > 1. Gaussian Blur ($\sigma \in [1.0, 2.5]$)
  > 2. Salt-and-Pepper Pixel Noise ($p \in [0.01, 0.05]$)
  > 3. Contrast & Photometric Fading ($\alpha \in [0.4, 0.7]$)
  > 4. JPEG Artifact Compression ($Q \in [15, 30]$)
  > 5. Affine Skew & Optical Distortion
  > We defined 4 noise tiers: **Clean**, **Low (10%)**, **Medium (25%)**, and **High (40%)**, and evaluated 32 legal queries across factual accuracy, warning detection rate, and unchecked hallucination rate."

---

### Q6. What were the key empirical findings from your Phase 10 Benchmark?
- **Examiner Intent**: Validating real performance improvements.
- **Model Answer**:
  > "Our experimental results demonstrate three major findings:
  > 1. **High Noise Tier**: Baseline Naive RAG suffered a **75.0% unchecked hallucination rate** (giving wrong legal answers with zero warnings). Our Confidence-Aware RAG achieved a **0.0% unchecked hallucination rate** with a **100% warning detection rate**.
  > 2. **Clean Scans**: On clean scans, our proposed pipeline maintained **95.8% factual accuracy**, proving that confidence scoring introduces zero penalty on clean text.
  > 3. **Latency**: Proposed pipeline added less than 15ms overhead (mean latency 61.8ms vs baseline 64.3ms), making it fully practical for real-time production deployment."

---

### Q7. Why did you choose SentenceTransformers `all-MiniLM-L6-v2` and an in-memory/FAISS vector store?
- **Examiner Intent**: Checking system architecture and model selection justification.
- **Model Answer**:
  > "`all-MiniLM-L6-v2` produces 384-dimensional dense vectors with an optimal trade-off between semantic retrieval quality and low inference latency (<15ms per batch on CPU). For the vector store, we implemented normalized cosine similarity in a thread-safe `NumpyVectorStore` with FAISS compatibility, supporting CRUD document lifecycles, scoped document filtering, and rapid in-memory reranking."

---

### Q8. Why did you implement dual LLM providers (Groq, OpenAI, and MockLLMProvider)?
- **Examiner Intent**: Checking robustness and offline testing capabilities.
- **Model Answer**:
  > "In high-stakes legal applications and continuous testing environments, API keys may experience rate-limits or network downtime. We implemented an abstract `BaseLLMProvider` interface with:
  > 1. `GroqLLMProvider` (Llama-3-70b/8b via Groq's LPU for ultra-fast <500ms inference).
  > 2. `OpenAILLMProvider` (GPT-4o / GPT-3.5-turbo).
  > 3. `MockLLMProvider` (deterministic rule-based generator for 100% offline automated CI/CD unit testing and repeatable viva evaluation)."

---

### Q9. How is the frontend designed to serve legal professionals and judges?
- **Examiner Intent**: Evaluating user experience, transparency, and explainability.
- **Model Answer**:
  > "Legal professionals require full explainability. Our React + TypeScript frontend provides:
  > 1. **Side-by-Side Dual View**: Directly compares Baseline Naive RAG vs Confidence-Aware RAG on the same document.
  > 2. **Token-Level Visual Inspector**: Corrupted words are highlighted with red/amber badges showing exact OCR confidence (e.g. `₹25,000 (48%)`).
  > 3. **Document Repository Metrics**: Displays page count, chunk count, average confidence, and minimum token confidence before querying.
  > 4. **Live Benchmark Dashboard**: Exposes the complete 4-tier evaluation dataset and accuracy metrics for institutional auditability."

---

### Q10. What are the future research directions and enhancements?
- **Examiner Intent**: Looking for vision and understanding of project limitations.
- **Model Answer**:
  > "Future work includes:
  > 1. Fine-tuning an open-source Indian legal embedding model (e.g., fine-tuning `bge-m3` on Indian Supreme Court Judgments with token confidence loss).
  > 2. Incorporating Indic language multi-modal vision-language models (e.g. IndicOCR, Gemma 2) for direct multi-lingual Hindi/Tamil/Bengali court orders.
  > 3. Developing active learning feedback loops where human legal clerks can verify highlighted low-confidence tokens, retraining the local OCR dictionary."
