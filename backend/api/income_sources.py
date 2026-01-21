"""API endpoints for income source management."""

import logging
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.services.income_source_service import IncomeSourceService
from backend.schemas.income_source import (
    IncomeSourceCreate,
    IncomeSourceUpdate,
    IncomeSourceResponse,
    IncomeSourceListResponse,
    LinkTransactionRequest,
    UpdateExpectedAmountRequest,
    HistoryEntry
)

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("", response_model=IncomeSourceResponse, status_code=201)
async def create_income_source(
    income_source: IncomeSourceCreate,
    db: Session = Depends(get_db)
):
    """
    Create a new income source.

    The income source name must be unique.
    Creates an initial history entry with the provided expected amount.
    """
    income_source_service = IncomeSourceService(db)

    try:
        created = income_source_service.create_income_source(
            name=income_source.name,
            initial_expected_amount=income_source.initial_expected_amount,
            cnpj=income_source.cnpj,
            description=income_source.description
        )

        return IncomeSourceResponse(
            id=created.id,
            name=created.name,
            cnpj=created.cnpj,
            description=created.description,
            is_active=created.is_active,
            current_expected_amount=created.current_expected_amount,
            currency=created.currency,
            created_at=created.created_at,
            updated_at=created.updated_at,
            historical_values=[
                HistoryEntry(date=d.isoformat(), amount=a, note=None)
                for d, a in created.historical_values
            ]
        )

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("", response_model=IncomeSourceListResponse)
async def get_income_sources(
    active_only: bool = Query(False, description="Only return active income sources"),
    db: Session = Depends(get_db)
):
    """
    Get list of all income sources.

    Can filter to show only active income sources.
    """
    income_source_service = IncomeSourceService(db)

    income_sources = income_source_service.get_all_income_sources(active_only=active_only)

    income_source_responses = [
        IncomeSourceResponse(
            id=source.id,
            name=source.name,
            cnpj=source.cnpj,
            description=source.description,
            is_active=source.is_active,
            current_expected_amount=source.current_expected_amount,
            currency=source.currency,
            created_at=source.created_at,
            updated_at=source.updated_at,
            historical_values=[
                HistoryEntry(date=d.isoformat(), amount=a, note=None)
                for d, a in source.historical_values
            ]
        )
        for source in income_sources
    ]

    return IncomeSourceListResponse(
        total=len(income_source_responses),
        income_sources=income_source_responses
    )


@router.get("/{income_source_id}", response_model=IncomeSourceResponse)
async def get_income_source(
    income_source_id: int,
    db: Session = Depends(get_db)
):
    """
    Get a single income source by ID.
    """
    income_source_service = IncomeSourceService(db)

    income_source = income_source_service.get_income_source(income_source_id)

    if not income_source:
        raise HTTPException(status_code=404, detail="Income source not found")

    return IncomeSourceResponse(
        id=income_source.id,
        name=income_source.name,
        cnpj=income_source.cnpj,
        description=income_source.description,
        is_active=income_source.is_active,
        current_expected_amount=income_source.current_expected_amount,
        currency=income_source.currency,
        created_at=income_source.created_at,
        updated_at=income_source.updated_at,
        historical_values=[
            HistoryEntry(date=d.isoformat(), amount=a, note=None)
            for d, a in income_source.historical_values
        ]
    )


@router.patch("/{income_source_id}", response_model=IncomeSourceResponse)
async def update_income_source(
    income_source_id: int,
    income_source_update: IncomeSourceUpdate,
    db: Session = Depends(get_db)
):
    """
    Update income source metadata (name, CNPJ, description, active status).

    To update the expected amount, use the PATCH /{income_source_id}/expected-amount endpoint.
    """
    income_source_service = IncomeSourceService(db)

    try:
        updated = income_source_service.update_income_source(
            income_source_id=income_source_id,
            name=income_source_update.name,
            cnpj=income_source_update.cnpj,
            description=income_source_update.description,
            is_active=income_source_update.is_active
        )

        if not updated:
            raise HTTPException(status_code=404, detail="Income source not found")

        return IncomeSourceResponse(
            id=updated.id,
            name=updated.name,
            cnpj=updated.cnpj,
            description=updated.description,
            is_active=updated.is_active,
            current_expected_amount=updated.current_expected_amount,
            currency=updated.currency,
            created_at=updated.created_at,
            updated_at=updated.updated_at,
            historical_values=[
                HistoryEntry(date=d.isoformat(), amount=a, note=None)
                for d, a in updated.historical_values
            ]
        )

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.patch("/{income_source_id}/expected-amount", response_model=IncomeSourceResponse)
async def update_expected_amount(
    income_source_id: int,
    update_request: UpdateExpectedAmountRequest,
    db: Session = Depends(get_db)
):
    """
    Update the expected monthly amount for an income source.

    Creates a new history entry to track the change.
    """
    income_source_service = IncomeSourceService(db)

    try:
        updated = income_source_service.update_expected_amount(
            income_source_id=income_source_id,
            new_amount=update_request.expected_amount,
            note=update_request.note
        )

        if not updated:
            raise HTTPException(status_code=404, detail="Income source not found")

        return IncomeSourceResponse(
            id=updated.id,
            name=updated.name,
            cnpj=updated.cnpj,
            description=updated.description,
            is_active=updated.is_active,
            current_expected_amount=updated.current_expected_amount,
            currency=updated.currency,
            created_at=updated.created_at,
            updated_at=updated.updated_at,
            historical_values=[
                HistoryEntry(date=d.isoformat(), amount=a, note=None)
                for d, a in updated.historical_values
            ]
        )

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/{income_source_id}")
async def delete_income_source(
    income_source_id: int,
    db: Session = Depends(get_db)
):
    """
    Delete an income source.

    This will unlink all associated transactions but not delete them.
    History entries are cascade deleted.
    """
    income_source_service = IncomeSourceService(db)

    success = income_source_service.delete_income_source(income_source_id)

    if not success:
        raise HTTPException(status_code=404, detail="Income source not found")

    return {"message": "Income source deleted successfully"}


@router.post("/link")
async def link_transaction(
    link_request: LinkTransactionRequest,
    db: Session = Depends(get_db)
):
    """
    Link a transaction to an income source.

    Only INCOME type transactions can be linked to income sources.
    """
    income_source_service = IncomeSourceService(db)

    try:
        transaction = income_source_service.link_transaction_to_income_source(
            transaction_id=link_request.transaction_id,
            income_source_id=link_request.income_source_id
        )

        return {
            "message": "Transaction linked successfully",
            "transaction_id": transaction.id,
            "income_source_id": link_request.income_source_id
        }

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/link/{transaction_id}")
async def unlink_transaction(
    transaction_id: int,
    db: Session = Depends(get_db)
):
    """
    Unlink a transaction from its income source.
    """
    income_source_service = IncomeSourceService(db)

    transaction = income_source_service.unlink_transaction_from_income_source(transaction_id)

    if not transaction:
        raise HTTPException(status_code=404, detail="Transaction not found")

    return {
        "message": "Transaction unlinked successfully",
        "transaction_id": transaction.id
    }


@router.get("/{income_source_id}/history")
async def get_income_source_history(
    income_source_id: int,
    db: Session = Depends(get_db)
):
    """
    Get historical expected amount changes for an income source.
    """
    income_source_service = IncomeSourceService(db)

    history = income_source_service.get_income_source_history(income_source_id)

    if history is None:
        raise HTTPException(status_code=404, detail="Income source not found")

    return {
        "income_source_id": income_source_id,
        "history": [
            {
                "id": entry.id,
                "expected_amount": entry.expected_amount,
                "effective_date": entry.effective_date.isoformat(),
                "note": entry.note
            }
            for entry in history
        ]
    }
