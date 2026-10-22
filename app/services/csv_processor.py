import csv
import io
import json
from typing import Dict, Any, List, Set
from fastapi import BackgroundTasks, HTTPException, Query, UploadFile, status
from pydantic import ValidationError
from sqlalchemy import text
from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.schemas.product import (
    BulkValidationSummarySchema,
    ProductCreateSchema,
    ProductResponseSchema,
    RowRejectionDetail,
)


class BatchConfigParams:
    def __init__(
        self,
        max_rows: int = Query(1000, ge=1, le=50000, description="Maximum rows allowed per file upload"),
        deduplicate_in_batch: bool = Query(True, description="Reject duplicate SKUs within the same CSV file"),
        persist_to_db: bool = Query(True, description="Save clean rows to master_products and errors to quarantine"),
    ):
        self.max_rows = max_rows
        self.deduplicate_in_batch = deduplicate_in_batch
        self.persist_to_db = persist_to_db


def log_rejections_in_background(rejected_rows: List[RowRejectionDetail]):
    """Tarea asíncrona en segundo plano (Día 5: BackgroundTasks) para guardar auditoría sin frenar al usuario"""
    if not rejected_rows:
        return
    db = SessionLocal()
    try:
        insert_reject_sql = text("""
            INSERT INTO rejected_products_log (raw_id, sku, product_name, rejection_reason, raw_payload)
            VALUES (:raw_id, :sku, :product_name, :rejection_reason, CAST(:raw_payload AS JSONB))
        """)
        payloads = [
            {
                "raw_id": r.row_number,
                "sku": r.raw_sku,
                "product_name": r.raw_data.get("product_name", "UNKNOWN"),
                "rejection_reason": " | ".join(r.errors),
                "raw_payload": json.dumps(r.raw_data),
            }
            for r in rejected_rows
        ]
        db.execute(insert_reject_sql, payloads)
        db.commit()
    finally:
        db.close()


async def process_product_csv(
    file: UploadFile,
    config: BatchConfigParams,
    db: Session,
    background_tasks: BackgroundTasks,
) -> BulkValidationSummarySchema:
    if not file.filename or not file.filename.lower().endswith(".csv"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid file format. Only .csv files are accepted.",
        )

    content = await file.read()
    decoded_text = content.decode("utf-8-sig")
    csv_reader = csv.DictReader(io.StringIO(decoded_text))

    valid_records: List[ProductResponseSchema] = []
    rejected_records: List[RowRejectionDetail] = []
    seen_skus: Set[str] = set()
    total_rows = 0

    for idx, row in enumerate(csv_reader, start=2):
        total_rows += 1
        if total_rows > config.max_rows:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"File exceeds the maximum limit of {config.max_rows} rows.",
            )

        raw_sku = (row.get("sku") or "").strip().upper()

        if config.deduplicate_in_batch and raw_sku and raw_sku in seen_skus:
            rejected_records.append(
                RowRejectionDetail(
                    row_number=idx,
                    raw_sku=raw_sku,
                    errors=["Duplicate SKU detected within the same upload batch"],
                    raw_data=row,
                )
            )
            continue

        try:
            validated_prod = ProductCreateSchema(**row)
            seen_skus.add(validated_prod.sku)
            valid_records.append(ProductResponseSchema(**validated_prod.model_dump()))
        except ValidationError as exc:
            error_messages = [
                f"{'.'.join(str(loc) for loc in err['loc'])}: {err['msg']}"
                for err in exc.errors()
            ]
            rejected_records.append(
                RowRejectionDetail(
                    row_number=idx,
                    raw_sku=raw_sku or "MISSING_SKU",
                    errors=error_messages,
                    raw_data=row,
                )
            )

    # Día 4: Inserción Masiva Atómica (Bulk UPSERT) en PostgreSQL
    if config.persist_to_db and valid_records:
        upsert_sql = text("""
            INSERT INTO master_products (sku, product_name, category, unit_price, currency, uom, supplier_email, attributes)
            VALUES (:sku, :product_name, :category, :unit_price, :currency, :uom, :supplier_email, CAST(:attributes AS JSONB))
            ON CONFLICT (sku) DO UPDATE SET
                product_name = EXCLUDED.product_name,
                category = EXCLUDED.category,
                unit_price = EXCLUDED.unit_price,
                currency = EXCLUDED.currency,
                uom = EXCLUDED.uom,
                supplier_email = EXCLUDED.supplier_email,
                updated_at = CURRENT_TIMESTAMP
        """)
        db_params = [
            {
                "sku": rec.sku,
                "product_name": rec.product_name,
                "category": rec.category,
                "unit_price": rec.unit_price,
                "currency": rec.currency,
                "uom": rec.uom,
                "supplier_email": rec.supplier_email,
                "attributes": json.dumps(rec.attributes),
            }
            for rec in valid_records
        ]
        db.execute(upsert_sql, db_params)
        db.commit()

    # Día 5: Enviar los rechazados a PostgreSQL en segundo plano
    if config.persist_to_db and rejected_records:
        background_tasks.add_task(log_rejections_in_background, rejected_records)

    quality_score = round((len(valid_records) / total_rows * 100), 2) if total_rows > 0 else 0.0

    return BulkValidationSummarySchema(
        filename=file.filename,
        total_rows_processed=total_rows,
        valid_count=len(valid_records),
        rejected_count=len(rejected_records),
        data_quality_score_pct=quality_score,
        valid_records=valid_records,
        rejected_records=rejected_records,
    )
