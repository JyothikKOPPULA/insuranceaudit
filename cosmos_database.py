"""
Simple Cosmos DB client for insurance claims audit system.
"""

import os
import logging
from azure.cosmos import CosmosClient, PartitionKey
from azure.cosmos.exceptions import CosmosHttpResponseError
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class CosmosDBClient:
    def __init__(self):
        self.endpoint = os.getenv('COSMOS_DB_ENDPOINT')
        self.key = os.getenv('COSMOS_DB_KEY')
        self.database_name = os.getenv('COSMOS_DB_DATABASE_NAME')
        
        if not all([self.endpoint, self.key, self.database_name]):
            raise ValueError("Missing required Cosmos DB environment variables")
        
        self.client = CosmosClient(self.endpoint, self.key)
        self._setup_database()
    
    def _setup_database(self):
        try:
            # Create database if not exists (no throughput for serverless accounts)
            self.database = self.client.create_database_if_not_exists(
                id=self.database_name
            )
            
            # Create audit container (no throughput for serverless accounts)
            self.audit_container = self.database.create_container_if_not_exists(
                id="insurance_claims_audit",
                partition_key=PartitionKey(path="/customerId")
            )
            
            logger.info("Cosmos DB setup completed successfully")
            
        except Exception as e:
            logger.error(f"Failed to setup Cosmos DB: {str(e)}")
            raise
    
    def get_audit_container(self):
        return self.audit_container

# Global client instance
_cosmos_client = None

def get_cosmos_client():
    global _cosmos_client
    if _cosmos_client is None:
        _cosmos_client = CosmosDBClient()
    return _cosmos_client

def get_audit_container():
    client = get_cosmos_client()
    return client.get_audit_container()

def check_cosmos_connection():
    try:
        client = get_cosmos_client()
        db_properties = client.database.read()
        return {
            "status": "connected",
            "database_name": db_properties.get("id")
        }
    except Exception as e:
        return {
            "status": "disconnected",
            "error": str(e)
        }
