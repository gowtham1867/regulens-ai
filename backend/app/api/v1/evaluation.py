from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.core.deps import get_current_user
from app.models.user import User, UserRole
from app.services.evaluation_service import EvaluationBenchmarkService
from app.services.audit_service import record_audit_event

router = APIRouter(prefix="/admin/evaluation", tags=["Testing and Evaluation Benchmark"])


@router.post("/run-suite")
def run_evaluation_benchmark_suite(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if current_user.role not in [UserRole.AICTE_OFFICER, UserRole.ADMINISTRATOR]:
        raise HTTPException(status_code=403, detail="Unauthorized")

    service = EvaluationBenchmarkService(db)
    benchmark_report = service.run_13_case_evaluation_suite()

    record_audit_event(
        db=db,
        action="RUN_EVALUATION_BENCHMARK",
        entity_type="SYSTEM",
        entity_id="BENCHMARK_SUITE_13",
        actor=current_user,
        details=f"Ran 13-case benchmark. Pass rate: {benchmark_report['pass_rate_percentage']}% ({benchmark_report['passed_tests']}/{benchmark_report['total_tests']})."
    )

    return benchmark_report

