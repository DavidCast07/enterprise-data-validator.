from datetime import datetime
from typing import Any, Dict, Literal, Optional
from pydantic import BaseModel, EmailStr, Field, field_validator


class ProductCreateSchema(BaseModel):
    sku: str = Field(..., min_length=3, max_length=50, description="Unique Material SKU")
    product_name: str = Field(..., min_length=2, max_length=255)
    category: str = Field(..., min_length=2, max_length=100)
    unit_price: float = Field(..., gt=0, description="Price must be strictly greater than 0")
    currency: Literal["USD", "EUR"] = Field(default="USD")
    uom: Literal["EA", "KG", "BOX", "L"] = Field(..., description="Allowed Units of Measure")
    supplier_email: EmailStr
    attributes: Optional[Dict[str, Any]] = Field(default_factory=dict)

    # Normalización automática antes de validar (equivalente a TRIM y UPPER en SQL)
    @field_validator("sku", "currency", "uom", mode="before")
    @classmethod
    def normalize_uppercase_codes(cls, v: Any) -> Any:
        if isinstance(v, str):
            return v.strip().upper()
        return v

    @field_validator("product_name", "category", mode="before")
    @classmethod
    def clean_strings(cls, v: Any) -> Any:
        if isinstance(v, str):
            return v.strip()
        return v

    @field_validator("sku")
    @classmethod
    def validate_sku_prefix(cls, v: str) -> str:
        if not (v.startswith("MAT-") or v.startswith("SKU-")):
            raise ValueError("SKU must start with 'MAT-' or 'SKU-' prefix (Enterprise MDG Rule)")
        return v


class ProductResponseSchema(ProductCreateSchema):
    validation_status: str = "VALID"
    validated_at: datetime = Field(default_factory=datetime.utcnow)

from typing import List

class RowRejectionDetail(BaseModel):
    row_number: int
    raw_sku: Optional[str] = None
    errors: List[str]
    raw_data: Dict[str, Any]


class BulkValidationSummarySchema(BaseModel):
    filename: str
    total_rows_processed: int
    valid_count: int
    rejected_count: int
    data_quality_score_pct: float
    valid_records: List[ProductResponseSchema]
    rejected_records: List[RowRejectionDetail]
