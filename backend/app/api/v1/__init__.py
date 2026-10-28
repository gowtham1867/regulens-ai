from fastapi import APIRouter
from app.api.v1.auth import router as auth_router
from app.api.v1.applications import router as applications_router
from app.api.v1.documents import router as documents_router
from app.api.v1.validation import router as validation_router
from app.api.v1.verification import router as verification_router
from app.api.v1.trustgraph import router as trustgraph_router
from app.api.v1.clarifications import router as clarifications_router
from app.api.v1.officer_reviews import router as officer_reviews_router
from app.api.v1.reports import router as reports_router
from app.api.v1.audit import router as audit_router
from app.api.v1.admin_rules import router as admin_rules_router
from app.api.v1.evaluation import router as evaluation_router
from app.api.v1.notifications import router as notifications_router

api_router = APIRouter()
api_router.include_router(auth_router)
api_router.include_router(applications_router)
api_router.include_router(documents_router)
api_router.include_router(validation_router)
api_router.include_router(verification_router)
api_router.include_router(trustgraph_router)
api_router.include_router(clarifications_router)
api_router.include_router(officer_reviews_router)
api_router.include_router(reports_router)
api_router.include_router(audit_router)
api_router.include_router(admin_rules_router)
api_router.include_router(evaluation_router)
api_router.include_router(notifications_router)

