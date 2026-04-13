# React Native Explorer

A mobile-first exploration and testing platform for React Native apps, consisting of two active projects:

---

## Projects

### 📱 [`src/react-native-app`](./src/react-native-app)

An Expo-based React Native mobile app — the primary subject of exploration and testing.

See [`src/react-native-app/README.md`](./src/react-native-app/README.md) for setup and run instructions.

---

### 🔭 [`src/react-native-explorer`](./src/react-native-explorer)

An AI-powered exploration agent with a Next.js dashboard. Connects to the mobile app via MCP, autonomously explores screens, and visualizes the app's navigation graph in real time.

See [`src/react-native-explorer/README.md`](./src/react-native-explorer/README.md) for setup and run instructions.

---

## Quick Start

1. Start the React Native app:
   ```bash
   cd src/react-native-app
   npm install
   npx expo start
   ```

2. Start the Explorer:
   ```bash
   cd src/react-native-explorer
   # See README for full setup (Python venv, Next.js frontend)
   ./start-v2.ps1
   ```
