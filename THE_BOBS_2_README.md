# The Bobs 2.0 - Modern Process Modeling Application

A robust AI-powered business process modeling application built with Vue.js, FastAPI, and bpmn-js.

## 🏗️ Architecture

### Frontend (Vue.js + TypeScript)
- **Framework**: Vue 3 with TypeScript
- **State Management**: Pinia
- **BPMN Visualization**: bpmn-js (official open-source BPMN viewer)
- **HTTP Client**: Axios
- **Build Tool**: Vite

### Backend (FastAPI + Python)
- **Framework**: FastAPI
- **AI Integration**: Marvin scripts for process generation
- **Session Management**: In-memory storage (Redis recommended for production)
- **Process Validation**: Core validation modules
- **CORS**: Configured for development

## 🚀 Getting Started

### Prerequisites
- Python 3.8+
- Node.js 16+
- uv (Python package manager)

### Installation

1. **Clone and navigate to the project**:
   ```bash
   git clone <repository-url>
   cd AgenticBobs
   ```

2. **Install Python dependencies**:
   ```bash
   uv sync
   ```

3. **Install Node.js dependencies**:
   ```bash
   cd thebobs
   npm install
   cd ..
   ```

### Running the Application

#### Option 1: Using the start script (Recommended)
```bash
./start.sh
```

This will start both servers:
- Frontend: http://localhost:5173
- Backend: http://localhost:8000
- API Documentation: http://localhost:8000/docs

#### Option 2: Manual startup

**Start the backend**:
```bash
cd backend
python dev_server.py
```

**Start the frontend** (in a new terminal):
```bash
cd thebobs
npm run dev
```

## 📁 Project Structure

```
AgenticBobs/
├── backend/                    # FastAPI backend
│   ├── main.py                # Main FastAPI application
│   ├── dev_server.py          # Development server script
│   └── requirements.txt       # Python dependencies
├── thebobs/                   # Vue.js frontend
│   ├── src/
│   │   ├── components/
│   │   │   ├── BpmnViewer.vue # BPMN diagram viewer
│   │   │   └── ChatPanel.vue  # Chat interface
│   │   ├── stores/
│   │   │   └── chat.ts        # Pinia store for chat state
│   │   ├── App.vue            # Main application component
│   │   └── main.ts            # Application entry point
│   └── package.json
├── core/                      # Core process modeling modules
├── marvin_scripts/           # AI-powered process generation
├── start.sh                  # Development startup script
└── README.md
```

## 🎯 Features

### Chat Interface
- **Session Management**: Persistent conversation sessions
- **Real-time Communication**: WebSocket-like experience with HTTP
- **Message History**: Full conversation tracking
- **Refinement Questions**: AI-generated follow-up questions

### BPMN Visualization
- **Interactive Viewer**: Powered by bpmn-js
- **Auto-fit Viewport**: Automatic diagram scaling
- **Real-time Updates**: Live diagram updates from chat
- **Export Functionality**: Download generated BPMN XML

### Process Generation
- **Multi-format Support**: BPMN, DMN, CMMN, ArchiMate detection
- **Intelligent Refinement**: Iterative process improvement
- **Validation**: Real-time BPMN validation with error reporting
- **Marvin Integration**: Seamless AI agent pipeline integration

## 🔧 Configuration

### Backend Configuration
The backend can be configured through environment variables:

```bash
# API Configuration
API_HOST=0.0.0.0
API_PORT=8000

# CORS Origins (for production)
CORS_ORIGINS=["http://localhost:5173"]

# Model Configuration (via marvin_scripts)
SMALL_MODEL=qwen3:8b
LARGE_MODEL=gpt-oss:20b
```

### Frontend Configuration
The frontend API base URL can be configured in `src/stores/chat.ts`:

```typescript
const API_BASE = 'http://localhost:8000/api'
```

## 🧪 API Endpoints

### Chat
- `POST /api/chat` - Send chat message and get process updates
- `GET /api/sessions/{session_id}/messages` - Get session message history
- `DELETE /api/sessions/{session_id}` - Delete a session

### Process Validation
- `POST /api/validate-bpmn` - Validate BPMN XML and get Mermaid diagram
- `GET /api/sample-bpmn` - Get sample BPMN for testing

### Health
- `GET /api/health` - Health check endpoint
- `GET /` - API root with service information

## 🔄 State Management (Pinia)

The frontend uses Pinia for state management with the following store structure:

```typescript
// Chat Store
interface ChatStore {
  // State
  messages: ChatMessage[]
  sessionId: string | null
  currentBpmn: string | null
  currentProcessType: string | null
  refinementQuestions: string[]
  isLoading: boolean
  error: string | null
  
  // Actions
  sendMessage(content: string): Promise<void>
  clearChat(): void
  validateBpmn(xml: string): Promise<ValidationResult>
  loadSampleBpmn(): Promise<void>
  deleteSession(): Promise<void>
}
```

## 🚧 Development

### Adding New Features

1. **Backend**: Add new endpoints in `backend/main.py`
2. **Frontend**: Create new components in `thebobs/src/components/`
3. **State**: Extend the Pinia store in `thebobs/src/stores/chat.ts`

### Running Tests
```bash
# Backend tests
cd backend
pytest

# Frontend tests  
cd thebobs
npm test
```

### Building for Production
```bash
# Frontend build
cd thebobs
npm run build

# Backend deployment
cd backend
uvicorn main:app --host 0.0.0.0 --port 8000
```

## 🔍 Troubleshooting

### Common Issues

1. **CORS Errors**: Ensure the backend CORS middleware includes your frontend URL
2. **Model Loading**: Verify marvin scripts and model configurations are correct
3. **BPMN Rendering**: Check browser console for bpmn-js errors
4. **Session Management**: Clear browser storage if experiencing session issues

### Debug Mode
Start the backend with debug logging:
```bash
cd backend
uvicorn main:app --log-level debug --reload
```

## 📚 Dependencies

### Key Frontend Dependencies
- `vue`: 3.5.18
- `pinia`: 2.2.8
- `bpmn-js`: 18.6.3
- `axios`: 1.7.9
- `typescript`: 5.8.3

### Key Backend Dependencies
- `fastapi`: 0.115.6
- `uvicorn`: 0.33.0
- `marvin`: (AI integration)
- `pydantic`: 2.10.4

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License.
