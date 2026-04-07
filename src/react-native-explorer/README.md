# React Native Explorer Agent v2.0

An intelligent, AI-powered tool for autonomously exploring React Native applications and generating E2E test scenarios.

## 🚀 Features

### Smart Exploration
- **Multi-Level Caching**: Uses perceptual hashing to minimize AI API calls
  - Level 1: Exact content hash match (instant)
  - Level 2: Perceptual hash match (similar appearance)
  - Level 3: Structure hash match (same layout)
  - Level 4: AI vision analysis (only for truly new screens)
  
- **Intelligent Navigation**: DFS-based exploration with priority scoring
- **Screen Clustering**: Auto-groups similar screens by type
- **Cost Tracking**: Monitors AI API usage and estimates costs

### Comprehensive App Mapping
- **Visual Graph**: D3.js-powered interactive navigation map
- **Screen Gallery**: Browse all discovered screens with screenshots
- **Element Detection**: Captures interactive elements with coordinates
- **Transition Tracking**: Maps all navigation paths

### E2E Test Generation
- **Story Builder**: Visual drag-and-drop test scenario creator
- **Multiple Export Formats**:
  - Detox (React Native)
  - Maestro (Modern mobile testing)
  - Appium (Cross-platform)
  - Cypress (Web)
  - Playwright (Web)

### Web UI Dashboard
- Real-time exploration status
- Screen gallery with search/filter
- Interactive app map
- Story management
- Export functionality

## 📁 Project Structure

```
agent/
├── __init__.py          # Package exports
├── __main__.py          # CLI entry point
├── explorer.py          # Main exploration orchestrator
├── graph.py             # SQLite database & graph operations
├── vision.py            # OpenRouter/Gemini AI integration
├── strategy.py          # Exploration decision engine
├── server.py            # HTTP API & WebSocket server
├── mcp_client.py        # Mobile MCP client
├── exporters.py         # E2E test format exporters
└── utils.py             # Utilities, caching, hashing

ui/
└── index.html           # Vue.js-based web interface

storage/
├── screenshots/         # Captured screen images
├── cache/              # Perceptual hash cache
├── stories/            # Exported stories
├── graph.db            # SQLite database
└── exploration_state.json
```

## 🔧 Installation

```bash
# Create virtual environment
python -m venv venv

# Activate
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows

# Install dependencies
pip install -r requirements.txt

# Set API key
export OPENROUTER_API_KEY="your-key-here"  # Linux/Mac
set OPENROUTER_API_KEY=your-key-here       # Windows
```

## 🎮 Usage

### Start Exploration
```bash
python -m agent
```

### UI-Only Mode (view results without exploring)
```bash
python -m agent --ui-only
```

### Resume Previous Exploration
```bash
python -m agent --resume
```

### Custom Configuration
```bash
python -m agent --config custom.yaml --max-screens 100
```

### Clear All Data
```bash
python -m agent --clear
```

## 🌐 Web UI

The web interface is available at `http://localhost:3000` with these sections:

### Dashboard
- Real-time exploration stats
- Cost tracking
- Recent activity feed

### App Map
- Interactive D3.js visualization
- Click nodes to view screen details
- Drag to rearrange
- Shows navigation flows

### Gallery
- Grid view of all screens
- Filter by type (list, form, auth, etc.)
- Search by name/description
- Click to view details

### Stories
- List of E2E test scenarios
- Create, edit, delete stories
- Auto-generate recommended stories
- Export to multiple formats

### Story Builder
- Drag screens from left panel
- Build step-by-step scenarios
- Set name, description, priority
- Save and export

## 📊 Data Model

### Screen
```typescript
{
  id: string;
  name: string;
  screen_type: string;
  description: string;
  screenshot_path: string;
  phash: string;           // Perceptual hash
  content_hash: string;    // SHA-256
  structure_hash: string;  // Layout fingerprint
  element_count: number;
  cluster_id: string;
  fully_explored: boolean;
  first_seen: number;
  last_seen: number;
  visit_count: number;
}
```

### Element
```typescript
{
  id: string;
  screen_id: string;
  element_type: string;    // button, input, etc.
  label: string;
  x, y: number;            // Coordinates
  width, height: number;
  text_content: string;
  accessibility_id: string;
  interacted: boolean;
  confidence: number;
}
```

### Story
```typescript
{
  id: string;
  name: string;
  description: string;
  priority: "high" | "medium" | "low";
  tags: string[];
  steps: StoryStep[];
  created_at: number;
  updated_at: number;
}
```

### StoryStep
```typescript
{
  id: number;
  step_number: number;
  action_type: string;     // tap, type, navigate, etc.
  screen_id: string;
  element_id: string;
  coordinates: [x, y];
  data: object;
  assertion: string;
}
```

## 🔌 API Endpoints

### Graph
- `GET /api/graph` - Full graph data
- `GET /api/graph/stats` - Statistics

### Screens
- `GET /api/screens` - List all screens
- `GET /api/screens/:id` - Screen details
- `GET /api/screens/:id/path/:target` - Shortest path
- `GET /api/screens/search?q=query` - Search

### Gallery
- `GET /api/gallery` - Gallery data
- `GET /api/gallery/clusters` - Clustered view
- `GET /api/gallery/by-type/:type` - Filter by type

### Stories
- `GET /api/stories` - List stories
- `POST /api/stories` - Create story
- `GET /api/stories/:id` - Get story
- `PUT /api/stories/:id` - Update story
- `DELETE /api/stories/:id` - Delete story
- `POST /api/stories/:id/steps` - Add step
- `POST /api/stories/:id/export/:format` - Export

### Exports
- `GET /api/export/detox` - Detox tests
- `GET /api/export/maestro` - Maestro flows
- `GET /api/export/appium` - Appium tests
- `GET /api/export/full` - Complete data
- `GET /api/export/zip` - ZIP archive

### Agent Control
- `POST /api/agent/start` - Start exploration
- `POST /api/agent/pause` - Pause
- `POST /api/agent/stop` - Stop
- `GET /api/status` - Current status
- `WS /ws/live` - WebSocket for real-time updates

## 🧪 Export Formats

### Detox
```javascript
describe('User Flow', () => {
  it('should complete checkout', async () => {
    await element(by.id('cart')).tap();
    await element(by.id('checkout')).tap();
    await expect(element(by.id('success'))).toBeVisible();
  });
});
```

### Maestro
```yaml
appId: ${APP_ID}
---
- tapOn:
    id: "cart"
- tapOn:
    id: "checkout"
- assertVisible:
    id: "success"
```

### Appium
```python
def test_checkout(self):
    self.driver.find_element(By.ID, 'cart').click()
    self.driver.find_element(By.ID, 'checkout').click()
    WebDriverWait(self.driver, 10).until(
        EC.visibility_of_element_located((By.ID, 'success'))
    )
```

## ⚙️ Configuration

```yaml
# config.yaml
app:
  name: "My React Native App"
  platform: "android"

exploration:
  max_screens: 50
  max_actions_per_screen: 15
  action_delay_ms: 1500
  enable_clustering: true

vision:
  model: "google/gemini-2.0-flash-001"
  api_key_env: "OPENROUTER_API_KEY"
  max_tokens: 2048

storage:
  screenshots_dir: "./storage/screenshots"
  database: "./storage/graph.db"
  cache_dir: "./storage/cache"

server:
  host: "127.0.0.1"
  port: 5100

ui:
  port: 3000
  auto_open: true
```

## 📈 Performance

With the multi-level caching system:
- **Exact matches**: ~100x faster than AI analysis
- **Similar screens**: Detected without AI calls
- **Cost reduction**: 60-80% fewer API calls vs naive approach
- **Speed**: Average 2-3 seconds per unique screen

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## 📄 License

MIT License - see LICENSE file for details.

## 🙏 Acknowledgments

- Built with [Vue.js](https://vuejs.org/), [D3.js](https://d3js.org/), and [aiohttp](https://docs.aiohttp.org/)
- AI powered by [OpenRouter](https://openrouter.ai/) and Google's Gemini
- Mobile automation via [Mobile MCP](https://github.com/mobile-next/mobile-mcp)
