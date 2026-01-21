"""API endpoints for subscription management."""

import logging
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.services.subscription_service import SubscriptionService
from backend.schemas.subscription import (
    SubscriptionCreate,
    SubscriptionUpdate,
    SubscriptionResponse,
    SubscriptionListResponse,
    LinkTransactionRequest,
    HistoricalValue
)

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("", response_model=SubscriptionResponse, status_code=201)
async def create_subscription(
    subscription: SubscriptionCreate,
    db: Session = Depends(get_db)
):
    """
    Create a new subscription.

    The subscription name must be unique.
    The pattern is used for exact matching of transaction descriptions.
    """
    subscription_service = SubscriptionService(db)

    try:
        created = subscription_service.create_subscription(
            name=subscription.name,
            pattern=subscription.pattern,
            description=subscription.description,
            initial_value=subscription.initial_value
        )

        return SubscriptionResponse(
            id=created.id,
            name=created.name,
            description=created.description,
            pattern=created.pattern,
            is_active=created.is_active,
            current_value=created.current_value,
            currency=created.currency,
            created_at=created.created_at,
            updated_at=created.updated_at,
            historical_values=[
                HistoricalValue(date=d.isoformat(), amount=a)
                for d, a in created.historical_values
            ]
        )

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("", response_model=SubscriptionListResponse)
async def get_subscriptions(
    active_only: bool = Query(False, description="Only return active subscriptions"),
    db: Session = Depends(get_db)
):
    """
    Get list of all subscriptions.

    Can filter to show only active subscriptions.
    """
    subscription_service = SubscriptionService(db)

    subscriptions = subscription_service.get_all_subscriptions(active_only=active_only)

    subscription_responses = [
        SubscriptionResponse(
            id=sub.id,
            name=sub.name,
            description=sub.description,
            pattern=sub.pattern,
            is_active=sub.is_active,
            current_value=sub.current_value,
            currency=sub.currency,
            created_at=sub.created_at,
            updated_at=sub.updated_at,
            historical_values=[
                HistoricalValue(date=d.isoformat(), amount=a)
                for d, a in sub.historical_values
            ]
        )
        for sub in subscriptions
    ]

    return SubscriptionListResponse(
        total=len(subscription_responses),
        subscriptions=subscription_responses
    )


@router.get("/{subscription_id}", response_model=SubscriptionResponse)
async def get_subscription(
    subscription_id: int,
    db: Session = Depends(get_db)
):
    """
    Get a single subscription by ID.
    """
    subscription_service = SubscriptionService(db)

    subscription = subscription_service.get_subscription(subscription_id)

    if not subscription:
        raise HTTPException(status_code=404, detail="Subscription not found")

    return SubscriptionResponse(
        id=subscription.id,
        name=subscription.name,
        description=subscription.description,
        pattern=subscription.pattern,
        is_active=subscription.is_active,
        current_value=subscription.current_value,
        currency=subscription.currency,
        created_at=subscription.created_at,
        updated_at=subscription.updated_at,
        historical_values=[
            HistoricalValue(date=d.isoformat(), amount=a)
            for d, a in subscription.historical_values
        ]
    )


@router.patch("/{subscription_id}", response_model=SubscriptionResponse)
async def update_subscription(
    subscription_id: int,
    subscription_update: SubscriptionUpdate,
    db: Session = Depends(get_db)
):
    """
    Update a subscription.

    Allows updating name, description, pattern, and active status.
    """
    subscription_service = SubscriptionService(db)

    subscription = subscription_service.update_subscription(
        subscription_id=subscription_id,
        name=subscription_update.name,
        description=subscription_update.description,
        pattern=subscription_update.pattern,
        is_active=subscription_update.is_active
    )

    if not subscription:
        raise HTTPException(status_code=404, detail="Subscription not found")

    logger.info(f"Updated subscription {subscription_id}")

    return SubscriptionResponse(
        id=subscription.id,
        name=subscription.name,
        description=subscription.description,
        pattern=subscription.pattern,
        is_active=subscription.is_active,
        current_value=subscription.current_value,
        currency=subscription.currency,
        created_at=subscription.created_at,
        updated_at=subscription.updated_at,
        historical_values=[
            HistoricalValue(date=d.isoformat(), amount=a)
            for d, a in subscription.historical_values
        ]
    )


@router.delete("/{subscription_id}")
async def delete_subscription(
    subscription_id: int,
    db: Session = Depends(get_db)
):
    """
    Delete a subscription.

    This will unlink all associated transactions but not delete them.
    """
    subscription_service = SubscriptionService(db)

    deleted = subscription_service.delete_subscription(subscription_id)

    if not deleted:
        raise HTTPException(status_code=404, detail="Subscription not found")

    logger.info(f"Deleted subscription {subscription_id}")

    return {"message": f"Subscription {subscription_id} deleted successfully"}


@router.post("/link", response_model=SubscriptionResponse)
async def link_transaction_to_subscription(
    link_request: LinkTransactionRequest,
    db: Session = Depends(get_db)
):
    """
    Link a transaction to a subscription.

    This updates the subscription's current_value to the transaction amount.
    """
    subscription_service = SubscriptionService(db)

    try:
        transaction, subscription = subscription_service.link_transaction_to_subscription(
            transaction_id=link_request.transaction_id,
            subscription_id=link_request.subscription_id
        )

        logger.info(f"Linked transaction {link_request.transaction_id} to subscription {link_request.subscription_id}")

        return SubscriptionResponse(
            id=subscription.id,
            name=subscription.name,
            description=subscription.description,
            pattern=subscription.pattern,
            is_active=subscription.is_active,
            current_value=subscription.current_value,
            currency=subscription.currency,
            created_at=subscription.created_at,
            updated_at=subscription.updated_at,
            historical_values=[
                HistoricalValue(date=d.isoformat(), amount=a)
                for d, a in subscription.historical_values
            ]
        )

    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.delete("/link/{transaction_id}")
async def unlink_transaction_from_subscription(
    transaction_id: int,
    db: Session = Depends(get_db)
):
    """
    Unlink a transaction from its subscription.
    """
    subscription_service = SubscriptionService(db)

    transaction = subscription_service.unlink_transaction_from_subscription(transaction_id)

    if not transaction:
        raise HTTPException(status_code=404, detail="Transaction not found")

    logger.info(f"Unlinked transaction {transaction_id} from subscription")

    return {"message": f"Transaction {transaction_id} unlinked successfully"}
