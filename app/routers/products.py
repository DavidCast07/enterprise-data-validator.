from fastapi import APIRouter, Depends, File, UploadFile, status
from app.schemas.product import (
    BulkValidationSummarySchema,
    ProductCreateSchema,
    ProductResponseSchema,
)
from app.services.csv_processor import BatchConfigParams, process_product_csv

router = APIRouter(prefix="/api/v1/products", tags=["Master Data Governance - Products"])


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
    summary="Bulk validate a CSV template and separate clean records from quarantined rows",
)
async def upload_and_validate_csv(
    file: UploadFile = File(..., description="CSV file containing raw product master data"),
    config: BatchConfigParams = Depends(),
):
    """
    Recibe una plantilla CSV de migración, evalúa fila por fila usando Pydantic V2,
    detecta SKUs duplicados en el lote y devuelve el score de calidad de datos.
    """
    return await process_product_csv(file=file, config=config)
