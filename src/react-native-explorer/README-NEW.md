# React Native Explorer v2.0

A complete overhaul with **Next.js frontend** + **FastAPI agent server** + **MCP mobile control**.

## Architecture

```
┌─────────────────┐      WebSocket/HTTP      ┌──────────────────┐
│   Next.js UI    │ ◄──────────────────────► │   Agent Server   │
│   (Port 3000)   │                         │   (Port 5100)    │
└─────────────────┘                         └──────────────────┘
                                                     │
                                                     │ MCP (stdio)
                                                     ▼
                                            ┌──────────────────┐
                                            │  @mobilenext/    │
                                            │  mobile-mcp      │
                                            │  (Android)       │
                                            └──────────────────┘
```

## Quick Start

### 1. Install Agent Server Dependencies

```bash
cd agent-server
pip install -r requirements.txt
```

### 2. Install Frontend Dependencies

```bash
cd frontend
npm install
```

### 3. Start the Agent Server

```bash
cd agent-server
python -m src.main
```

The agent server will start on `http://127.0.0.1:5100`.

### 4. Start the Frontend (in a new terminal)

```bash
cd frontend
npm run dev
```

The UI will be available at `http://localhost:3000`.

## Configuration

Set environment variables:

```bash
# Optional: Override defaults
export AGENT_HOST=127.0.0.1
export AGENT_PORT=5100
export MAX_SCREENS=50
export OPENROUTER_API_KEY=your_key_here
```

## API Endpoints

### REST API

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/health` | GET | Health check |
| `/api/status` | GET | Current exploration status |
| `/api/exploration/start` | POST | Start exploration |
| `/api/exploration/pause` | POST | Pause exploration |
| `/api/exploration/resume` | POST | Resume exploration |
| `/api/exploration/stop` | POST | Stop exploration |
| `/api/screens` | GET | List all screens |
| `/api/screens/{id}` | GET | Get screen details |
| `/api/graph` | GET | Get navigation graph |
| `/api/stories` | GET | List stories |
| `/api/stories` | POST | Create story |

### WebSocket

Connect to `ws://127.0.0.1:5100/ws` for real-time updates:

- `state_change` - Exploration state changed
- `new_screen` - New screen discovered
- `action` - Action executed
- `exploration_complete` - Exploration finished

## Project Structure

```
react-native-explorer/
├── agent-server/          # FastAPI agent server
│   ├── src/
│   │   └── main.py       # FastAPI app
│   ├── core/
│   │   ├── config.py     # Configuration
│   │   ├── database.py   # SQLite models
│   │   └── explorer.py   # Exploration engine
│   ├── mcp_client/
│   │   └── client.py     # MCP client
│   └── requirements.txt
├── frontend/              # Next.js frontend
│   ├── src/
│   │   ├── app/          # Next.js app router
│   │   ├── components/   # React components
│   │   ├── lib/          # API client
│   │   └── types/        # TypeScript types
│   ├── package.json
│   └── tailwind.config.js
└── storage/              # Data storage
    ├── agent.db          # SQLite database
    └── screenshots/      # Screen captures
```

## Features

### v2.0 Improvements

1. **Clean Separation**: UI and agent are completely separate processes
2. **Modern Frontend**: React + TypeScript + Tailwind + D3
3. **Real-time Updates**: WebSocket for live exploration updates
4. **Better State Management**: Clear exploration state machine
5. **Proper API**: RESTful endpoints with typed responses
6. **Extensible**: Easy to add new exploration strategies

### UI Views

- **Graph**: Interactive D3 visualization of screen navigation
- **Gallery**: Grid view of all captured screens
- **Stories**: Create and manage user journey stories

## Troubleshooting

### Agent won't connect to MCP

Make sure you have Node.js installed and `npx` is available:

```bash
npx --version
```

### Frontend can't connect to agent

Check that the agent server is running and CORS is enabled:

```bash
curl http://127.0.0.1:5100/api/health
```

### Database errors

Delete the database to reset:

```bash
rm storage/agent.db
```
