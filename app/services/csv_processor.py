import csv
import io
from typing import Set
from fastapi import HTTPException, Query, UploadFile, status
from pydantic import ValidationError
from app.schemas.product import (
    BulkValidationSummarySchema,
    ProductCreateSchema,
    ProductResponseSchema,
    RowRejectionDetail,
)


class BatchConfigParams:
    """Dependencia reutilizable para configurar reglas de carga masiva (Día 4: Depends)"""
    def __init__(
        self,
        max_rows: int = Query(1000, ge=1, le=50000, description="Maximum rows allowed per file upload"),
        deduplicate_in_batch: bool = Query(True, description="Reject duplicate SKUs within the same CSV file"),
    ):
        self.max_rows = max_rows
        self.deduplicate_in_batch = deduplicate_in_batch


async def process_product_csv(
    file: UploadFile, 
    config: BatchConfigParams
) -> BulkValidationSummarySchema:
    if not file.filename or not file.filename.lower().endswith(".csv"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid file format. Only .csv files are accepted.",
        )

    content = await file.read()
    try:
        decoded_text = content.decode("utf-8-sig")
    except UnicodeDecodeError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File encoding must be UTF-8.",
        )

    csv_reader = csv.DictReader(io.StringIO(decoded_text))
    
    valid_records = []
    rejected_records = []
    seen_skus: Set[str] = set()
    total_rows = 0

    for idx, row in enumerate(csv_reader, start=2):  # Fila 1 es la cabecera del CSV
        total_rows += 1
        if total_rows > config.max_rows:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"File exceeds the maximum limit of {config.max_rows} rows.",
            )

        raw_sku = (row.get("sku") or "").strip().upper()

        # Regla 1: Detectar duplicados dentro del mismo archivo CSV
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

        # Regla 2: Validar contra Pydantic V2 (ProductCreateSchema)
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
