# MCP (Model Context Protocol) Servers

This directory contains MCP servers that provide tools for AI assistants to interact with external services.

## Overview

MCP servers expose functionality as tools that AI assistants can call. Each tool must return human-readable strings and handle errors gracefully.

## Server Structure

### Basic Tool Definition
```python
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("server-name")

@mcp.tool()
async def tool_name(param1: str, param2: Optional[int] = None) -> str:
    """Tool description.
    
    Args:
        param1: Description of parameter 1
        param2: Description of parameter 2 (optional)
        
    Returns:
        Description of what the tool returns
    """
    try:
        # Implementation
        return "formatted result"
    except Exception as e:
        return f"Error: {str(e)}"

if __name__ == "__main__":
    mcp.run(transport='stdio')
```

## Requirements

### 1. **Function Signature**
- **Must be `async`**: All MCP tools must be asynchronous functions
- **Must return `str`**: Tools must return human-readable strings, not JSON or objects
- **Type annotations**: All parameters must have proper type hints

### 2. **Decorator**
- **`@mcp.tool()`**: Required decorator to register the function as an MCP tool

### 3. **Documentation**
- **Comprehensive docstrings**: Include Args and Returns sections
- **Clear descriptions**: Explain what the tool does and what it returns

### 4. **Error Handling**
- **Try-catch blocks**: Wrap all implementations in exception handling
- **User-friendly errors**: Return descriptive error messages, not stack traces

## Best Practices

### 1. **Type Annotations**
```python
from typing import Any, Dict, List, Optional, Union

# Good examples:
async def get_data(user_id: str, limit: Optional[int] = None) -> str:
async def create_item(name: str, tags: List[str], metadata: Dict[str, Any]) -> str:
```

### 2. **Integration Pattern**
- **Thin wrapper approach**: Keep MCP tools as thin wrappers around business logic
- **Separation of concerns**: Use integration layers for complex operations
- **String formatting**: Always return formatted strings for human consumption

### 3. **File Organization**
```
tools/mcp-servers/
├── service-name/
│   ├── tools.py          # MCP tool definitions
│   ├── integration.py    # Business logic integration
│   └── README.md         # Service-specific documentation
```

## Precautions

### 1. **Security**
- **Environment variables**: Store sensitive data (API keys, tokens) in environment variables
- **Input validation**: Validate all parameters before processing
- **Rate limiting**: Implement rate limiting for external API calls

### 2. **Error Handling**
- **Graceful degradation**: Handle API failures gracefully
- **Timeout handling**: Set appropriate timeouts for external requests
- **Logging**: Log errors for debugging but return user-friendly messages

### 3. **Performance**
- **Async operations**: Use async/await for I/O operations
- **Connection pooling**: Reuse connections where possible
- **Caching**: Implement caching for frequently accessed data

### 4. **Data Formatting**
- **Human-readable**: Always return strings formatted for human consumption
- **Consistent format**: Use consistent formatting across all tools
- **No raw JSON**: Don't return raw JSON or complex objects

## Example: Notion Integration

```python
# tools.py - MCP layer
@mcp.tool()
async def get_users() -> str:
    """Get all users from Notion."""
    try:
        from integration import get_notion_users
        return await get_notion_users()
    except Exception as e:
        return f"Error fetching users: {str(e)}"

# integration.py - Business logic layer
async def get_notion_users() -> str:
    """Get and format Notion users."""
    users = get_all_users()  # Your existing function
    return format_users_for_mcp(users)
```

## Running Servers

```bash
# Run a server
python tools/mcp-servers/service-name/tools.py

# Server will start and listen on stdio for MCP protocol messages
```

## Testing

- Test each tool individually
- Verify error handling with invalid inputs
- Ensure all tools return properly formatted strings
- Test integration with actual external services

## Common Issues

1. **Import errors**: Ensure proper path setup for importing business logic
2. **Type errors**: Use proper type annotations and handle Optional types
3. **Async issues**: Make sure all I/O operations are properly awaited
4. **String formatting**: Always return strings, not objects or JSON
