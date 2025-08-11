"""
FastAPI application for insurance claims audit system using Azure Cosmos DB.
"""

from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime
import logging
import os
import uvicorn
from dotenv import load_dotenv

from cosmos_database import get_audit_container, check_cosmos_connection
from azure.cosmos.exceptions import CosmosHttpResponseError
from models.cosmos_models import (
    AuditRecordRequest,
    AuditRecordResponse,
    CosmosAuditRecord
)

load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Get root_path from environment variable, default to "" for local development
root_path = os.getenv("ROOT_PATH", "")

app = FastAPI(
    title="Agent Logging API",
    description="REST API for agent logging and audit trail management. Supports agent activity logging to Azure Cosmos DB.",
    version="1.0.0",
    root_path=root_path,
    openapi_url="/openapi.json",
    docs_url="/docs",
    redoc_url="/redoc",
    servers=[
        {
            "url": "https://cosmosaudit.azurewebsites.net"
        }
    ],
    openapi_tags=[
        {
            "name": "Logging",
            "description": "Operations for agent logging"
        },
        {
            "name": "Health",
            "description": "Health check endpoints"
        }
    ]
)

# Add CORS middleware with security considerations
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"]
)

def extract_customer_id_from_claim(claim_id: str) -> str:
    """Extract customer ID from claim ID."""
    if "_" in claim_id:
        return claim_id.split("_")[0]
    elif len(claim_id) >= 6:
        return claim_id[:6].upper()
    else:
        return f"CUST_{claim_id}"

@app.post("/audit", response_model=dict, tags=["Logging"])
async def create_audit_record(
    record: AuditRecordRequest,
    container = Depends(get_audit_container)
):
    """Create a new audit record."""
    try:
        # Extract customer ID from claim ID
        customer_id = extract_customer_id_from_claim(record.claim_id)
        
        # Create Cosmos DB audit record
        cosmos_record = CosmosAuditRecord(
            claim_id=record.claim_id,
            customer_id=customer_id,
            customer_name=record.customer_name,
            process_name=record.process_name,
            process_status=record.process_status,
            process_details=record.process_details,
            agent_name=record.agent_name
        )
        
        # Store in Cosmos DB
        created_item = container.create_item(
            body=cosmos_record.to_dict(),
            enable_automatic_id_generation=False
        )
        
        logger.info(f"Created audit record {cosmos_record.audit_id} for customer {customer_id}")
        
        return {
            "message": "Audit record created successfully",
            "record": cosmos_record.to_response_model().dict()
        }
        
    except CosmosHttpResponseError as e:
        logger.error(f"Cosmos DB error: {e.message}")
        if e.status_code == 409:
            raise HTTPException(status_code=409, detail="Audit record already exists")
        else:
            raise HTTPException(status_code=500, detail=f"Database error: {e.message}")
    except Exception as e:
        logger.error(f"Error creating audit record: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to create audit record: {str(e)}")

@app.get("/audit/{customer_id}", response_model=dict, tags=["Logging"])
async def get_audit_records_by_customer(
    customer_id: str,
    container = Depends(get_audit_container)
):
    """Get all audit records for a specific customer."""
    try:
        # Query audit records for the specific customer
        query = "SELECT * FROM c WHERE c.customerId = @customer_id AND c.type = @type ORDER BY c.timestamp ASC"
        parameters = [
            {"name": "@customer_id", "value": customer_id},
            {"name": "@type", "value": "audit_record"}
        ]
        
        items = list(container.query_items(
            query=query,
            parameters=parameters,
            partition_key=customer_id,
            enable_cross_partition_query=False
        ))
        
        if not items:
            raise HTTPException(status_code=404, detail=f"No audit records found for customer: {customer_id}")
        
        # Convert to response models
        audit_records = []
        for item in items:
            cosmos_record = CosmosAuditRecord.from_dict(item)
            audit_records.append(cosmos_record.to_response_model())
        
        logger.info(f"Retrieved {len(audit_records)} audit records for customer {customer_id}")
        
        return {
            "records": [record.dict() for record in audit_records]
        }
        
    except HTTPException:
        raise
    except CosmosHttpResponseError as e:
        logger.error(f"Cosmos DB error: {e.message}")
        raise HTTPException(status_code=500, detail=f"Database error: {e.message}")
    except Exception as e:
        logger.error(f"Error retrieving audit records: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve audit records: {str(e)}")

@app.get("/", tags=["Health"])
def read_root():
    """Welcome endpoint."""
    return {
        "message": "Welcome to Insurance Claims Audit API",
        "endpoints": {
            "create_audit": "POST /audit",
            "get_audits": "GET /audit/{customer_id}",
            "health_check": "GET /health",
            "docs": "GET /docs"
        }
    }

@app.get("/health", tags=["Health"])
async def health_check():
    """Health check endpoint."""
    try:
        cosmos_status = check_cosmos_connection()
        
        return {
            "status": "healthy" if cosmos_status["status"] == "connected" else "unhealthy",
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "database": cosmos_status["status"],
            "database_name": cosmos_status.get("database_name"),
            "environment": os.getenv("ENV", "production")
        }
        
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        return {
            "status": "unhealthy",
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "database": "error",
            "error": str(e)
        }

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=int(os.getenv("PORT", 8000)),
        reload=os.getenv("ENV", "dev") == "dev"
    )
