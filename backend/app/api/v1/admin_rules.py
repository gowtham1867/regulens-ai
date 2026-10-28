from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.core.deps import get_current_user
from app.models.user import User, UserRole
from app.models.rule import RegulatoryRule, RegulatoryRuleVersion, ApplicationChecklist
from app.schemas.all_schemas import RegulatoryRuleResponse
from app.services.audit_service import record_audit_event

router = APIRouter(prefix="/admin", tags=["Administrative Rule Management"])


@router.get("/rules", response_model=List[RegulatoryRuleResponse])
def list_regulatory_rules(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    rules = db.query(RegulatoryRule).all()
    return rules


@router.patch("/rules/{rule_id}/toggle")
def toggle_rule_active(
    rule_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if current_user.role != UserRole.ADMINISTRATOR:
        raise HTTPException(status_code=403, detail="Only Administrators can modify regulatory rule configuration")

    rule = db.query(RegulatoryRule).filter(RegulatoryRule.id == rule_id).first()
    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")

    old_state = rule.is_active
    rule.is_active = not rule.is_active
    db.commit()

    record_audit_event(
        db=db,
        action="TOGGLE_RULE_ACTIVE_STATE",
        entity_type="REGULATORY_RULE",
        entity_id=str(rule.id),
        actor=current_user,
        before_state={"is_active": old_state},
        after_state={"is_active": rule.is_active},
        details=f"Rule {rule.rule_code} set to {'ACTIVE' if rule.is_active else 'INACTIVE'}."
    )

    return {"message": f"Rule {rule.rule_code} status updated", "is_active": rule.is_active}

