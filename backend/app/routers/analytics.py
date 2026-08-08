from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.deps import require_seller
from app.database import get_db
from app.models.user import User
from app.schemas.analytics import AnalyticsSummary, ProductForecast, SalesTrendPoint, TopProduct
from app.services import analytics as analytics_service

router = APIRouter(prefix="/analytics", tags=["analytics"])

RangeQuery = Query(default="week", pattern="^(today|week|month)$")


@router.get("/summary", response_model=AnalyticsSummary)
def get_summary(
    seller: User = Depends(require_seller),
    db: Session = Depends(get_db),
):
    return analytics_service.get_summary(db, seller.id)


@router.get("/top-products", response_model=list[TopProduct])
def get_top_products(
    range: str = RangeQuery,
    limit: int = Query(default=5, ge=1, le=50),
    seller: User = Depends(require_seller),
    db: Session = Depends(get_db),
):
    return analytics_service.get_top_products(db, seller.id, range, limit)


@router.get("/sales-trend", response_model=list[SalesTrendPoint])
def get_sales_trend(
    range: str = RangeQuery,
    seller: User = Depends(require_seller),
    db: Session = Depends(get_db),
):
    return analytics_service.get_sales_trend(db, seller.id, range)


@router.get("/forecast", response_model=list[ProductForecast])
def get_forecast(
    seller: User = Depends(require_seller),
    db: Session = Depends(get_db),
):
    return analytics_service.get_forecast(db, seller.id)
