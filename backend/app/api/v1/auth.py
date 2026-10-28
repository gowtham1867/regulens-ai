from typing import Optional
from datetime import timedelta
from pydantic import BaseModel
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.config import settings
from app.core.security import verify_password, create_access_token, get_password_hash
from app.core.deps import get_current_user
from app.models.user import User, UserRole
from app.models.institution import InstitutionMembership, Institution
from app.schemas.all_schemas import Token, LoginRequest, RegisterRequest, UserResponse
from app.services.audit_service import record_audit_event

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/login", response_model=Token)
def login(
    login_data: LoginRequest,
    portal: Optional[str] = Query(None, description="Optional portal target: 'INSTITUTION' or 'OFFICER'"),
    db: Session = Depends(get_db)
):
    user = db.query(User).filter(User.email == login_data.email.strip().lower()).first()
    if not user or not verify_password(login_data.password, user.hashed_password):
        # Audit login failure
        record_audit_event(
            db=db,
            action="LOGIN_FAILED",
            entity_type="USER",
            entity_id=login_data.email,
            details=f"Invalid credentials attempted for {login_data.email} via portal {portal or 'GENERAL'}"
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Account is deactivated")

    # Portal-specific role enforcement
    if portal:
        portal_upper = portal.strip().upper()
        if portal_upper == "INSTITUTION" and user.role != UserRole.INSTITUTION_USER:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="This portal is exclusively reserved for academic institutions. Please sign in via the AICTE Officer Portal."
            )
        elif portal_upper == "OFFICER" and user.role == UserRole.INSTITUTION_USER:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Institutional user accounts cannot access the AICTE Scrutiny Officer Portal. Please sign in via the Institution Portal."
            )

    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        subject=user.id,
        role=user.role.value,
        expires_delta=access_token_expires
    )

    # Get institution info if user is institution user
    inst_id = None
    inst_name = None
    approval_status = "APPROVED"
    if user.role == UserRole.INSTITUTION_USER:
        membership = db.query(InstitutionMembership).filter(
            InstitutionMembership.user_id == user.id
        ).first()
        if membership:
            inst_id = membership.institution_id
            inst_name = membership.institution.name
            approval_status = membership.institution.approval_status or "APPROVED"

    # Audit login success
    record_audit_event(
        db=db,
        action="LOGIN_SUCCESS",
        entity_type="USER",
        entity_id=str(user.id),
        actor=user,
        details=f"User {user.email} logged in with role {user.role.value}"
    )

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "role": user.role.value,
        "user_id": user.id,
        "full_name": user.full_name,
        "email": user.email,
        "institution_id": inst_id,
        "institution_name": inst_name,
        "approval_status": approval_status
    }


@router.post("/register", response_model=Token)
def register_institution(reg_data: RegisterRequest, db: Session = Depends(get_db)):
    clean_email = reg_data.email.strip().lower()

    # Password strength validation (min 8 chars)
    if not reg_data.password or len(reg_data.password) < 8:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must be at least 8 characters long for regulatory security compliance."
        )

    # Check existing user
    existing_user = db.query(User).filter(User.email == clean_email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="An account with this email address already exists. Please sign in."
        )

    # Check for existing institution duplicate by AICTE ID or exact Name
    inst = None
    if reg_data.aicte_id and reg_data.aicte_id.strip():
        inst = db.query(Institution).filter(Institution.aicte_id == reg_data.aicte_id.strip()).first()
    if not inst and reg_data.institution_name:
        inst = db.query(Institution).filter(Institution.name.ilike(reg_data.institution_name.strip())).first()

    if inst:
        # Check if institution already has an authorized primary contact user
        has_primary = db.query(InstitutionMembership).filter(
            InstitutionMembership.institution_id == inst.id,
            InstitutionMembership.is_primary_contact == True
        ).first()
        if has_primary:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"An authorized account already exists for '{inst.name}'. Please sign in or contact your institutional registrar."
            )
    else:
        aicte_id = reg_data.aicte_id.strip() if (reg_data.aicte_id and reg_data.aicte_id.strip()) else f"1-{abs(hash(reg_data.institution_name)) % 9000000000 + 1000000000}"
        inst = Institution(
            aicte_id=aicte_id,
            name=reg_data.institution_name.strip(),
            address=reg_data.address.strip() if reg_data.address else "Campus Address",
            state=reg_data.state.strip() if reg_data.state else "Delhi",
            district=reg_data.district.strip() if reg_data.district else "New Delhi",
            pin_code=reg_data.pin_code.strip() if reg_data.pin_code else "110001",
            institution_type=reg_data.institution_type or "ENGINEERING_AND_TECHNOLOGY",
            contact_email=reg_data.institution_email.strip().lower() if reg_data.institution_email else clean_email,
            contact_phone=reg_data.contact_phone or reg_data.phone or "9876543210",
            approved_intake=reg_data.approved_intake or 300,
            land_area_acres=str(reg_data.land_area_acres or 5.0),
            approval_status="PENDING_VERIFICATION"
        )
        db.add(inst)
        db.flush()

    new_user = User(
        email=clean_email,
        hashed_password=get_password_hash(reg_data.password),
        full_name=reg_data.full_name.strip(),
        role=UserRole.INSTITUTION_USER,
        designation=reg_data.designation or "Authorized Representative",
        is_active=True
    )
    db.add(new_user)
    db.flush()

    membership = InstitutionMembership(
        user_id=new_user.id,
        institution_id=inst.id,
        is_primary_contact=True
    )
    db.add(membership)
    db.commit()
    db.refresh(new_user)
    db.refresh(inst)

    record_audit_event(
        db=db,
        action="REGISTER_INSTITUTION",
        entity_type="USER",
        entity_id=str(new_user.id),
        actor=new_user,
        details=f"New institution account registered: '{inst.name}' ({inst.aicte_id}) by {new_user.email}. Verification status: PENDING_VERIFICATION"
    )

    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        subject=new_user.id,
        role=new_user.role.value,
        expires_delta=access_token_expires
    )

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "role": new_user.role.value,
        "user_id": new_user.id,
        "full_name": new_user.full_name,
        "email": new_user.email,
        "institution_id": inst.id,
        "institution_name": inst.name,
        "approval_status": inst.approval_status
    }


@router.get("/institutions/pending")
def list_pending_institutions(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if current_user.role not in [UserRole.AICTE_OFFICER, UserRole.ADMINISTRATOR]:
        raise HTTPException(status_code=403, detail="Only authorized AICTE Officers can inspect pending institution registrations")

    pending_insts = db.query(Institution).filter(
        Institution.approval_status == "PENDING_VERIFICATION"
    ).all()

    return [
        {
            "id": inst.id,
            "aicte_id": inst.aicte_id,
            "name": inst.name,
            "institution_type": inst.institution_type,
            "state": inst.state,
            "district": inst.district,
            "contact_email": inst.contact_email,
            "contact_phone": inst.contact_phone,
            "approval_status": inst.approval_status,
            "created_at": inst.created_at
        }
        for inst in pending_insts
    ]


class InstitutionVerifyPayload(BaseModel):
    approval_status: Optional[str] = "APPROVED"


@router.patch("/institutions/{institution_id}/verify")
def verify_institution_registration(
    institution_id: int,
    payload: Optional[InstitutionVerifyPayload] = None,
    approval_status: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if current_user.role not in [UserRole.AICTE_OFFICER, UserRole.ADMINISTRATOR]:
        raise HTTPException(status_code=403, detail="Only authorized AICTE Officers can verify institutions")

    inst = db.query(Institution).filter(Institution.id == institution_id).first()
    if not inst:
        raise HTTPException(status_code=404, detail="Institution not found")

    target_status = "APPROVED"
    if payload and payload.approval_status:
        target_status = payload.approval_status.upper()
    elif approval_status:
        target_status = approval_status.upper()

    old_status = inst.approval_status
    inst.approval_status = target_status
    db.commit()

    record_audit_event(
        db=db,
        action="VERIFY_INSTITUTION_REGISTRATION",
        entity_type="INSTITUTION",
        entity_id=str(inst.id),
        actor=current_user,
        before_state={"status": old_status},
        after_state={"status": inst.approval_status},
        details=f"Officer {current_user.full_name} set verification status of '{inst.name}' to {inst.approval_status}"
    )

    return {
        "message": f"Institution verification status updated to {inst.approval_status}",
        "institution_id": inst.id,
        "approval_status": inst.approval_status
    }


@router.get("/me", response_model=UserResponse)
def get_current_user_profile(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    inst_id = None
    inst_name = None
    if current_user.role == UserRole.INSTITUTION_USER:
        membership = db.query(InstitutionMembership).filter(
            InstitutionMembership.user_id == current_user.id
        ).first()
        if membership:
            inst_id = membership.institution_id
            inst_name = membership.institution.name

    return {
        "id": current_user.id,
        "email": current_user.email,
        "full_name": current_user.full_name,
        "role": current_user.role.value,
        "designation": current_user.designation,
        "is_active": current_user.is_active,
        "institution_id": inst_id,
        "institution_name": inst_name
    }


@router.post("/logout")
def logout(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    record_audit_event(
        db=db,
        action="LOGOUT",
        entity_type="USER",
        entity_id=str(current_user.id),
        actor=current_user,
        details="User session terminated"
    )
    return {"message": "Session terminated successfully"}

