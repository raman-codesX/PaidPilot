from fastapi import FastAPI

from app.api.webhooks import router as webhook_router
from app.api.dashboard import router as dashboard_router
from app.api.recommendations import router as recommendations_router
from app.api.approvals import router as approvals_router
from app.db.session import Base, engine


Base.metadata.create_all(bind=engine)

app = FastAPI(title="PaidPilot API")

app.include_router(webhook_router)
app.include_router(dashboard_router)
app.include_router(recommendations_router)
app.include_router(approvals_router)


@app.get("/")
def root():
    return {"message": "PaidPilot API is running"}
