from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.core.deps import get_current_user
from app.models.user import User, UserRole
from app.models.institution import InstitutionMembership
from app.models.application import Application
from app.services.trustgraph_service import TrustGraphService

router = APIRouter(tags=["TrustGraph Evidence Registry"])


@router.get("/applications/{application_id}/trustgraph")
def get_application_trustgraph(
    application_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    app = db.query(Application).filter(Application.id == application_id).first()
    if not app:
        raise HTTPException(status_code=404, detail="Application not found")

    if current_user.role == UserRole.INSTITUTION_USER:
        membership = db.query(InstitutionMembership).filter(
            InstitutionMembership.user_id == current_user.id
        ).first()
        if not membership or membership.institution_id != app.institution_id:
            raise HTTPException(status_code=403, detail="Unauthorized")

    service = TrustGraphService(db)
    graph_data = service.generate_graph_for_application(application_id)
    return graph_data

