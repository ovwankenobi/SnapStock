from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.business_time import DateRange, InvalidRangeError, resolve_range
from app.core.deps import require_seller
from app.database import get_db
from app.models.user import User
from app.schemas.analytics import (
    AnalyticsOverview,
    AnalyticsSummary,
    ForecastResponse,
    Insight,
    InventoryHealthItem,
    SalesPatterns,
    SalesTrendPoint,
    TopProduct,
)
from app.services import analytics as analytics_service

router = APIRouter(prefix="/analytics", tags=["analytics"])


def period(
    range: str = Query(default="week", pattern="^(today|week|month|custom)$"),
    start: date | None = Query(default=None, description="Local date, for range=custom"),
    end: date | None = Query(default=None, description="Local date (inclusive), for range=custom"),
) -> DateRange:
    try:
        return resolve_range(range, start, end)
    except InvalidRangeError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.get("/summary", response_model=AnalyticsSummary)
def get_summary(
    seller: User = Depends(require_seller),
    db: Session = Depends(get_db),
):
    return analytics_service.get_summary(db, seller.id)


@router.get("/overview", response_model=AnalyticsOverview)
def get_overview(
    date_range: DateRange = Depends(period),
    seller: User = Depends(require_seller),
    db: Session = Depends(get_db),
):
    return analytics_service.get_overview(db, seller.id, date_range)


@router.get("/top-products", response_model=list[TopProduct])
def get_top_products(
    date_range: DateRange = Depends(period),
    limit: int = Query(default=5, ge=1, le=50),
    sort: str = Query(default="revenue", pattern="^(revenue|quantity|profit)$"),
    seller: User = Depends(require_seller),
    db: Session = Depends(get_db),
):
    return analytics_service.get_top_products(db, seller.id, date_range, limit, sort)


@router.get("/sales-trend", response_model=list[SalesTrendPoint])
def get_sales_trend(
    date_range: DateRange = Depends(period),
    granularity: str = Query(default="day", pattern="^(day|week|month)$"),
    seller: User = Depends(require_seller),
    db: Session = Depends(get_db),
):
    return analytics_service.get_sales_trend(db, seller.id, date_range, granularity)


@router.get("/patterns", response_model=SalesPatterns)
def get_patterns(
    weeks: int = Query(default=8, ge=1, le=26),
    seller: User = Depends(require_seller),
    db: Session = Depends(get_db),
):
    return analytics_service.get_patterns(db, seller.id, weeks)


@router.get("/inventory", response_model=list[InventoryHealthItem])
def get_inventory_health(
    seller: User = Depends(require_seller),
    db: Session = Depends(get_db),
):
    return analytics_service.get_inventory_health(db, seller.id)


@router.get("/forecast", response_model=ForecastResponse)
def get_forecast(
    seller: User = Depends(require_seller),
    db: Session = Depends(get_db),
):
    return analytics_service.get_forecast(db, seller.id)


@router.get("/insights", response_model=list[Insight])
def get_insights(
    seller: User = Depends(require_seller),
    db: Session = Depends(get_db),
):
    return analytics_service.get_insights(db, seller.id)
