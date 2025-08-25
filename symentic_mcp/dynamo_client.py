"""DynamoDB client for Symentic MCP Server."""

import os
import json
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
from decimal import Decimal

import boto3
from boto3.dynamodb.conditions import Key, Attr
from botocore.exceptions import ClientError

from .models import UserProfile, Enrichment, EnrichmentInput

logger = logging.getLogger(__name__)


class DynamoDBClient:
    """Client for interacting with DynamoDB SymenticProfileEngrams table."""
    
    def __init__(self, table_name: str, aws_profile: str = "leogao", region: str = "us-east-1"):
        """Initialize DynamoDB client with specified profile and region."""
        self.table_name = table_name
        self.aws_profile = aws_profile
        self.region = region
        
        # Set up AWS session with profile
        if aws_profile:
            session = boto3.Session(profile_name=aws_profile)
        else:
            session = boto3.Session()
        
        # Create DynamoDB resource
        self.dynamodb = session.resource('dynamodb', region_name=region)
        self.table = self.dynamodb.Table(table_name)
        
        logger.info(f"Connected to DynamoDB table: {table_name} in region: {region}")
    
    def _serialize_item(self, item: Dict[str, Any]) -> Dict[str, Any]:
        """Convert Python dict to DynamoDB format."""
        def serialize_value(value):
            if isinstance(value, dict):
                return {"M": {k: serialize_value(v) for k, v in value.items()}}
            elif isinstance(value, list):
                return {"L": [serialize_value(v) for v in value]}
            elif isinstance(value, bool):
                return {"BOOL": value}
            elif isinstance(value, (int, float)):
                return {"N": str(value)}
            elif value is None:
                return {"NULL": True}
            else:
                return {"S": str(value)}
        
        return {k: serialize_value(v) for k, v in item.items()}
    
    def _deserialize_item(self, item: Dict[str, Any]) -> Dict[str, Any]:
        """Convert DynamoDB format to Python dict."""
        def deserialize_value(value):
            if "M" in value:
                return {k: deserialize_value(v) for k, v in value["M"].items()}
            elif "L" in value:
                return [deserialize_value(v) for v in value["L"]]
            elif "BOOL" in value:
                return value["BOOL"]
            elif "N" in value:
                return float(value["N"]) if "." in value["N"] else int(value["N"])
            elif "S" in value:
                return value["S"]
            elif "NULL" in value:
                return None
            else:
                return value
        
        return {k: deserialize_value(v) for k, v in item.items()}
    
    def get_user_profile(self, business_id: str, user_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific user profile by business ID and user ID."""
        try:
            pk = f"symentic_{business_id.lower()}"
            sk = f"USER#{user_id}"
            
            response = self.table.get_item(
                Key={
                    'PK': pk,
                    'SK': sk
                }
            )
            
            if 'Item' in response:
                return response['Item']
            return None
            
        except ClientError as e:
            logger.error(f"Error getting user profile: {e}")
            raise
    
    def list_users(self, business_id: Optional[str] = None, limit: int = 100) -> List[Dict[str, Any]]:
        """List all users, optionally filtered by business ID."""
        try:
            if business_id:
                pk = f"symentic_{business_id.lower()}"
                response = self.table.query(
                    KeyConditionExpression=Key('PK').eq(pk) & Key('SK').begins_with('USER#'),
                    Limit=limit
                )
                return response.get('Items', [])
            else:
                # Scan all users (less efficient)
                response = self.table.scan(
                    FilterExpression=Attr('SK').begins_with('USER#'),
                    Limit=limit
                )
                return response.get('Items', [])
                
        except ClientError as e:
            logger.error(f"Error listing users: {e}")
            raise
    
    def search_users_by_type(self, business_id: str, user_type: str) -> List[Dict[str, Any]]:
        """Search users by type (internal/external) using GSI."""
        try:
            gsi1_pk = f"symentic_{business_id.lower()}"
            gsi1_sk = f"TYPE#{user_type}#USER#"
            
            response = self.table.query(
                IndexName='GSI1',
                KeyConditionExpression=Key('GSI1PK').eq(gsi1_pk) & Key('GSI1SK').begins_with(gsi1_sk)
            )
            
            return response.get('Items', [])
            
        except ClientError as e:
            logger.error(f"Error searching users by type: {e}")
            raise
    
    def update_user_profile(self, business_id: str, user_id: str, updates: Dict[str, Any]) -> Dict[str, Any]:
        """Update user profile attributes."""
        try:
            pk = f"symentic_{business_id.lower()}"
            sk = f"USER#{user_id}"
            
            # Build update expression
            update_expr_parts = []
            expr_attr_names = {}
            expr_attr_values = {}
            
            for key, value in updates.items():
                # Handle reserved keywords
                attr_name = f"#{key}"
                attr_value = f":{key}"
                
                update_expr_parts.append(f"{attr_name} = {attr_value}")
                expr_attr_names[attr_name] = key
                expr_attr_values[attr_value] = value
            
            # Add lastUpdated
            update_expr_parts.append("#lastUpdated = :lastUpdated")
            expr_attr_names["#lastUpdated"] = "lastUpdated"
            expr_attr_values[":lastUpdated"] = datetime.utcnow().isoformat() + "Z"
            
            update_expression = "SET " + ", ".join(update_expr_parts)
            
            response = self.table.update_item(
                Key={'PK': pk, 'SK': sk},
                UpdateExpression=update_expression,
                ExpressionAttributeNames=expr_attr_names,
                ExpressionAttributeValues=expr_attr_values,
                ReturnValues="ALL_NEW"
            )
            
            return response['Attributes']
            
        except ClientError as e:
            logger.error(f"Error updating user profile: {e}")
            raise
    
    def add_enrichment(self, business_id: str, user_id: str, enrichment: EnrichmentInput) -> Dict[str, Any]:
        """Add a new enrichment to a user profile."""
        try:
            pk = f"symentic_{business_id.lower()}"
            sk = f"USER#{user_id}"
            
            # Prepare enrichment data
            enrichment_data = {
                "M": {
                    "agent": {"S": enrichment.agent},
                    "detail": {"S": enrichment.detail},
                    "date": {"S": enrichment.date or datetime.utcnow().strftime("%Y-%m-%d")}
                }
            }
            
            # Update the enrichments list
            response = self.table.update_item(
                Key={'PK': pk, 'SK': sk},
                UpdateExpression="SET enrichments = list_append(if_not_exists(enrichments, :empty_list), :new_enrichment), lastUpdated = :lastUpdated",
                ExpressionAttributeValues={
                    ':new_enrichment': [enrichment_data['M']],
                    ':empty_list': [],
                    ':lastUpdated': datetime.utcnow().isoformat() + "Z"
                },
                ReturnValues="ALL_NEW"
            )
            
            return response['Attributes']
            
        except ClientError as e:
            logger.error(f"Error adding enrichment: {e}")
            raise
    
    def increment_interaction_count(self, business_id: str, user_id: str) -> Dict[str, Any]:
        """Increment the interaction count for a user."""
        try:
            pk = f"symentic_{business_id.lower()}"
            sk = f"USER#{user_id}"
            
            now = datetime.utcnow().isoformat() + "Z"
            
            response = self.table.update_item(
                Key={'PK': pk, 'SK': sk},
                UpdateExpression="SET interactionCount = if_not_exists(interactionCount, :zero) + :one, " +
                               "interactions = if_not_exists(interactions, :zero) + :one, " +
                               "lastInteraction = :now, lastUpdated = :now",
                ExpressionAttributeValues={
                    ':zero': 0,
                    ':one': 1,
                    ':now': now
                },
                ReturnValues="ALL_NEW"
            )
            
            return response['Attributes']
            
        except ClientError as e:
            logger.error(f"Error incrementing interaction count: {e}")
            raise
    
    def search_enrichments_by_agent(self, business_id: str, agent_name: str) -> List[Dict[str, Any]]:
        """Search all users for enrichments from a specific agent."""
        try:
            pk = f"symentic_{business_id.lower()}"
            
            # Query all users in the business
            response = self.table.query(
                KeyConditionExpression=Key('PK').eq(pk) & Key('SK').begins_with('USER#')
            )
            
            # Filter users with enrichments from the specified agent
            users_with_agent = []
            for item in response.get('Items', []):
                enrichments = item.get('enrichments', [])
                agent_enrichments = [e for e in enrichments if e.get('agent') == agent_name]
                if agent_enrichments:
                    users_with_agent.append({
                        'user': item,
                        'agent_enrichments': agent_enrichments
                    })
            
            return users_with_agent
            
        except ClientError as e:
            logger.error(f"Error searching enrichments by agent: {e}")
            raise
    
    def get_recent_interactions(self, business_id: str, days: int = 7) -> List[Dict[str, Any]]:
        """Get users with recent interactions within specified days."""
        try:
            from datetime import timedelta
            
            pk = f"symentic_{business_id.lower()}"
            cutoff_date = (datetime.utcnow() - timedelta(days=days)).isoformat() + "Z"
            
            response = self.table.query(
                KeyConditionExpression=Key('PK').eq(pk) & Key('SK').begins_with('USER#'),
                FilterExpression=Attr('lastInteraction').gt(cutoff_date)
            )
            
            return response.get('Items', [])
            
        except ClientError as e:
            logger.error(f"Error getting recent interactions: {e}")
            raise