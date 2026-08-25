# AYUSH EMR Terminology Microservice

A standardized clinical terminology microservice for AYUSH systems of medicine (Ayurveda, Siddha, Unani, Homeopathy, Yoga & Naturopathy) integrating with ICD-11-TM2, SNOMED-CT, and National Health Claims Exchange (NHCX) standards.

## Project Structure

```
ayush-emr-terminology/
├── README.md               # Documentation
├── .env.example            # Environment configuration template
├── .gitignore              # Git ignore configuration
├── docker-compose.yml      # Multi-container service definition
├── Dockerfile              # Backend container definition
├── requirements.txt        # Python backend dependencies
├── docs/                   # System architecture and design specifications
├── etl/                    # Terminology extraction, transformation, loading pipelines
├── indexing/               # Vector embeddings and indexing utilities
├── security/               # Security, authentication, and data privacy policies
├── db/                     # Database models, session management, and migrations
├── api/                    # FastAPI application, routing, and configuration
├── frontend/               # React (Vite) administration & terminology UI
└── tests/                  # Pytest test suite
```

## Quick Start

### Prerequisites
- Python 3.11+
- Node.js 18+ and npm
- Docker & Docker Compose

### Local Development Setup

1. **Environment Variables**:
   ```bash
   cp .env.example .env
   ```

2. **Backend Setup**:
   ```bash
   python -m venv .venv
   # Windows
   .venv\Scripts\activate
   # Linux/macOS
   source .venv/bin/activate

   pip install -r requirements.txt
   ```

3. **Running Backend Tests**:
   ```bash
   pytest
   ```

4. **Running Backend Server**:
   ```bash
   uvicorn api.main:app --reload --port 8000
   ```

5. **Frontend Setup**:
   ```bash
   cd frontend
   npm install
   npm run dev
   ```

6. **Docker Compose Setup**:
   ```bash
   docker-compose up --build
   ```

## API Endpoints (Foundation)
- `GET /health` - Microservice and Database connectivity health status
- `GET /` - Root welcoming message with service metadata

## Architecture Document
For full schema, concept mapping design, and vector embedding strategy, see [docs/architecture.md](docs/architecture.md).
