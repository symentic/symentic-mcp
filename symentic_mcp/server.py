"""Symentic MCP Server - Main server implementation."""

import os
import sys
import json
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime

from dotenv import load_dotenv
from mcp.server import Server, NotificationOptions
from mcp.server.models import InitializationOptions
import mcp.server.stdio
from mcp.types import Tool, TextContent, Resource

from .dynamo_client import DynamoDBClient
from .models import UserProfileUpdate, EnrichmentInput

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize MCP server
server = Server("symentic-mcp")

# Initialize DynamoDB client
db_client: Optional[DynamoDBClient] = None


@server.list_tools()
async def list_tools() -> List[Tool]:
    """List all available tools for the MCP server."""
    return [
        Tool(
            name="get_user_profile",
            description="Retrieve a user profile by business ID and user ID",
            inputSchema={
                "type": "object",
                "properties": {
                    "business_id": {"type": "string", "description": "Business/workspace ID"},
                    "user_id": {"type": "string", "description": "User ID"}
                },
                "required": ["business_id", "user_id"]
            }
        ),
        Tool(
            name="list_users",
            description="List all users, optionally filtered by business ID",
            inputSchema={
                "type": "object",
                "properties": {
                    "business_id": {"type": "string", "description": "Optional business ID to filter by"},
                    "limit": {"type": "integer", "description": "Maximum number of users to return", "default": 100}
                }
            }
        ),
        Tool(
            name="search_users_by_type",
            description="Search users by type (internal or external)",
            inputSchema={
                "type": "object",
                "properties": {
                    "business_id": {"type": "string", "description": "Business/workspace ID"},
                    "user_type": {"type": "string", "enum": ["internal", "external"], "description": "User type"}
                },
                "required": ["business_id", "user_type"]
            }
        ),
        Tool(
            name="update_user_profile",
            description="Update user profile attributes",
            inputSchema={
                "type": "object",
                "properties": {
                    "business_id": {"type": "string", "description": "Business/workspace ID"},
                    "user_id": {"type": "string", "description": "User ID"},
                    "updates": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string"},
                            "description": {"type": "string"},
                            "role": {"type": "string"},
                            "tags": {"type": "array", "items": {"type": "string"}},
                            "expertise": {"type": "array", "items": {"type": "string"}}
                        }
                    }
                },
                "required": ["business_id", "user_id", "updates"]
            }
        ),
        Tool(
            name="add_enrichment",
            description="Add an enrichment to a user profile",
            inputSchema={
                "type": "object",
                "properties": {
                    "business_id": {"type": "string", "description": "Business/workspace ID"},
                    "user_id": {"type": "string", "description": "User ID"},
                    "agent": {"type": "string", "description": "Agent name that created the enrichment"},
                    "detail": {"type": "string", "description": "Enrichment detail/content"},
                    "date": {"type": "string", "description": "Optional date (YYYY-MM-DD), defaults to today"}
                },
                "required": ["business_id", "user_id", "agent", "detail"]
            }
        ),
        Tool(
            name="get_user_enrichments",
            description="Get all enrichments for a specific user",
            inputSchema={
                "type": "object",
                "properties": {
                    "business_id": {"type": "string", "description": "Business/workspace ID"},
                    "user_id": {"type": "string", "description": "User ID"}
                },
                "required": ["business_id", "user_id"]
            }
        ),
        Tool(
            name="search_enrichments_by_agent",
            description="Search for enrichments created by a specific agent",
            inputSchema={
                "type": "object",
                "properties": {
                    "business_id": {"type": "string", "description": "Business/workspace ID"},
                    "agent_name": {"type": "string", "description": "Name of the agent"}
                },
                "required": ["business_id", "agent_name"]
            }
        ),
        Tool(
            name="increment_interaction",
            description="Increment the interaction count for a user",
            inputSchema={
                "type": "object",
                "properties": {
                    "business_id": {"type": "string", "description": "Business/workspace ID"},
                    "user_id": {"type": "string", "description": "User ID"}
                },
                "required": ["business_id", "user_id"]
            }
        ),
        Tool(
            name="get_recent_interactions",
            description="Get users with recent interactions within specified days",
            inputSchema={
                "type": "object",
                "properties": {
                    "business_id": {"type": "string", "description": "Business/workspace ID"},
                    "days": {"type": "integer", "description": "Number of days to look back", "default": 7}
                },
                "required": ["business_id"]
            }
        )
    ]


@server.call_tool()
async def call_tool(name: str, arguments: Dict[str, Any]) -> List[TextContent]:
    """Handle tool calls from the MCP client."""
    global db_client
    
    if not db_client:
        return [TextContent(type="text", text="Error: Database client not initialized")]
    
    try:
        if name == "get_user_profile":
            result = db_client.get_user_profile(
                arguments["business_id"],
                arguments["user_id"]
            )
            if result:
                return [TextContent(type="text", text=json.dumps(result, indent=2, default=str))]
            else:
                return [TextContent(type="text", text="User not found")]
        
        elif name == "list_users":
            result = db_client.list_users(
                arguments.get("business_id"),
                arguments.get("limit", 100)
            )
            return [TextContent(type="text", text=json.dumps(result, indent=2, default=str))]
        
        elif name == "search_users_by_type":
            result = db_client.search_users_by_type(
                arguments["business_id"],
                arguments["user_type"]
            )
            return [TextContent(type="text", text=json.dumps(result, indent=2, default=str))]
        
        elif name == "update_user_profile":
            result = db_client.update_user_profile(
                arguments["business_id"],
                arguments["user_id"],
                arguments["updates"]
            )
            return [TextContent(type="text", text=json.dumps(result, indent=2, default=str))]
        
        elif name == "add_enrichment":
            enrichment = EnrichmentInput(
                agent=arguments["agent"],
                detail=arguments["detail"],
                date=arguments.get("date")
            )
            result = db_client.add_enrichment(
                arguments["business_id"],
                arguments["user_id"],
                enrichment
            )
            return [TextContent(type="text", text=json.dumps(result, indent=2, default=str))]
        
        elif name == "get_user_enrichments":
            user = db_client.get_user_profile(
                arguments["business_id"],
                arguments["user_id"]
            )
            if user:
                enrichments = user.get("enrichments", [])
                return [TextContent(type="text", text=json.dumps(enrichments, indent=2, default=str))]
            else:
                return [TextContent(type="text", text="User not found")]
        
        elif name == "search_enrichments_by_agent":
            result = db_client.search_enrichments_by_agent(
                arguments["business_id"],
                arguments["agent_name"]
            )
            return [TextContent(type="text", text=json.dumps(result, indent=2, default=str))]
        
        elif name == "increment_interaction":
            result = db_client.increment_interaction_count(
                arguments["business_id"],
                arguments["user_id"]
            )
            return [TextContent(type="text", text=json.dumps(result, indent=2, default=str))]
        
        elif name == "get_recent_interactions":
            result = db_client.get_recent_interactions(
                arguments["business_id"],
                arguments.get("days", 7)
            )
            return [TextContent(type="text", text=json.dumps(result, indent=2, default=str))]
        
        else:
            return [TextContent(type="text", text=f"Unknown tool: {name}")]
    
    except Exception as e:
        logger.error(f"Error executing tool {name}: {e}")
        return [TextContent(type="text", text=f"Error: {str(e)}")]


@server.list_resources()
async def list_resources() -> List[Resource]:
    """List available resources."""
    return [
        Resource(
            uri="symentic://schema",
            name="Table Schema",
            description="DynamoDB table schema and structure information",
            mimeType="application/json"
        ),
        Resource(
            uri="symentic://stats",
            name="Usage Statistics",
            description="Current usage statistics for the Symentic system",
            mimeType="application/json"
        )
    ]


@server.read_resource()
async def read_resource(uri: str) -> str:
    """Read a resource by URI."""
    if uri == "symentic://schema":
        schema = {
            "table_name": "SymenticProfileEngrams-prod",
            "primary_key": {
                "partition_key": "PK (format: symentic_businessId)",
                "sort_key": "SK (format: USER#userId)"
            },
            "global_secondary_index": {
                "GSI1": {
                    "partition_key": "GSI1PK",
                    "sort_key": "GSI1SK (format: TYPE#userType#USER#userId)"
                }
            },
            "attributes": {
                "businessId": "Business/workspace identifier",
                "userId": "User identifier",
                "userType": "internal or external",
                "name": "User's name",
                "email": "User's email address",
                "description": "User description",
                "role": "User's role",
                "enrichments": "Array of enrichment objects",
                "expertise": "Array of expertise tags",
                "tags": "Array of general tags",
                "interactionCount": "Number of interactions",
                "lastInteraction": "Timestamp of last interaction",
                "slackProfile": "Slack profile information",
                "consent": "User consent information"
            }
        }
        return json.dumps(schema, indent=2)
    
    elif uri == "symentic://stats":
        if db_client:
            try:
                # Get some basic statistics
                users = db_client.list_users(limit=1000)
                total_users = len(users)
                internal_users = sum(1 for u in users if u.get("userType") == "internal")
                external_users = sum(1 for u in users if u.get("userType") == "external")
                
                stats = {
                    "total_users": total_users,
                    "internal_users": internal_users,
                    "external_users": external_users,
                    "table_name": db_client.table_name,
                    "region": db_client.region,
                    "profile": db_client.aws_profile
                }
                return json.dumps(stats, indent=2)
            except Exception as e:
                return json.dumps({"error": str(e)})
        else:
            return json.dumps({"error": "Database client not initialized"})
    
    else:
        return json.dumps({"error": f"Unknown resource: {uri}"})


async def main():
    """Main entry point for the MCP server."""
    global db_client
    
    # Get configuration from environment
    table_name = os.getenv("DYNAMODB_TABLE", "SymenticProfileEngrams-prod")
    aws_profile = os.getenv("AWS_PROFILE", "leogao")
    aws_region = os.getenv("AWS_REGION", "us-east-1")
    
    logger.info(f"Starting Symentic MCP Server...")
    logger.info(f"Table: {table_name}")
    logger.info(f"Profile: {aws_profile}")
    logger.info(f"Region: {aws_region}")
    
    try:
        # Initialize DynamoDB client
        db_client = DynamoDBClient(
            table_name=table_name,
            aws_profile=aws_profile,
            region=aws_region
        )
        
        # Run the server  
        async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
            init_options = InitializationOptions(
                server_name="symentic-mcp",
                server_version="0.1.0",
                capabilities=server.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={},
                )
            )
            await server.run(read_stream, write_stream, init_options)
        
    except Exception as e:
        logger.error(f"Failed to start server: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())