# ✈️ Wanderlust AI

> **Your Intelligent Conversational Travel Concierge** — Built on Google Agent Development Kit (ADK), Agent Platform, and Gemini.

![Wanderlust AI Demo](demo.gif)

---

## 🌟 Overview

**Wanderlust AI** is an agentic travel assistant designed to help travelers discover destinations, build personalized multi-day itineraries, estimate budget splits, and generate rich media content. Powered by Google Cloud's Agent Platform and Gemini models, Wanderlust AI seamlessly integrates cross-session memory, structured Firestore storage, AI media generation, sandboxed code execution, and an agent-first UI (A2UI).

---

## 🛠️ Implemented Tools & Google Cloud Services

The capabilities below reflect the exact tools, APIs, and Google Cloud services wired up in the agent codebase (`app/agent.py` and `agents-cli-manifest.yaml`):

### 🧠 Cross-Session Memory
- **Vertex AI Memory Bank**: Integrated via `PreloadMemoryTool` and automated session-saving callbacks (`add_session_to_memory`). Remembers user travel preferences, budget levels, dietary restrictions, preferred travel styles, and past trips across separate chat sessions.

### 🗄️ Database & Storage
- **Google Cloud Firestore Catalog**:
  - `search_destinations`: Queries destination catalog documents in Firestore.
  - `get_destination_details`: Retrieves full destination details by ID.
  - `save_destination`: Adds or updates destination documents.
  - `save_trip_itinerary`: Persists generated travel itineraries to Firestore.
- **Google Cloud Storage**: Stores generated media assets (images and videos) in a public bucket (`wanderlust-ai-media-<project>`) and returns public HTTPS URLs.

### 🎨 Media Generation
- **AI Postcard Image Generation** (`generate_destination_image`): Uses `gemini-3.1-flash-lite-image` (location: `global`) to create travel postcard visuals. Saves images as ADK artifacts (`tool_context.save_artifact`) and uploads them directly to Cloud Storage.
- **AI Preview Video Generation** (`generate_destination_video`): Uses `gemini-omni-flash-preview` (location: `global`) via Vertex AI Interactions API to generate short destination video clips. Saves videos as ADK artifacts and uploads bytes directly to Cloud Storage.

### 🧪 Code Execution & Math
- **Agent Platform Code Sandbox**: Uses `AgentEngineSandboxCodeExecutor` to safely execute Python code for calculating trip budget breakdowns, currency splits among travel companions, and expense estimates.

### 🪟 Agent-First UI (A2UI)
- **A2UI Card & Component Rendering**: Emits rich interactive A2UI cards, columns, rows, text hierarchy, images, and video elements via `a2ui` catalog manager and `after_model_callback`.

### 🌐 Live External APIs & Utilities
- **Currency Exchange** (`get_exchange_rate`): Real-time currency conversions via Frankfurter API.
- **Public Holidays** (`get_public_holidays`): Upcoming national holidays lookups via Nager.Date API.
- **Weather & Time** (`get_weather`, `get_current_time`): Current weather conditions and timezone calculations.

---

## 📌 Feature Roadmap & Status

| Feature | Status | Description |
|---|---|---|
| Cross-Session Memory | ✅ Implemented | Vertex AI Memory Bank integration |
| Firestore Catalog | ✅ Implemented | Destination & itinerary storage |
| Cloud Storage | ✅ Implemented | Public GCS media asset hosting |
| Postcard Image Gen | ✅ Implemented | Gemini Image generation |
| Destination Video Gen | ✅ Implemented | Gemini Omni Flash video generation |
| Sandboxed Code Executor | ✅ Implemented | Python budget/currency math calculations |
| A2UI Card Rendering | ✅ Implemented | Rich card UI responses |
| Live Currency & Weather | ✅ Implemented | Live external API integrations |
| Google Maps API Integration | ⏳ *Planned, not yet implemented* | Interactive venue & route mapping |

---

## 💻 Local Setup & Running Instructions

### Prerequisites
- Python 3.11+
- Node.js 18+ (for frontend)
- Google Cloud SDK (`gcloud`) authenticated with a billing-enabled GCP project:
  ```bash
  gcloud auth login
  gcloud auth application-default login
  ```

### 1. Run Agent Locally (Playground)
Navigate to the project directory, install dependencies, and launch the ADK playground:

```bash
cd wanderlust-ai

# Set your GCP Project and Region
export GOOGLE_CLOUD_PROJECT="<your-gcp-project-id>"
export GOOGLE_CLOUD_LOCATION="us-east1"

# Install dependencies using agents-cli
agents-cli install

# Launch the local development playground
agents-cli playground
```

### 2. Run Chat Frontend Locally
To launch the FastAPI proxy and chat interface locally:

```bash
cd wanderlust-ai/frontend

# Install dependencies
npm install

# Set environment variables pointing to your agent directory & deployed engine
export AGENT_DIRECTORY="../app"
export AGENT_ENGINE_RESOURCE_NAME="projects/<project-number>/locations/us-east1/reasoningEngines/<engine-id>"

# Start the development server
npm run dev
```

---

## 📄 License
Demonstration project built for the **Build with Gemini** workshop.
