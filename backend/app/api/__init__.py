from fastapi import APIRouter
from app.api.health import router as health_router
from app.api.patients import router as patients_router
from app.api.measurements import router as measurements_router
from app.api.twin import router as twin_router
from app.api.forecast import router as forecast_router
from app.api.simulation import router as simulation_router
from app.api.evaluation import router as evaluation_router
from app.api.web3_routes import router as web3_router

from app.api.auth import router as auth_router
from app.api.reports import router as reports_router
from app.api.videos import router as videos_router
from app.api.disease_tracker import router as disease_tracker_router
from app.api.cycle import router as cycle_router

api_router = APIRouter(prefix="/api")

api_router.include_router(health_router)
api_router.include_router(auth_router)
api_router.include_router(web3_router)
api_router.include_router(patients_router)
api_router.include_router(measurements_router)
api_router.include_router(twin_router)
api_router.include_router(forecast_router)
api_router.include_router(simulation_router)
api_router.include_router(evaluation_router)
api_router.include_router(reports_router)
api_router.include_router(videos_router)
api_router.include_router(disease_tracker_router)
api_router.include_router(cycle_router)

__all__ = ["api_router"]

