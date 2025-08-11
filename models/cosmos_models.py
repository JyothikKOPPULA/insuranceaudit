"""
Simple models for insurance claims audit system.
"""

from pydantic import BaseModel
from datetime import datetime
from typing import Optional

class AuditRecordRequest(BaseModel):
    claim_id: str
    customer_name: str
    process_name: str
    process_status: str  # pending, in_progress, completed, failed, cancelled
    process_details: str
    agent_name: str

class AuditRecordResponse(BaseModel):
    audit_id: str
    claim_id: str
    customer_id: str
    customer_name: str
    process_name: str
    process_status: str
    process_details: str
    agent_name: str
    timestamp: str
    created_at: str
    updated_at: str

class CosmosAuditRecord:
    def __init__(self, claim_id: str, customer_id: str, customer_name: str, 
                 process_name: str, process_status: str, process_details: str, 
                 agent_name: str, audit_id: Optional[str] = None):
        self.claim_id = claim_id
        self.customer_id = customer_id
        self.customer_name = customer_name
        self.process_name = process_name
        self.process_status = process_status
        self.process_details = process_details
        self.agent_name = agent_name
        
        # Generate audit_id if not provided
        self.audit_id = audit_id or self._generate_audit_id()
        
        # Timestamps
        current_time = datetime.utcnow().isoformat() + "Z"
        self.timestamp = current_time
        self.created_at = current_time
        self.updated_at = current_time
        
        # Cosmos DB document ID
        self.id = f"{self.customer_id}_{self.audit_id}"
    
    def _generate_audit_id(self) -> str:
        timestamp_part = datetime.utcnow().strftime("%Y%m%d%H%M%S")
        return f"AUD{timestamp_part}"
    
    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "audit_id": self.audit_id,
            "claim_id": self.claim_id,
            "customerId": self.customer_id,
            "customer_name": self.customer_name,
            "process_name": self.process_name,
            "process_status": self.process_status,
            "process_details": self.process_details,
            "agent_name": self.agent_name,
            "timestamp": self.timestamp,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "type": "audit_record"
        }
    
    @classmethod
    def from_dict(cls, data: dict):
        record = cls(
            claim_id=data["claim_id"],
            customer_id=data["customerId"],
            customer_name=data["customer_name"],
            process_name=data["process_name"],
            process_status=data["process_status"],
            process_details=data["process_details"],
            agent_name=data["agent_name"],
            audit_id=data["audit_id"]
        )
        record.timestamp = data.get("timestamp", record.timestamp)
        record.created_at = data.get("created_at", record.created_at)
        record.updated_at = data.get("updated_at", record.updated_at)
        record.id = data.get("id", record.id)
        return record
    
    def to_response_model(self) -> AuditRecordResponse:
        return AuditRecordResponse(
            audit_id=self.audit_id,
            claim_id=self.claim_id,
            customer_id=self.customer_id,
            customer_name=self.customer_name,
            process_name=self.process_name,
            process_status=self.process_status,
            process_details=self.process_details,
            agent_name=self.agent_name,
            timestamp=self.timestamp,
            created_at=self.created_at,
            updated_at=self.updated_at
        )
