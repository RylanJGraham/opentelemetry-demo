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

// Filler product data with placeholder images
const MOCK_PRODUCTS: Product[] = [
  {
    id: "1",
    name: "Astronaut Figurine",
    description: "A detailed figurine of an astronaut in a space suit. Perfect for your desk!",
    picture: "https://placehold.co/400x400/1e3a5f/white?text=👨‍🚀+Astronaut",
    priceUsd: { currencyCode: "USD", units: 25, nanos: 99 },
    categories: ["figurines"],
  },
  {
    id: "2",
    name: "Mars Rover Model",
    description: "Scale model of the Perseverance Mars rover. 1:50 scale.",
    picture: "https://placehold.co/400x400/c1440e/white?text=🚀+Rover",
    priceUsd: { currencyCode: "USD", units: 45, nanos: 0 },
    categories: ["models"],
  },
  {
    id: "3",
    name: "Telescope",
    description: "High-quality refracting telescope for stargazing. 70mm aperture.",
    picture: "https://placehold.co/400x400/0d1b2a/white?text=🔭+Telescope",
    priceUsd: { currencyCode: "USD", units: 199, nanos: 0 },
    categories: ["equipment"],
  },
  {
    id: "4",
    name: "Star Map Poster",
    description: "Beautiful constellation map for your wall. Glows in the dark!",
    picture: "https://placehold.co/400x400/0b1026/white?text=⭐+Star+Map",
    priceUsd: { currencyCode: "USD", units: 15, nanos: 99 },
    categories: ["posters"],
  },
  {
    id: "5",
    name: "Space Station LEGO Set",
    description: "Build your own ISS with this 864-piece LEGO set.",
    picture: "https://placehold.co/400x400/f4d03f/black?text=🧱+LEGO+ISS",
    priceUsd: { currencyCode: "USD", units: 79, nanos: 99 },
    categories: ["toys"],
  },
  {
    id: "6",
    name: "Meteorite Fragment",
    description: "Genuine meteorite fragment from the Campo del Cielo fall.",
    picture: "https://placehold.co/400x400/5a5a5a/white?text=☄️+Meteorite",
    priceUsd: { currencyCode: "USD", units: 120, nanos: 0 },
    categories: ["collectibles"],
  },
  {
    id: "7",
    name: "NASA Hoodie",
    description: "Comfortable hoodie with the classic NASA 'meatball' logo.",
    picture: "https://placehold.co/400x400/1a5490/white?text=👕+NASA+Hoodie",
    priceUsd: { currencyCode: "USD", units: 55, nanos: 0 },
    categories: ["clothing"],
  },
  {
    id: "8",
    name: "Planet Lamps",
    description: "3D printed lamps that look like planets. Remote controlled colors.",
    picture: "https://placehold.co/400x400/2d1b69/white?text=🪐+Planet+Lamp",
    priceUsd: { currencyCode: "USD", units: 35, nanos: 99 },
    categories: ["home"],
  },
];

// In-memory cart storage
let mockCart: IProductCart = {
  userId: "mock-user",
  items: [],
  currencyCode: "USD",
};

// Generate price in different currencies
const getPrice = (product: Product, currencyCode: string): Money => {
  const basePrice = product.priceUsd?.units || 0;
  const baseNanos = product.priceUsd?.nanos || 0;
  
  const rates: Record<string, number> = {
    USD: 1,
    EUR: 0.85,
    GBP: 0.73,
    JPY: 110,
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

  async emptyCart(): Promise<undefined> {
    mockCart.items = [];
    return undefined;
  },

  getSupportedCurrencyList(): Promise<string[]> {
    return Promise.resolve(["USD", "EUR", "GBP", "JPY"]);
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
    // Mock order placement
    mockCart.items = [];
    
    return Promise.resolve({
      orderId: `ORDER-${Date.now()}`,
      shippingTrackingId: `TRACK-${Math.random().toString(36).substr(2, 9)}`,
      shippingCost: { currencyCode, units: 5, nanos: 0 },
      totalPaid: { currencyCode, units: 100, nanos: 0 }, // Simplified
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
        text: "Space deals!",
        image: "/images/ads/ad1.jpg",
      },
      {
        redirectUrl: "https://example.com/ad2",
        text: "Astronaut gear!",
        image: "/images/ads/ad2.jpg",
      },
    ]);
  },
};

export default MockApiGateway;
