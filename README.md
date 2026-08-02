# CixioHub AI Microservice (`hub_ai`)

This is the standalone FastAPI microservice for CixioHub that handles AI/ML tasks including LLM chat streaming, document processing, vision RAG, vector embedding generation, and web search integrations.

---

## 🚀 Choose Your Setup Method

You can run `hub_ai` in **two ways**:
- **[Option 1: Docker Compose Setup](#option-1-docker-compose-setup)** (Runs `hub_ai` inside Docker container on port `8003`)
- **[Option 2: Native Localhost Setup](#option-2-native-localhost-setup-without-docker)** (Runs `hub_ai` natively via Python `uvicorn` on port `8003`)

---

## Prerequisites (Both Options)

1. **Ollama** running on your device ([ollama.com](https://ollama.com)):
   ```bash
   ollama serve
   ```
2. **Pull Required Models:**
   ```bash
   ollama pull nomic-embed-text
   ollama pull qwen3.5:4b
   ollama pull qwen3-vl:2b
   ```
3. **CixioHub Backend (`hub_backend`)** running on port `8000`.

---

## Option 1: Docker Compose Setup

Runs `hub_ai` inside a container using host networking mode on Linux.

### 1. Configure `.env`
```bash
cd hub_ai
cp .env.example .env
```
Ensure your `.env` contains:
```env
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=qwen3.5:4b
OLLAMA_EMBED_MODEL=nomic-embed-text
OLLAMA_VISION_MODEL=qwen3-vl:2b
QDRANT_URL=http://localhost:6333
QDRANT_COLLECTION=user_documents
ENABLE_VISION_RAG=True
AI_API_KEY=1234
```

### 2. Start Service via Docker Compose
```bash
docker compose up -d --build
```

### 3. View Logs
```bash
docker compose logs -f ai-service
```

---

## Option 2: Native Localhost Setup (Without Docker)

Run `hub_ai` natively using Python and `uvicorn` on your host machine.

### 1. Create Virtual Environment & Install Dependencies
```bash
cd hub_ai
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Configure `.env` for Localhost
```bash
cp .env.example .env
```
Ensure your `.env` contains:
```env
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=qwen3.5:4b
OLLAMA_EMBED_MODEL=nomic-embed-text
OLLAMA_VISION_MODEL=qwen3-vl:2b
QDRANT_URL=http://localhost:6333
QDRANT_COLLECTION=user_documents
ENABLE_VISION_RAG=True
AI_API_KEY=1234

# Reranker Configuration
ENABLE_RERANKER=True
RERANKER_MODEL=mixedbread-ai/mxbai-rerank-base-v1
RERANKER_DEVICE=cpu   # Set to 'cuda' if NVIDIA GPU with PyTorch CUDA is installed
```

### 3. Setup & Download Reranker Model (Non-Docker)
When running natively without Docker, `sentence_transformers` accesses your host internet and caches models directly in `~/.cache/huggingface/`.

- **Automatic Download:** On the first search request requiring reranking, `mixedbread-ai/mxbai-rerank-base-v1` will automatically download from Hugging Face to `~/.cache/huggingface/`.
- **Optional Pre-download Step:** To avoid first-query latency, pre-download the model ahead of time:
  ```bash
  python3 -c "from sentence_transformers import CrossEncoder; CrossEncoder('mixedbread-ai/mxbai-rerank-base-v1')"
  ```

### 4. Start AI Server
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8003 --reload
```

---

## 🔗 API Documentation & Verification

Once running (Docker or Localhost):
- **Interactive Swagger Docs:** [http://localhost:8003/docs](http://localhost:8003/docs)
- **Health Check:** [http://localhost:8003/health](http://localhost:8003/health)

### Authentication Header
Requests sent from `hub_backend` include the authentication header:
```http
X-AI-API-Key: 1234
```
