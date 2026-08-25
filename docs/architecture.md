# AYUSH EMR Terminology Microservice Architecture

## Overview
The AYUSH EMR Terminology Microservice provides standard-compliant clinical terminology mapping, validation, semantic search, and FHIR bundle integration for traditional Indian systems of medicine (Ayurveda, Yoga & Naturopathy, Unani, Siddha, and Homoeopathy).

It connects traditional AYUSH concepts (NAMASTE portal concepts, National Health Portal codes) with international standards like ICD-11 (specifically ICD-11 TM2 chapter for Traditional Medicine) and SNOMED-CT.

## Core System Architecture

```
                                 +-------------------------+
                                 |   EHR / EMR Clients     |
                                 +------------+------------+
                                              |
                                              v
                                 +-------------------------+
                                 |  FastAPI Microservice   |
                                 |     (REST / FHIR)       |
                                 +------------+------------+
                                              |
                     +------------------------+------------------------+
                     |                        |                        |
                     v                        v                        v
            +----------------+       +----------------+       +----------------+
            | Concept Search |       | FHIR Mapper    |       | Audit/Security |
            | & Embeddings   |       | & Validation   |       | & NHCX Rules   |
            +-------+--------+       +-------+--------+       +-------+--------+
                    |                        |                        |
                    +------------------------+------------------------+
                                              |
                                              v
                                 +-------------------------+
                                 |   PostgreSQL + pgvector |
                                 +-------------------------+
```

## Data Schema & Entities

1. **Terminology Concepts (`concepts`)**:
   - `id` (UUID, Primary Key)
   - `code` (String, Indexed) - Unique code within the code system
   - `system` (String, Indexed) - URI/Identifier of the CodeSystem (e.g., `http://namaste.ayush.gov.in`, `http://id.who.int/icd/release/11/mms`)
   - `display` (String) - Standard preferred term name
   - `system_category` (Enum/String) - Ayurveda, Siddha, Unani, Homeopathy, Yoga, ICD-11-TM2, SNOMED-CT
   - `definition` (Text) - Clinical description
   - `status` (String) - active / retired
   - `version` (String) - Code system version
   - Timestamps (`created_at`, `updated_at`)

2. **Terminology Mappings (`terminology_mappings`)**:
   - `id` (UUID, Primary Key)
   - `source_concept_id` (FK -> `concepts.id`)
   - `target_concept_id` (FK -> `concepts.id`)
   - `relationship_type` (String) - equivalent, broader, narrower, related-to
   - `confidence_score` (Float) - 0.0 to 1.0 confidence rating
   - `mapping_status` (String) - verified, candidate, rejected
   - `created_by` (String) - System / User ID
   - Timestamps

3. **Concept Embeddings (`concept_embeddings`)**:
   - `id` (UUID, Primary Key)
   - `concept_id` (FK -> `concepts.id`, Unique)
   - `embedding` (Vector(384)) - Dense vector embedding for semantic search
   - `model_name` (String) - Embedding model identifier (e.g. `all-MiniLM-L6-v2`)
   - `updated_at`

4. **FHIR Bundles / Encounters (`fhir_bundles`)**:
   - `id` (UUID, Primary Key)
   - `bundle_id` (String, Indexed) - External FHIR Bundle ID
   - `patient_id` (String) - De-identified patient ID
   - `encounter_id` (String)
   - `raw_payload` (JSONB) - Original input FHIR JSON
   - `transformed_payload` (JSONB) - Processed FHIR JSON with standardized AYUSH coding
   - `status` (String) - processed, pending, failed
   - Timestamps

5. **Audit Logs (`audit_logs`)**:
   - `id` (UUID, Primary Key)
   - `event_type` (String) - MAPPING_LOOKUP, CONCEPT_SEARCH, CORRECTION_SUBMITTED, FHIR_TRANSFORM
   - `actor_id` (String)
   - `details` (JSONB)
   - `ip_address` (String)
   - `created_at`

6. **Correction Logs (`correction_logs`)**:
   - `id` (UUID, Primary Key)
   - `mapping_id` (FK -> `terminology_mappings.id`)
   - `suggested_target_id` (FK -> `concepts.id`)
   - `reason` (Text)
   - `status` (String) - pending, approved, rejected
   - `submitted_by` (String)
   - Timestamps

7. **NHCX Rules (`nhcx_rules`)**:
   - `id` (UUID, Primary Key)
   - `rule_code` (String, Unique) - Rule identifier (e.g. `NHCX-AYUSH-VAL-001`)
   - `description` (Text)
   - `validation_expression` (Text) - JSONLogic or CEL validation rules for NHCX compliance
   - `is_active` (Boolean)
   - Timestamps

8. **Code System Versions (`code_system_versions`)**:
   - `id` (UUID, Primary Key)
   - `system_uri` (String) - Code system identifier URI
   - `name` (String) - Standard display name (e.g. NAMASTE Ayurveda v2.1)
   - `version` (String)
   - `release_date` (Date)
   - `concept_count` (Integer)
   - `is_active` (Boolean)
   - Timestamps

## Tech Stack
- **Language**: Python 3.11+
- **Backend Framework**: FastAPI + Uvicorn
- **Database**: PostgreSQL 16 + pgvector extension
- **ORM & DB Access**: SQLAlchemy 2.0 + Psycopg3 / Psycopg2
- **Data Validation**: Pydantic v2
- **Testing**: pytest + httpx
- **Frontend**: React (Vite, Vanilla CSS, Responsive Dashboard UI)
- **Containerization**: Docker & Docker Compose
