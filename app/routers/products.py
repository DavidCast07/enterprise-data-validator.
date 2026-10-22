from typing import Optional
from fastapi import APIRouter, BackgroundTasks, Depends, File, Header, HTTPException, Query, UploadFile, status
from sqlalchemy import text
from sqlalchemy.orm import Session
from app.database import get_db, settings
from app.schemas.product import (
    BulkValidationSummarySchema,
    ProductCreateSchema,
    ProductResponseSchema,
)
from app.services.csv_processor import BatchConfigParams, process_product_csv

router = APIRouter(prefix="/api/v1/products", tags=["Master Data Governance - Products"])


def verify_api_key(
    x_api_key: str = Header(default="mdg-enterprise-secret-token-2026", description="Enterprise API Token")
):
    """Día 5: Middleware de seguridad para proteger endpoints de escritura"""
    if x_api_key != settings.API_SECRET_KEY:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing X-API-Key header",
        )
    return x_api_key


@router.post(
    "/validate",
    response_model=ProductResponseSchema,
    status_code=status.HTTP_200_OK,
    summary="Validate and normalize a single product record against MDG rules",
)
def validate_product_payload(product: ProductCreateSchema):
    return ProductResponseSchema(**product.model_dump())


@router.post(
    "/upload-csv",
    response_model=BulkValidationSummarySchema,
    status_code=status.HTTP_200_OK,
    summary="Validate CSV, persist clean records to PostgreSQL, and quarantine errors in background",
)
async def upload_and_validate_csv(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(..., description="CSV file containing raw product master data"),
    config: BatchConfigParams = Depends(),
    db: Session = Depends(get_db),
    _api_key: str = Depends(verify_api_key),
):
    return await process_product_csv(
        file=file, config=config, db=db, background_tasks=background_tasks
    )


@router.get(
    "/master",
    summary="Query clean Master Products directly from PostgreSQL 16",
)
def get_master_products(
    category: Optional[str] = Query(None, description="Filter by category (e.g., Chemicals, Tools)"),
    limit: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db),
):
    if category:
        stmt = text("""
            SELECT product_id, sku, product_name, category, unit_price, currency, uom, supplier_email, updated_at
            FROM master_products
            WHERE category = :category
            ORDER BY updated_at DESC
            LIMIT :limit
        """)
        rows = db.execute(stmt, {"category": category, "limit": limit}).mappings().all()
    else:
        stmt = text("""
            SELECT product_id, sku, product_name, category, unit_price, currency, uom, supplier_email, updated_at
            FROM master_products
            ORDER BY updated_at DESC
            LIMIT :limit
        """)
        rows = db.execute(stmt, {"limit": limit}).mappings().all()

    return {"count": len(rows), "items": rows}


@router.get(
    "/data-quality",
    summary="Fetch real-time Data Quality KPIs from PostgreSQL View",
)
def get_data_quality_kpis(db: Session = Depends(get_db)):
    summary = db.execute(text("SELECT * FROM vw_data_quality_summary;")).mappings().first()
    breakdown = db.execute(text("""
        SELECT rejection_reason, COUNT(*) AS total
        FROM rejected_products_log
        GROUP BY rejection_reason
        ORDER BY total DESC;
    """)).mappings().all()
    return {
        "kpis": summary,
        "rejection_breakdown": breakdown,
    }
