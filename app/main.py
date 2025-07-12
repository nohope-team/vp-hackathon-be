from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
# from aws_xray_sdk.core import xray_recorder
from aws_xray_sdk.core import patch_all
# from aws_xray_sdk.ext.fastapi import XRayMiddleware

# Load environment variables from .env file
load_dotenv()

from app.configs.settings import settings
from app.routes.chat import router as chat_router
from app.routes.flow import router as flow_router
from app.routes.facebook_workflow import router as facebook_workflow_router
from app.services.scheduler_service import scheduler_service
from app.utils.logger import app_logger

# Patch AWS SDK for X-Ray tracing
patch_all()

# Configure X-Ray
# xray_recorder.configure(
#     context_missing='LOG_ERROR',
#     plugins=('EC2Plugin', 'ECSPlugin'),
#     daemon_address='127.0.0.1:2000',
#     use_ssl=False
# )

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="Multi-Agent Platform Backend with Amazon Bedrock",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json"
)

# Add X-Ray middleware
# app.add_middleware(XRayMiddleware, recorder=xray_recorder)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if settings.environment == "development" else [],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(chat_router)
app.include_router(flow_router)
app.include_router(facebook_workflow_router)


@app.on_event("startup")
async def startup_event():
    """Application startup event"""
    app_logger.info(f"Starting {settings.app_name} v{settings.app_version}")
    app_logger.info(f"Environment: {settings.environment}")
    app_logger.info(f"AWS Region: {settings.aws_region}")
    
    # Start scheduler for n8n collection and Langfuse processing
    scheduler_service.start()


@app.on_event("shutdown")
async def shutdown_event():
    """Application shutdown event"""
    scheduler_service.stop()
    app_logger.info(f"Shutting down {settings.app_name}")


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": f"Welcome to {settings.app_name}",
        "version": settings.app_version,
        "status": "running"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.environment == "development",
        log_level=settings.log_level.lower()
    )