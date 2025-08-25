# Symentic MCP Server

A Model Context Protocol (MCP) server for Symentic - the personal memory context layer for enterprises. This server provides seamless integration with AWS DynamoDB to manage user profiles, enrichments, and interaction tracking.

## Features

- **User Profile Management**: Create, read, update user profiles with comprehensive metadata
- **Enrichment System**: Track and manage enrichments from various agents
- **Interaction Tracking**: Monitor user interactions and engagement metrics
- **Search Capabilities**: Query users by type, recent interactions, and agent enrichments
- **Slack Integration**: Support for Slack profile data and metadata

## Prerequisites

- Python 3.8 or higher
- AWS CLI configured with appropriate credentials
- Access to the DynamoDB table `SymenticProfileEngrams-prod`
- AWS profile `leogao` configured with access to the table

## Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/symentic-mcp.git
cd symentic-mcp
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Set up environment variables:
```bash
cp .env.example .env
# Edit .env with your configuration
```

4. Verify AWS profile:
```bash
aws --profile leogao dynamodb describe-table --table-name SymenticProfileEngrams-prod --region us-east-1
```

## Configuration

### Environment Variables

Create a `.env` file with the following configuration:

```env
AWS_PROFILE=leogao
AWS_REGION=us-east-1
DYNAMODB_TABLE=SymenticProfileEngrams-prod
```

### Claude Desktop Integration

To use this MCP server with Claude Desktop, add the following to your `claude_desktop_config.json`:

**Windows** (`%AppData%\Claude\claude_desktop_config.json`):
```json
{
  "mcpServers": {
    "symentic": {
      "command": "python",
      "args": ["-m", "symentic_mcp.server"],
      "cwd": "C:\\Users\\leoga\\coding\\symentic-mcp",
      "env": {
        "AWS_PROFILE": "leogao",
        "AWS_REGION": "us-east-1",
        "DYNAMODB_TABLE": "SymenticProfileEngrams-prod"
      }
    }
  }
}
```

**macOS** (`~/Library/Application Support/Claude/claude_desktop_config.json`):
```json
{
  "mcpServers": {
    "symentic": {
      "command": "python",
      "args": ["-m", "symentic_mcp.server"],
      "cwd": "/path/to/symentic-mcp",
      "env": {
        "AWS_PROFILE": "leogao",
        "AWS_REGION": "us-east-1",
        "DYNAMODB_TABLE": "SymenticProfileEngrams-prod"
      }
    }
  }
}
```

## Usage

### Running the Server

For development and testing:
```bash
python -m symentic_mcp.server
```

### Available MCP Tools

The server provides the following tools:

1. **get_user_profile** - Retrieve a specific user profile
   - Parameters: `business_id`, `user_id`

2. **list_users** - List all users with optional filtering
   - Parameters: `business_id` (optional), `limit` (optional)

3. **search_users_by_type** - Find users by type (internal/external)
   - Parameters: `business_id`, `user_type`

4. **update_user_profile** - Update user attributes
   - Parameters: `business_id`, `user_id`, `updates`

5. **add_enrichment** - Add enrichment to user profile
   - Parameters: `business_id`, `user_id`, `agent`, `detail`, `date` (optional)

6. **get_user_enrichments** - Get all enrichments for a user
   - Parameters: `business_id`, `user_id`

7. **search_enrichments_by_agent** - Find enrichments by agent
   - Parameters: `business_id`, `agent_name`

8. **increment_interaction** - Update interaction count
   - Parameters: `business_id`, `user_id`

9. **get_recent_interactions** - Get recently active users
   - Parameters: `business_id`, `days` (optional)

### MCP Resources

The server also provides resources:

- `symentic://schema` - Table schema and structure information
- `symentic://stats` - Usage statistics and metrics

## DynamoDB Schema

The server works with the following DynamoDB structure:

- **Primary Key**: 
  - PK: `symentic_{businessId}` 
  - SK: `USER#{userId}`

- **Global Secondary Index (GSI1)**:
  - GSI1PK: `symentic_{businessId}`
  - GSI1SK: `TYPE#{userType}#USER#{userId}`

- **Key Attributes**:
  - User identification (businessId, userId, name, email)
  - Profile data (description, role, expertise, tags)
  - Enrichments (agent-generated insights)
  - Interaction metrics (count, last interaction)
  - Slack integration data

## Development

### Project Structure

```
symentic-mcp/
├── symentic_mcp/
│   ├── __init__.py
│   ├── server.py          # Main MCP server implementation
│   ├── dynamo_client.py   # DynamoDB operations
│   └── models.py          # Pydantic data models
├── requirements.txt
├── pyproject.toml
├── .env.example
└── README.md
```

### Testing

To test the server locally:

1. Run the server in stdio mode:
```bash
python -m symentic_mcp.server
```

2. Test with MCP client or Claude Desktop

## Troubleshooting

### AWS Credentials

If you encounter AWS credential issues:

1. Verify your AWS profile:
```bash
aws configure list --profile leogao
```

2. Test DynamoDB access:
```bash
aws --profile leogao dynamodb list-tables --region us-east-1
```

### Connection Issues

- Ensure the DynamoDB table exists and is accessible
- Check AWS region configuration matches your table location
- Verify IAM permissions for the AWS profile

## Security

- Never commit `.env` files with actual credentials
- Use AWS IAM roles with minimal required permissions
- Regularly rotate AWS access keys
- Monitor DynamoDB access logs

## License

Copyright (c) 2025 Symentic

## Support

For issues or questions, please contact the Symentic team or open an issue in the repository.
