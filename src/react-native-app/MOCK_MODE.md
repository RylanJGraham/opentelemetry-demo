# React Native App - Mock Mode

Run the app **without the backend Docker infrastructure** using filler/mock data!

## Quick Start (No Backend Required)

```bash
cd src/react-native-app

# Install dependencies
npm install

# Start the app (mock mode is enabled by default)
npm run android
# or
npm run ios
```

## What's Included

The mock mode provides:

- ✅ **8 Fake Products** with images, prices, descriptions
- ✅ **Working Cart** - add, remove, view items
- ✅ **Checkout Flow** - place orders (mocked)
- ✅ **Currency Support** - USD, EUR, GBP, JPY
- ✅ **Shipping Calculation** - mocked costs
- ✅ **Product Recommendations** - random suggestions
- ✅ **Ads** - placeholder advertisements

## Mock Data

### Products
| Product | Price | Category |
|---------|-------|----------|
| 👨‍🚀 Astronaut Figurine | $25.99 | Figurines |
| 🚀 Mars Rover Model | $45.00 | Models |
| 🔭 Telescope | $199.00 | Equipment |
| ⭐ Star Map Poster | $15.99 | Posters |
| 🧱 LEGO ISS Set | $79.99 | Toys |
| ☄️ Meteorite Fragment | $120.00 | Collectibles |
| 👕 NASA Hoodie | $55.00 | Clothing |
| 🪐 Planet Lamp | $35.99 | Home |

## Toggle Mock Mode

Edit `.env`:

```env
# Use mock data (no backend needed)
EXPO_PUBLIC_USE_MOCK_API=true

# OR use real backend
EXPO_PUBLIC_USE_MOCK_API=false
EXPO_PUBLIC_FRONTEND_PROXY=http://your-backend:8080
```

## Backend Mode (Optional)

If you want to use the real backend:

1. Start the OpenTelemetry Demo:
   ```bash
   cd ../..
   make start
   ```

2. Update `.env`:
   ```env
   EXPO_PUBLIC_USE_MOCK_API=false
   ```

3. Restart the app

## For Explorer Testing

The mock mode is perfect for testing the React Native Explorer because:

- App loads instantly (no backend latency)
- Consistent data for repeatable tests
- Works offline
- No Docker overhead
- AI exploration can tap through all screens

Start explorer:
```bash
cd ../react-native-explorer/agent-server
python -m src.main
```
