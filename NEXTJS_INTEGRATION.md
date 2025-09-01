# Next.js Integration Guide

This document explains how to integrate a Next.js application with the Flask RAG API.

## API Endpoints for Next.js

All external API endpoints require two headers:
- `X-API-Key`: API key for authentication (currently a placeholder)
- `X-User-ID`: The user's MongoDB ID

### 1. Chat with the RAG System

**Endpoint**: `POST /api/external/chat`

Send a message to the RAG system and receive a response.

**Request Body**:
```json
{
  "message": "What is my latest soil moisture status?",
  "session_id": "optional-session-id"  // If not provided, a new session will be created
}
```

**Response**:
```json
{
  "success": true,
  "response": "Based on your latest soil moisture data...",
  "session_id": "session-id",
  "timestamp": "2023-01-01T00:00:00.000Z"
}
```

### 2. Get User Data

**Endpoint**: `GET /api/external/user-data`

Retrieve all user-related data for context.

**Response**:
```json
{
  "user": { ... },
  "locations": [ ... ],
  "soil_moisture": [ ... ],
  "weather": [ ... ],
  "vegetation": [ ... ]
}
```

### 3. Get Chat History

**Endpoint**: `GET /api/external/chat/history?session_id=optional-session-id`

Retrieve chat history for a specific session or the latest session.

**Response**:
```json
{
  "success": true,
  "chat_history": [ ... ],
  "session_id": "session-id"
}
```

### 4. Get Chat Sessions

**Endpoint**: `GET /api/external/chat/sessions`

Retrieve all chat sessions for the user.

**Response**:
```json
{
  "success": true,
  "chat_sessions": [ ... ]
}
```

### 5. Create New Chat Session

**Endpoint**: `POST /api/external/chat/session/new`

Create a new chat session.

**Response**:
```json
{
  "success": true,
  "session_id": "new-session-id"
}
```

### 6. Delete Chat History

**Endpoint**: `POST /api/external/chat/delete`

Delete all chat history for the user.

**Response**:
```json
{
  "success": true,
  "message": "Chat history deleted successfully.",
  "session_id": "new-session-id"
}
```

## Example Usage in Next.js

```javascript
// Example function to send a message to the RAG system
async function sendMessage(message, userId) {
  const response = await fetch('http://localhost:5000/api/external/chat', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-API-Key': 'your-api-key',  // Placeholder for now
      'X-User-ID': userId
    },
    body: JSON.stringify({ message })
  });
  
  const data = await response.json();
  return data;
}

// Example function to get user data
async function getUserData(userId) {
  const response = await fetch('http://localhost:5000/api/external/user-data', {
    headers: {
      'X-API-Key': 'your-api-key',  // Placeholder for now
      'X-User-ID': userId
    }
  });
  
  const data = await response.json();
  return data;
}
```

## Authentication Notes

Currently, the API uses a simple header-based authentication system. In production, you should implement a more robust authentication system using JWT tokens or OAuth.

The `X-API-Key` header is currently not validated but should be implemented in production. The `X-User-ID` header is used to identify the user and must be a valid MongoDB user ID.