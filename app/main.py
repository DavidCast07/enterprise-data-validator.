from fastapi import FastAPI
from app.routers import products

app = FastAPI(
    title="Enterprise Data Validator & MDG API",
    description="High-performance API for Master Data Governance, validation, and ERP migration.",
    version="1.0.0",
)

app.include_router(products.router)


@app.get("/health", tags=["System Health"])
def health_check():
    return {"status": "healthy", "service": "enterprise-data-validator-api"}

@app.get("/", tags=["Root"])
def root():
    return {
        "message": "Welcome to the Enterprise Data Validator API",
        "documentation": "http://127.0.0.1:8000/docs",
    }
