# Enterprise Data Validator & ERP Migration Engine

![Python](https://img.shields.io/badge/Python-3.12-blue?logo=python)
![FastAPI](https://img.shields.io/badge/FastAPI-Pydantic_V2-009688?logo=fastapi)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-336791?logo=postgresql)
![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?logo=docker)

An enterprise-grade **Master Data Governance (MDG) & Automated Data Quarantine Pipeline** built with **FastAPI, Pydantic V2, SQLAlchemy 2.0, and PostgreSQL 16**. 

Designed to solve real-world ERP data migration bottlenecks (such as **SAP S/4HANA** templates) by intercepting dirty CSV/JSON payloads, enforcing strict business validation rules, deduplicating records via SQL Window Functions, and routing rejected rows into an asynchronous audit quarantine log.

---

## Key Engineering Highlights

* **High-Speed In-Memory Validation (Pydantic V2):** Normalizes strings, enforces SKU naming conventions (`MAT-` / `SKU-`), validates positive pricing, ISO currencies (`USD`, `EUR`), Units of Measure (`EA`, `KG`, `BOX`, `L`), and supplier email formats prior to database ingestion.
* **Idempotent Bulk Upserts (`ON CONFLICT DO UPDATE`):** Migrates clean records atomically into `master_products` without throwing duplicate key crashes on re-runs.
* **Asynchronous Quarantine Logging (`BackgroundTasks`):** Offloads rejected rows and detailed error traces (`JSONB`) to `rejected_products_log` in the background to keep API response times low.
* **Analytical SQL Pipeline & Stress Tested (100,000+ Rows):** Includes advanced SQL scripts utilizing CTEs (`WITH`), Window Functions (`ROW_NUMBER`, `DENSE_RANK`, `LAG`, `LEAD`), `generate_series` stress testing (100k rows processed in `<300ms`), and composite B-Tree indexing verified with `EXPLAIN ANALYZE`.
* **Production Ready:** Fully containerized with Docker Compose (`postgres:16-alpine` + `FastAPI`), secured via `X-API-Key` header authentication, and tested automatically with `pytest` & **GitHub Actions CI**.

---

## Architecture Overview

```text
[Raw CSV / ERP Template] 
       │
       ▼
[FastAPI + Pydantic V2 Validation Engine] ──(Invalid Rows)──► [BackgroundTasks] ──► [PostgreSQL: rejected_products_log (JSONB)]
       │
  (Valid Rows)
       │
       ▼
[SQLAlchemy 2.0 Atomic Bulk UPSERT] ────────────────────────► [PostgreSQL: master_products + vw_data_quality_summary]
