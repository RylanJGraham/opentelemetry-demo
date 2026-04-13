// Copyright The OpenTelemetry Authors
// SPDX-License-Identifier: Apache-2.0
import { ThemedView } from "@/components/ThemedView";
import { ThemedText } from "@/components/ThemedText";
import { useLocalSearchParams, Stack } from "expo-router";
import { ActivityIndicator, Image, StyleSheet, ScrollView, View, Pressable, TextInput } from "react-native";
import { useQuery } from "@tanstack/react-query";
import ApiGateway from "@/gateways/Api.gateway";
import { useCart } from "@/providers/Cart.provider";
import ProductList from "@/components/ProductList";
import Toast from "react-native-toast-message";
import { useState, useEffect } from "react";
import { useThemeColor } from "@/hooks/useThemeColor";

// Mock reviews
const MOCK_REVIEWS = [
  { id: 1, user: "Sarah J.", rating: 5, date: "2026-03-15", text: "Absolutely love this! Great quality and fast shipping.", verified: true },
  { id: 2, user: "Mike R.", rating: 4, date: "2026-02-28", text: "Good product, exactly as described. Would recommend.", verified: true },
  { id: 3, user: "Lisa T.", rating: 5, date: "2026-02-10", text: "Bought as a gift and they loved it! Will buy again.", verified: true },
];

const SAMPLE_IMAGES = [
  "https://images.unsplash.com/photo-1518709268805-4e9042af9f23?q=80&w=800&auto=format&fit=crop",
  "https://images.unsplash.com/photo-1614729939124-032f0b56c9ce?q=80&w=800&auto=format&fit=crop",
  "https://images.unsplash.com/photo-1541185933-ef5d8ed016c2?q=80&w=800&auto=format&fit=crop",
  "https://images.unsplash.com/photo-1628126235206-5260b9ea6441?q=80&w=800&auto=format&fit=crop",
  "https://images.unsplash.com/photo-1610296669228-602fa827fc1f?q=80&w=800&auto=format&fit=crop",
  "https://images.unsplash.com/photo-1635322966219-b75ed372fba1?q=80&w=800&auto=format&fit=crop",
  "https://images.unsplash.com/photo-1454789548928-9efd52dc4031?q=80&w=800&auto=format&fit=crop"
];

function getAwesomeImage(id: string | undefined) {
  if (!id) return SAMPLE_IMAGES[0];
  let hash = 0;
  for (let i = 0; i < id.length; i++) hash += id.charCodeAt(i);
  return SAMPLE_IMAGES[hash % SAMPLE_IMAGES.length];
}

export default function ProductDetails() {
  const { id } = useLocalSearchParams();
  const productId = Array.isArray(id) ? id[0] : id;
  const { addItem } = useCart();
  const tint = useThemeColor({}, "tint");
  const [quantity, setQuantity] = useState(1);
  const [activeTab, setActiveTab] = useState<"description" | "reviews">("description");
  const [isWishlisted, setIsWishlisted] = useState(false);

  const { data: product, isLoading } = useQuery({
    queryKey: ["product", productId, "USD"],
    queryFn: () => ApiGateway.getProduct(productId!, "USD"),
    enabled: !!productId,
  });

  const { data: recommendations, isLoading: recommendationsLoading } = useQuery({
    queryKey: ["recommendations", productId, "USD"],
    queryFn: () => ApiGateway.listRecommendations([productId!], "USD"),
    enabled: !!productId,
  });

  const onAddToCart = () => {
    if (product) {
      addItem({
        productId: product.id,
        quantity,
      });
      Toast.show({
        type: "success",
        position: "bottom",
        text1: "Added to Cart!",
        text2: `${quantity} × ${product.name}`,
      });
    }
  };

  const toggleWishlist = () => {
    setIsWishlisted(!isWishlisted);
    Toast.show({
      type: isWishlisted ? "info" : "success",
      text1: isWishlisted ? "Removed from wishlist" : "Added to wishlist!",
    });
  };

  const renderStars = (count: number) => (
    <View style={styles.stars}>
      {[1, 2, 3, 4, 5].map((i) => (
        <ThemedText key={i} style={styles.star}>
          {i <= count ? "★" : "☆"}
        </ThemedText>
      ))}
    </View>
  );

  if (isLoading || !product) {
    return (
      <ThemedView style={styles.center}>
        <ActivityIndicator size="large" />
      </ThemedView>
    );
  }

  const price = (product.priceUsd?.units || 0) + (product.priceUsd?.nanos || 0) / 1000000000;

  return (
    <ThemedView style={styles.container}>
      <Stack.Screen options={{ title: product.name }} />
      <ScrollView showsVerticalScrollIndicator={false}>
        {/* Product Image */}
        <View style={styles.imageContainer}>
          <Image 
            source={{ uri: getAwesomeImage(product.id) }} 
            style={styles.image}
            resizeMode="cover"
          />
          <Pressable 
            style={[styles.wishlistButton, isWishlisted && styles.wishlistActive]}
            onPress={toggleWishlist}
          >
            <ThemedText style={styles.wishlistText}>
              {isWishlisted ? "❤️" : "🤍"}
            </ThemedText>
          </Pressable>
          <View style={styles.badge}>
            <ThemedText style={styles.badgeText}>In Stock</ThemedText>
          </View>
        </View>

        <View style={styles.content}>
          {/* Title & Price */}
          <ThemedText style={styles.title}>{product.name}</ThemedText>
          
          <View style={styles.ratingRow}>
            {renderStars(4)}
            <ThemedText style={styles.ratingText}>({MOCK_REVIEWS.length} reviews)</ThemedText>
          </View>

          <View style={styles.priceRow}>
            <ThemedText style={styles.price}>${price.toFixed(2)}</ThemedText>
            <ThemedText style={styles.originalPrice}>${(price * 1.2).toFixed(2)}</ThemedText>
            <View style={styles.discountBadge}>
              <ThemedText style={styles.discountText}>-20%</ThemedText>
            </View>
          </View>

          {/* Quantity Selector */}
          <View style={styles.quantitySection}>
            <ThemedText style={styles.quantityLabel}>Quantity:</ThemedText>
            <View style={styles.quantitySelector}>
              <Pressable 
                style={styles.quantityButton}
                onPress={() => setQuantity(Math.max(1, quantity - 1))}
              >
                <ThemedText style={styles.quantityButtonText}>−</ThemedText>
              </Pressable>
              <ThemedText style={styles.quantityValue}>{quantity}</ThemedText>
              <Pressable 
                style={styles.quantityButton}
                onPress={() => setQuantity(quantity + 1)}
              >
                <ThemedText style={styles.quantityButtonText}>+</ThemedText>
              </Pressable>
            </View>
          </View>

          {/* Action Buttons */}
          <View style={styles.actionButtons}>
            <Pressable style={styles.addToCartButton} onPress={onAddToCart}>
              <ThemedText style={styles.addToCartText}>🛒 Add to Cart</ThemedText>
            </Pressable>
            <Pressable style={styles.buyNowButton}>
              <ThemedText style={styles.buyNowText}>⚡ Buy Now</ThemedText>
            </Pressable>
          </View>

          {/* Tabs */}
          <View style={styles.tabs}>
            <Pressable 
              style={[styles.tab, activeTab === "description" && styles.activeTab]}
              onPress={() => setActiveTab("description")}
            >
              <ThemedText style={[styles.tabText, activeTab === "description" && styles.activeTabText]}>
                Description
              </ThemedText>
            </Pressable>
            <Pressable 
              style={[styles.tab, activeTab === "reviews" && styles.activeTab]}
              onPress={() => setActiveTab("reviews")}
            >
              <ThemedText style={[styles.tabText, activeTab === "reviews" && styles.activeTabText]}>
                Reviews ({MOCK_REVIEWS.length})
              </ThemedText>
            </Pressable>
          </View>

          {/* Tab Content */}
          <View style={styles.tabContent}>
            {activeTab === "description" ? (
              <View>
                <ThemedText style={styles.description}>{product.description}</ThemedText>
                
                <View style={styles.features}>
                  <ThemedText style={styles.featuresTitle}>Features:</ThemedText>
                  {[
                    "✓ Premium quality materials",
                    "✓ 30-day money-back guarantee",
                    "✓ Free shipping on orders over $50",
                    "✓ Officially licensed product",
                  ].map((feature, i) => (
                    <ThemedText key={i} style={styles.feature}>{feature}</ThemedText>
                  ))}
                </View>
              </View>
            ) : (
              <View>
                {MOCK_REVIEWS.map((review) => (
                  <View key={review.id} style={[styles.review, { borderColor: tint }]}>
                    <View style={styles.reviewHeader}>
                      <View style={styles.reviewUser}>
                        <View style={styles.avatar}>
                          <ThemedText>{review.user[0]}</ThemedText>
                        </View>
                        <View>
                          <ThemedText style={styles.reviewUserName}>{review.user}</ThemedText>
                          <ThemedText style={styles.reviewDate}>{review.date}</ThemedText>
                        </View>
                      </View>
                      {review.verified && (
                        <View style={styles.verifiedBadge}>
                          <ThemedText style={styles.verifiedText}>✓ Verified</ThemedText>
                        </View>
                      )}
                    </View>
                    {renderStars(review.rating)}
                    <ThemedText style={styles.reviewText}>{review.text}</ThemedText>
                  </View>
                ))}
              </View>
            )}
          </View>
        </View>

        {/* Recommendations */}
        {recommendations && recommendations.length > 0 && (
          <View style={styles.recommendationsContainer}>
            <ThemedText style={styles.sectionTitle}>You might also like</ThemedText>
            <ProductList productList={recommendations} />
          </View>
        )}

        <View style={styles.bottomPadding} />
      </ScrollView>
    </ThemedView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
  },
  center: {
    flex: 1,
    justifyContent: "center",
    alignItems: "center",
  },
  imageContainer: {
    position: "relative",
  },
  image: {
    width: "100%",
    height: 300,
  },
  wishlistButton: {
    position: "absolute",
    top: 16,
    right: 16,
    backgroundColor: "rgba(255,255,255,0.9)",
    width: 44,
    height: 44,
    borderRadius: 22,
    justifyContent: "center",
    alignItems: "center",
  },
  wishlistActive: {
    backgroundColor: "rgba(255,200,200,0.9)",
  },
  wishlistText: {
    fontSize: 22,
  },
  badge: {
    position: "absolute",
    bottom: 16,
    left: 16,
    backgroundColor: "#4CAF50",
    paddingHorizontal: 12,
    paddingVertical: 6,
    borderRadius: 4,
  },
  badgeText: {
    color: "#fff",
    fontSize: 12,
    fontWeight: "600",
  },
  content: {
    padding: 20,
  },
  title: {
    fontSize: 24,
    fontWeight: "bold",
    marginBottom: 8,
  },
  ratingRow: {
    flexDirection: "row",
    alignItems: "center",
    marginBottom: 12,
  },
  stars: {
    flexDirection: "row",
  },
  star: {
    fontSize: 16,
    color: "#FFD700",
  },
  ratingText: {
    marginLeft: 8,
    fontSize: 14,
    color: "#888",
  },
  priceRow: {
    flexDirection: "row",
    alignItems: "center",
    marginBottom: 16,
  },
  price: {
    fontSize: 28,
    fontWeight: "bold",
    color: "#4CAF50",
  },
  originalPrice: {
    fontSize: 18,
    textDecorationLine: "line-through",
    color: "#888",
    marginLeft: 12,
  },
  discountBadge: {
    backgroundColor: "#e94560",
    paddingHorizontal: 8,
    paddingVertical: 4,
    borderRadius: 4,
    marginLeft: 12,
  },
  discountText: {
    color: "#fff",
    fontSize: 12,
    fontWeight: "bold",
  },
  quantitySection: {
    flexDirection: "row",
    alignItems: "center",
    marginBottom: 20,
  },
  quantityLabel: {
    fontSize: 14,
    marginRight: 12,
  },
  quantitySelector: {
    flexDirection: "row",
    alignItems: "center",
    borderWidth: 1,
    borderColor: "#444",
    borderRadius: 8,
  },
  quantityButton: {
    width: 40,
    height: 40,
    justifyContent: "center",
    alignItems: "center",
  },
  quantityButtonText: {
    fontSize: 20,
    fontWeight: "bold",
  },
  quantityValue: {
    width: 40,
    textAlign: "center",
    fontSize: 16,
    fontWeight: "600",
  },
  actionButtons: {
    flexDirection: "row",
    gap: 12,
    marginBottom: 24,
  },
  addToCartButton: {
    flex: 1,
    backgroundColor: "#4CAF50",
    paddingVertical: 16,
    borderRadius: 10,
    alignItems: "center",
  },
  addToCartText: {
    color: "#fff",
    fontSize: 16,
    fontWeight: "600",
  },
  buyNowButton: {
    flex: 1,
    backgroundColor: "#ff9800",
    paddingVertical: 16,
    borderRadius: 10,
    alignItems: "center",
  },
  buyNowText: {
    color: "#fff",
    fontSize: 16,
    fontWeight: "600",
  },
  tabs: {
    flexDirection: "row",
    borderBottomWidth: 1,
    borderBottomColor: "#444",
    marginBottom: 16,
  },
  tab: {
    flex: 1,
    paddingVertical: 12,
    alignItems: "center",
  },
  activeTab: {
    borderBottomWidth: 2,
    borderBottomColor: "#4CAF50",
  },
  tabText: {
    fontSize: 14,
    color: "#888",
  },
  activeTabText: {
    color: "#4CAF50",
    fontWeight: "600",
  },
  tabContent: {
    minHeight: 200,
  },
  description: {
    fontSize: 15,
    lineHeight: 24,
    marginBottom: 16,
  },
  features: {
    marginTop: 8,
  },
  featuresTitle: {
    fontSize: 16,
    fontWeight: "600",
    marginBottom: 8,
  },
  feature: {
    fontSize: 14,
    marginBottom: 6,
    color: "#aaa",
  },
  review: {
    paddingVertical: 16,
    borderBottomWidth: 1,
  },
  reviewHeader: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    marginBottom: 8,
  },
  reviewUser: {
    flexDirection: "row",
    alignItems: "center",
  },
  avatar: {
    width: 36,
    height: 36,
    borderRadius: 18,
    backgroundColor: "#444",
    justifyContent: "center",
    alignItems: "center",
    marginRight: 10,
  },
  reviewUserName: {
    fontSize: 14,
    fontWeight: "600",
  },
  reviewDate: {
    fontSize: 12,
    color: "#888",
  },
  verifiedBadge: {
    backgroundColor: "#4CAF50",
    paddingHorizontal: 8,
    paddingVertical: 4,
    borderRadius: 4,
  },
  verifiedText: {
    color: "#fff",
    fontSize: 10,
  },
  reviewText: {
    fontSize: 14,
    marginTop: 8,
    lineHeight: 20,
  },
  recommendationsContainer: {
    marginTop: 20,
    paddingTop: 20,
    borderTopWidth: 1,
    borderTopColor: "#333",
  },
  sectionTitle: {
    fontSize: 20,
    fontWeight: "bold",
    marginLeft: 20,
    marginBottom: 10,
  },
  bottomPadding: {
    height: 40,
  },
});
