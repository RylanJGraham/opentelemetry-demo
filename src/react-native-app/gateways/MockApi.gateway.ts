// Mock API Gateway - returns filler data for standalone testing
// No backend Docker required!

import {
  Product,
  Cart,
  CartItem,
  Money,
  Address,
} from "@/protos/demo";
import { IProductCart, IProductCheckout } from "@/types/Cart";

// Extended product catalog with 20+ diverse items
const MOCK_PRODUCTS: Product[] = [
  // Electronics
  {
    id: "1",
    name: "Astronaut Figurine",
    description: "A detailed figurine of an astronaut in a space suit. Perfect for your desk! Features LED helmet light and movable joints.",
    picture: "https://placehold.co/400x400/1e3a5f/white?text=👨‍🚀+Astronaut",
    priceUsd: { currencyCode: "USD", units: 25, nanos: 99 },
    categories: ["figurines", "collectibles"],
  },
  {
    id: "2",
    name: "Mars Rover Model",
    description: "Scale model of the Perseverance Mars rover. 1:50 scale with authentic NASA detailing. Includes display stand.",
    picture: "https://placehold.co/400x400/c1440e/white?text=🚀+Rover",
    priceUsd: { currencyCode: "USD", units: 45, nanos: 0 },
    categories: ["models", "collectibles"],
  },
  {
    id: "3",
    name: "Telescope",
    description: "High-quality refracting telescope for stargazing. 70mm aperture, 400mm focal length. Perfect for beginners!",
    picture: "https://placehold.co/400x400/0d1b2a/white?text=🔭+Telescope",
    priceUsd: { currencyCode: "USD", units: 199, nanos: 0 },
    categories: ["equipment", "electronics"],
  },
  {
    id: "4",
    name: "Star Map Poster",
    description: "Beautiful constellation map for your wall. Glows in the dark! 24x36 inches, printed on high-quality matte paper.",
    picture: "https://placehold.co/400x400/0b1026/white?text=⭐+Star+Map",
    priceUsd: { currencyCode: "USD", units: 15, nanos: 99 },
    categories: ["posters", "home"],
  },
  {
    id: "5",
    name: "Space Station LEGO Set",
    description: "Build your own ISS with this 864-piece LEGO set. Includes microfigures and detailed instruction booklet.",
    picture: "https://placehold.co/400x400/f4d03f/black?text=🧱+LEGO+ISS",
    priceUsd: { currencyCode: "USD", units: 79, nanos: 99 },
    categories: ["toys", "collectibles"],
  },
  {
    id: "6",
    name: "Meteorite Fragment",
    description: "Genuine meteorite fragment from the Campo del Cielo fall. Certificate of authenticity included. Makes a unique gift!",
    picture: "https://placehold.co/400x400/5a5a5a/white?text=☄️+Meteorite",
    priceUsd: { currencyCode: "USD", units: 120, nanos: 0 },
    categories: ["collectibles"],
  },
  {
    id: "7",
    name: "NASA Hoodie",
    description: "Comfortable hoodie with the classic NASA 'meatball' logo. 80% cotton, 20% polyester. Available in multiple sizes.",
    picture: "https://placehold.co/400x400/1a5490/white?text=👕+NASA+Hoodie",
    priceUsd: { currencyCode: "USD", units: 55, nanos: 0 },
    categories: ["clothing"],
  },
  {
    id: "8",
    name: "Planet Lamp",
    description: "3D printed lamps that look like planets. Remote controlled colors with 16 RGB settings. USB powered.",
    picture: "https://placehold.co/400x400/2d1b69/white?text=🪐+Planet+Lamp",
    priceUsd: { currencyCode: "USD", units: 35, nanos: 99 },
    categories: ["home", "electronics"],
  },
  // New products
  {
    id: "9",
    name: "Rocket Ship Night Light",
    description: "Adorable rocket ship night light with color-changing LEDs. Auto shut-off after 1 hour. Perfect for kids' rooms!",
    picture: "https://placehold.co/400x400/ff6b6b/white?text=🚀+Night+Light",
    priceUsd: { currencyCode: "USD", units: 22, nanos: 50 },
    categories: ["home", "kids"],
  },
  {
    id: "10",
    name: "Space Shuttle Drone",
    description: "Remote-controlled space shuttle drone with 720p camera. 15-minute flight time, 100m range. Ages 14+.",
    picture: "https://placehold.co/400x400/4a90d9/white?text=🛸+Drone",
    priceUsd: { currencyCode: "USD", units: 149, nanos: 99 },
    categories: ["electronics", "toys"],
  },
  {
    id: "11",
    name: "Alien Plush Toy",
    description: "Super soft alien plush toy. 12 inches tall. Green with big eyes. Great for kids and adults alike!",
    picture: "https://placehold.co/400x400/7cb342/white?text=👽+Plush",
    priceUsd: { currencyCode: "USD", units: 18, nanos: 99 },
    categories: ["toys", "kids"],
  },
  {
    id: "12",
    name: "Moon Phase Wall Clock",
    description: "Elegant wall clock that shows moon phases. Silent quartz movement. 12-inch diameter.",
    picture: "https://placehold.co/400x400/2c3e50/white?text=🌙+Clock",
    priceUsd: { currencyCode: "USD", units: 42, nanos: 0 },
    categories: ["home"],
  },
  {
    id: "13",
    name: "Astronaut Ice Cube Tray",
    description: "Make astronaut-shaped ice cubes! Food-grade silicone. Makes 6 astronaut shapes per tray.",
    picture: "https://placehold.co/400x400/81d4fa/black?text=🧊+Ice+Tray",
    priceUsd: { currencyCode: "USD", units: 12, nanos: 99 },
    categories: ["home", "kitchen"],
  },
  {
    id: "14",
    name: "Galaxy Projector",
    description: "Transform any room into a planetarium! Projects rotating galaxy with 360° coverage. Bluetooth speaker built-in.",
    picture: "https://placehold.co/400x400/9c27b0/white?text=✨+Projector",
    priceUsd: { currencyCode: "USD", units: 59, nanos: 99 },
    categories: ["electronics", "home"],
  },
  {
    id: "15",
    name: "SpaceX Starship Poster",
    description: "Limited edition SpaceX Starship poster. 18x24 inches. Printed on archival paper.",
    picture: "https://placehold.co/400x400/1a237e/white?text=🚀+Poster",
    priceUsd: { currencyCode: "USD", units: 24, nanos: 99 },
    categories: ["posters"],
  },
  {
    id: "16",
    name: "Constellation Bedding Set",
    description: "Queen-size bedding set with constellation pattern. Includes 1 duvet cover and 2 pillowcases. 100% cotton.",
    picture: "https://placehold.co/400x400/1e1e1e/white?text=🛏️+Bedding",
    priceUsd: { currencyCode: "USD", units: 89, nanos: 99 },
    categories: ["home"],
  },
  {
    id: "17",
    name: "Astronaut Phone Case",
    description: "Protective phone case with astronaut design. Shock-absorbing TPU. Compatible with iPhone and Samsung.",
    picture: "https://placehold.co/400x400/37474f/white?text=📱+Case",
    priceUsd: { currencyCode: "USD", units: 19, nanos: 99 },
    categories: ["accessories"],
  },
  {
    id: "18",
    name: "NASA Backpack",
    description: "Official NASA backpack with laptop compartment. Water-resistant. Multiple pockets for organization.",
    picture: "https://placehold.co/400x400/1565c0/white?text=🎒+Backpack",
    priceUsd: { currencyCode: "USD", units: 65, nanos: 0 },
    categories: ["accessories", "clothing"],
  },
  {
    id: "19",
    name: "Solar System Model Kit",
    description: "Build and paint your own solar system. Includes 9 planet models, paint set, and display stand.",
    picture: "https://placehold.co/400x400/ff9800/white?text=🌌+Model+Kit",
    priceUsd: { currencyCode: "USD", units: 32, nanos: 99 },
    categories: ["toys", "educational"],
  },
  {
    id: "20",
    name: "Zero Gravity Pen",
    description: "Pressurized ink pen that writes at any angle. The same technology used by astronauts! Refillable.",
    picture: "https://placehold.co/400x400/607d8b/white?text=✒️+Space+Pen",
    priceUsd: { currencyCode: "USD", units: 28, nanos: 0 },
    categories: ["accessories"],
  },
  {
    id: "21",
    name: "Rocket Launch Monitor",
    description: "Smart display showing upcoming rocket launches worldwide. WiFi connected with companion app.",
    picture: "https://placehold.co/400x400/e53935/white?text=📺+Monitor",
    priceUsd: { currencyCode: "USD", units: 129, nanos: 99 },
    categories: ["electronics"],
  },
  {
    id: "22",
    name: "Space Station Playset",
    description: "Interactive playset with astronaut figures and space station modules. Lights and sounds included.",
    picture: "https://placehold.co/400x400/5e35b1/white?text=🎮+Playset",
    priceUsd: { currencyCode: "USD", units: 75, nanos: 0 },
    categories: ["toys", "kids"],
  },
];

// Special deals (subset of products with discounts)
const DEAL_PRODUCTS = ["3", "8", "14", "10", "21"]; // Telescope, Planet Lamp, Galaxy Projector, Drone, Monitor

// In-memory cart storage
let mockCart: IProductCart = {
  userId: "mock-user",
  items: [],
};

// Order history
interface MockOrder {
  id: string;
  date: string;
  total: Money;
  items: { productId: string; quantity: number; product: Product }[];
  status: "Delivered" | "Shipped" | "Processing";
}

let mockOrders: MockOrder[] = [
  {
    id: "ORD-9912",
    date: "2026-03-15",
    total: { currencyCode: "USD", units: 124, nanos: 99 * 10000000 },
    items: [
      { productId: "1", quantity: 2, product: MOCK_PRODUCTS[0] },
      { productId: "4", quantity: 1, product: MOCK_PRODUCTS[3] },
      { productId: "13", quantity: 3, product: MOCK_PRODUCTS[12] },
    ],
    status: "Delivered",
  },
  {
    id: "ORD-9945",
    date: "2026-04-01",
    total: { currencyCode: "USD", units: 55, nanos: 0 },
    items: [
      { productId: "7", quantity: 1, product: MOCK_PRODUCTS[6] },
    ],
    status: "Shipped",
  },
  {
    id: "ORD-9988",
    date: "2026-04-05",
    total: { currencyCode: "USD", units: 210, nanos: 50 * 10000000 },
    items: [
      { productId: "3", quantity: 1, product: MOCK_PRODUCTS[2] },
      { productId: "9", quantity: 2, product: MOCK_PRODUCTS[8] },
    ],
    status: "Processing",
  },
];

// Generate price in different currencies
const getPrice = (product: Product, currencyCode: string): Money => {
  const basePrice = product.priceUsd?.units || 0;
  const baseNanos = product.priceUsd?.nanos || 0;
  
  const rates: Record<string, number> = {
    USD: 1,
    EUR: 0.85,
    GBP: 0.73,
    JPY: 110,
    CAD: 1.35,
    AUD: 1.52,
  };
  
  const rate = rates[currencyCode] || 1;
  const totalNanos = (basePrice * 1000000000 + baseNanos) * rate;
  
  return {
    currencyCode,
    units: Math.floor(totalNanos / 1000000000),
    nanos: Math.floor(totalNanos % 1000000000),
  };
};

const MockApiGateway = {
  async getCart(currencyCode: string): Promise<IProductCart> {
    // Convert prices to requested currency
    return {
      ...mockCart,
      currencyCode,
      items: mockCart.items.map((item) => ({
        ...item,
        price: getPrice(item.product!, currencyCode),
      })),
    };
  },

  async addCartItem({
    currencyCode,
    ...item
  }: CartItem & { currencyCode: string }): Promise<Cart> {
    const product = MOCK_PRODUCTS.find((p) => p.id === item.productId);
    if (!product) throw new Error("Product not found");

    const existingItem = mockCart.items.find(
      (i) => i.productId === item.productId
    );

    if (existingItem) {
      existingItem.quantity += item.quantity;
    } else {
      mockCart.items.push({
        productId: item.productId,
        quantity: item.quantity,
        product,
        price: getPrice(product, currencyCode),
      });
    }

    return this.getCart(currencyCode);
  },

  async updateCartItem(productId: string, quantity: number, currencyCode: string): Promise<IProductCart> {
    const item = mockCart.items.find((i) => i.productId === productId);
    if (!item) throw new Error("Item not found");

    if (quantity <= 0) {
      mockCart.items = mockCart.items.filter((i) => i.productId !== productId);
    } else {
      item.quantity = quantity;
    }

    return this.getCart(currencyCode);
  },

  async removeCartItem(productId: string, currencyCode: string): Promise<IProductCart> {
    mockCart.items = mockCart.items.filter((i) => i.productId !== productId);
    return this.getCart(currencyCode);
  },

  async emptyCart(): Promise<undefined> {
    mockCart.items = [];
    return undefined;
  },

  getSupportedCurrencyList(): Promise<string[]> {
    return Promise.resolve(["USD", "EUR", "GBP", "JPY", "CAD", "AUD"]);
  },

  getShippingCost(
    itemList: { productId: string; quantity: number }[],
    currencyCode: string,
    address: Address
  ): Promise<Money> {
    // Mock shipping cost calculation
    const totalItems = itemList.reduce((sum, i) => sum + i.quantity, 0);
    const baseCost = 5 + totalItems * 2;
    
    const rates: Record<string, number> = {
      USD: 1,
      EUR: 0.85,
      GBP: 0.73,
      JPY: 110,
      CAD: 1.35,
      AUD: 1.52,
    };
    
    const rate = rates[currencyCode] || 1;
    const cost = baseCost * rate;

    return Promise.resolve({
      currencyCode,
      units: Math.floor(cost),
      nanos: Math.floor((cost % 1) * 1000000000),
    });
  },

  placeOrder({
    currencyCode,
    ...order
  }: {
    userId: string;
    userCurrency: string;
    address: Address;
    email: string;
    creditCard: {
      creditCardNumber: string;
      creditCardCvv: number;
      creditCardExpirationYear: number;
      creditCardExpirationMonth: number;
    };
    currencyCode: string;
  }): Promise<IProductCheckout> {
    // Calculate total
    const total = mockCart.items.reduce((sum, item) => {
      const price = getPrice(item.product!, currencyCode);
      return sum + (price.units + price.nanos / 1000000000) * item.quantity;
    }, 5); // $5 shipping

    // Create order record
    const newOrder: MockOrder = {
      id: `ORD-${Math.floor(Math.random() * 10000)}`,
      date: new Date().toISOString().split("T")[0],
      total: { currencyCode, units: Math.floor(total), nanos: Math.floor((total % 1) * 1000000000) },
      items: [...mockCart.items],
      status: "Processing",
    };
    mockOrders.unshift(newOrder);

    // Clear cart
    mockCart.items = [];
    
    return Promise.resolve({
      orderId: newOrder.id,
      shippingTrackingId: `TRACK-${Math.random().toString(36).substr(2, 9).toUpperCase()}`,
      shippingCost: { currencyCode, units: 5, nanos: 0 },
      totalPaid: newOrder.total,
    });
  },

  listProducts(currencyCode: string): Promise<Product[]> {
    // Return products with prices in requested currency
    return Promise.resolve(
      MOCK_PRODUCTS.map((p) => ({
        ...p,
        priceUsd: getPrice(p, currencyCode),
      }))
    );
  },

  getProduct(productId: string, currencyCode: string): Promise<Product> {
    const product = MOCK_PRODUCTS.find((p) => p.id === productId);
    if (!product) throw new Error("Product not found");
    
    return Promise.resolve({
      ...product,
      priceUsd: getPrice(product, currencyCode),
    });
  },

  async listRecommendations(
    productIds: string[],
    currencyCode: string
  ): Promise<Product[]> {
    // Return 3 random products not in the input list
    const otherProducts = MOCK_PRODUCTS.filter(
      (p) => !productIds.includes(p.id)
    );
    const shuffled = otherProducts.sort(() => 0.5 - Math.random());
    const recommendations = shuffled.slice(0, 3);
    
    return Promise.resolve(
      recommendations.map((p) => ({
        ...p,
        priceUsd: getPrice(p, currencyCode),
      }))
    );
  },

  listAds(): Promise<{
    redirectUrl: string;
    text: string;
    image: string;
  }[]> {
    // Mock ads
    return Promise.resolve([
      {
        redirectUrl: "https://example.com/ad1",
        text: "🚀 Space Week Sale! 20% off all telescopes!",
        image: "/images/ads/ad1.jpg",
      },
      {
        redirectUrl: "https://example.com/ad2",
        text: "👨‍🚀 New NASA Collection Just Dropped!",
        image: "/images/ads/ad2.jpg",
      },
      {
        redirectUrl: "https://example.com/ad3",
        text: "🌌 Free shipping on orders over $50!",
        image: "/images/ads/ad3.jpg",
      },
    ]);
  },

  // Get products by category
  getProductsByCategory(category: string, currencyCode: string): Promise<Product[]> {
    const filtered = MOCK_PRODUCTS.filter((p) => 
      p.categories?.includes(category)
    );
    return Promise.resolve(
      filtered.map((p) => ({
        ...p,
        priceUsd: getPrice(p, currencyCode),
      }))
    );
  },

  // Get all categories
  getCategories(): Promise<string[]> {
    const categories = new Set<string>();
    MOCK_PRODUCTS.forEach((p) => {
      p.categories?.forEach((c) => categories.add(c));
    });
    return Promise.resolve(Array.from(categories).sort());
  },

  // Get deal products
  getDeals(currencyCode: string): Promise<Product[]> {
    const deals = MOCK_PRODUCTS.filter((p) => DEAL_PRODUCTS.includes(p.id));
    // Add "original price" concept by increasing the displayed price 20%
    return Promise.resolve(
      deals.map((p) => {
        const discountedPrice = getPrice(p, currencyCode);
        const originalUnits = Math.floor(discountedPrice.units * 1.25);
        return {
          ...p,
          priceUsd: discountedPrice,
          // Store original price in a custom field for display
          // @ts-ignore
          originalPrice: { ...discountedPrice, units: originalUnits },
        };
      })
    );
  },

  // Order history
  getOrders(): Promise<MockOrder[]> {
    return Promise.resolve(mockOrders);
  },

  getOrder(orderId: string): Promise<MockOrder | undefined> {
    return Promise.resolve(mockOrders.find((o) => o.id === orderId));
  },
};

export type { MockOrder };
export { MOCK_PRODUCTS, DEAL_PRODUCTS };
export default MockApiGateway;
