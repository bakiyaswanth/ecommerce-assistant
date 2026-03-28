# 🛒 AI E-commerce Product Scout

An AI-powered shopping assistant that uses **Google ADK (Agent Development Kit)** with **Gemini 1.5 Flash** to help users search, compare, and get recommendations from a product catalog stored in **AlloyDB for PostgreSQL**.

## ✨ Features

- **Natural Language Search** — Ask questions like "Show me headphones under $100" and get relevant results
- **AI-Powered Recommendations** — The agent understands context and can suggest products
- **Product Comparisons** — Compare products side-by-side
- **Conversational Interface** — Maintains chat history within a session

## 🏗️ Architecture

```
Browser → Streamlit (8080) → FastAPI (8000) → ADK Agent → AlloyDB
                                                  ↓
                                          Gemini 1.5 Flash
```

| Component      | Technology                      | Port |
|----------------|----------------------------------|------|
| Frontend       | Streamlit                        | 8080 |
| Backend API    | FastAPI + Uvicorn               | 8000 |
| Agent          | Google ADK + Gemini 1.5 Flash   | —    |
| Database       | AlloyDB (PostgreSQL + AI NL)    | 5432 |

## 📁 Project Structure

```
├── main.py            # FastAPI backend with /chat endpoint
├── app.py             # Streamlit chat interface
├── agent_config.py    # ADK Agent setup (tools, model, instructions)
├── db.py              # Database connection pool & query helpers
├── schema.sql         # Database schema & sample data
├── requirements.txt   # Python dependencies
├── Dockerfile         # Container build
├── run.sh             # Process launcher
└── .env.example       # Environment variable template
```

## 🚀 Quick Start

### Prerequisites

- Python 3.11+
- Access to an AlloyDB instance with `alloydb_ai_nl` extension
- Google Cloud project with Vertex AI enabled
- `gcloud` CLI authenticated

### 1. Clone & Install

```bash
git clone <repository-url>
cd ecommerce-assistant

python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

pip install -r requirements.txt
```

### 2. Configure Environment

```bash
cp .env.example .env
# Edit .env with your actual values
```

| Variable               | Required | Description                     |
|------------------------|----------|---------------------------------|
| `DB_HOST`              | ✅        | AlloyDB private IP              |
| `DB_USER`              | ✅        | Database username               |
| `DB_PASS`              | ✅        | Database password               |
| `DB_NAME`              | —        | Database name (default: `postgres`) |
| `GOOGLE_CLOUD_PROJECT` | ✅        | GCP project ID                  |

### 3. Set Up Database

Run the schema against your AlloyDB instance:

```bash
psql -h $DB_HOST -U $DB_USER -d $DB_NAME -f schema.sql
```

### 4. Run Locally

**Option A — Using the launcher script:**
```bash
bash run.sh
```

**Option B — Separate terminals:**
```bash
# Terminal 1 - Backend
uvicorn main:app --host 0.0.0.0 --port 8000 --reload

# Terminal 2 - Frontend
streamlit run app.py --server.port 8080
```

Open http://localhost:8080 in your browser.

## 🐳 Docker

### Build

```bash
docker build -t ecommerce-scout .
```

### Run

```bash
docker run -p 8080:8080 -p 8000:8000 \
  -e DB_HOST=<your-alloydb-ip> \
  -e DB_USER=<your-db-user> \
  -e DB_PASS=<your-db-password> \
  -e GOOGLE_CLOUD_PROJECT=<your-project-id> \
  ecommerce-scout
```

## ☁️ Deploy to Cloud Run

### 1. Build & Push

```bash
export PROJECT_ID=$(gcloud config get-value project)
export REGION=us-central1

gcloud builds submit --tag gcr.io/$PROJECT_ID/ecommerce-scout
```

### 2. Deploy

```bash
gcloud run deploy ecommerce-scout \
  --image gcr.io/$PROJECT_ID/ecommerce-scout \
  --platform managed \
  --region $REGION \
  --port 8080 \
  --memory 1Gi \
  --cpu 1 \
  --min-instances 0 \
  --max-instances 3 \
  --vpc-connector <your-vpc-connector> \
  --set-env-vars "DB_HOST=<alloydb-ip>,DB_USER=<user>,DB_PASS=<pass>,GOOGLE_CLOUD_PROJECT=$PROJECT_ID" \
  --allow-unauthenticated
```

> **Note:** The `--vpc-connector` flag is required for AlloyDB connectivity since AlloyDB only exposes private IPs.

## 🧪 API Reference

### `POST /chat`

```json
// Request
{
  "message": "Show me wireless headphones under $100",
  "session_id": "optional-uuid"
}

// Response
{
  "response": "Here are some wireless headphones under $100:\n\n1. **SoundMax Pro** — $79.99\n   ...",
  "session_id": "the-session-uuid"
}
```

### `GET /health`

```json
{
  "status": "healthy",
  "database": "connected"
}
```

## 📄 License

MIT