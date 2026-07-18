"""Card management API routes."""
from fastapi import APIRouter, Depends, HTTPException
from core.database import SessionLocal
from schemas.card import CardCreate, CardUpdate, CardResponse
from schemas.auth import UserInfo
from models.card import Card
from api.auth import get_current_user_dependency
from algorithm.interest import calc_interest_free_days
from algorithm.models import CardInfo
from datetime import date

router = APIRouter(prefix="/api/v1/cards", tags=["cards"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _to_card_info(card: Card) -> CardInfo:
    return CardInfo(
        card_id=int(card.id) if card.id else 0,
        bank_name=str(card.bank_name),
        credit_limit=card.credit_limit,
        temp_limit=card.temp_limit,
        used_limit=card.used_limit,
        overpayment=card.overpayment,
        bill_day=int(card.bill_day),
        due_day=int(card.due_day),
        swipe_fee_rate=card.swipe_fee_rate,
        interest_rate=card.interest_rate,
        min_payment_ratio=card.min_payment_ratio,
        installment_amount=card.installment_amount,
        bill_day_inclusive=bool(card.bill_day_inclusive),
    )


@router.post("", response_model=None)
def create_card(data: CardCreate, current_user: UserInfo = Depends(get_current_user_dependency),
                db=Depends(get_db)):
    card = Card(user_id=current_user.id, **data.model_dump())
    db.add(card)
    db.commit()
    db.refresh(card)
    return _format_response(card)


@router.get("", response_model=None)
def list_cards(current_user: UserInfo = Depends(get_current_user_dependency),
               db=Depends(get_db)):
    cards = db.query(Card).filter(
        Card.user_id == current_user.id,
        Card.deleted_at.is_(None)
    ).all()
    return [_format_response(c) for c in cards]


@router.get("/{card_id}", response_model=None)
def get_card(card_id: int, current_user: UserInfo = Depends(get_current_user_dependency),
             db=Depends(get_db)):
    card = db.query(Card).filter(
        Card.id == card_id,
        Card.user_id == current_user.id,
        Card.deleted_at.is_(None)
    ).first()
    if not card:
        raise HTTPException(status_code=404, detail="信用卡不存在")
    
    card_info = _to_card_info(card)
    free_days, repay_date, cycle = calc_interest_free_days(card_info, date.today())
    
    return {
        "card": _format_response(card),
        "interest_free_info": {
            "free_days": free_days,
            "repayment_date": str(repay_date),
            "billing_cycle": cycle.value,
        }
    }


@router.put("/{card_id}", response_model=None)
def update_card(card_id: int, data: CardUpdate,
                current_user: UserInfo = Depends(get_current_user_dependency),
                db=Depends(get_db)):
    card = db.query(Card).filter(
        Card.id == card_id,
        Card.user_id == current_user.id,
        Card.deleted_at.is_(None)
    ).first()
    if not card:
        raise HTTPException(status_code=404, detail="信用卡不存在")
    
    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(card, key, value)
    
    db.commit()
    db.refresh(card)
    return _format_response(card)


@router.delete("/{card_id}", response_model=None)
def delete_card(card_id: int, current_user: UserInfo = Depends(get_current_user_dependency),
                db=Depends(get_db)):
    card = db.query(Card).filter(
        Card.id == card_id,
        Card.user_id == current_user.id,
        Card.deleted_at.is_(None)
    ).first()
    if not card:
        raise HTTPException(status_code=404, detail="信用卡不存在")
    
    card.soft_delete()
    db.commit()
    return {"status": "ok", "message": "已删除"}


def _format_response(card: Card) -> dict:
    return {
        "id": int(card.id),
        "user_id": int(card.user_id),
        "bank_name": str(card.bank_name),
        "card_tail": str(card.card_tail or ""),
        "credit_limit": str(card.credit_limit),
        "temp_limit": str(card.temp_limit),
        "used_limit": str(card.used_limit),
        "overpayment": str(card.overpayment),
        "avail_limit": str(card.avail_limit),
        "bill_day": int(card.bill_day),
        "due_day": int(card.due_day),
        "swipe_fee_rate": str(card.swipe_fee_rate),
        "interest_rate": str(card.interest_rate),
        "min_payment_ratio": str(card.min_payment_ratio),
        "installment_amount": str(card.installment_amount),
        "bill_day_inclusive": int(card.bill_day_inclusive),
        "status": int(card.status),
    }
