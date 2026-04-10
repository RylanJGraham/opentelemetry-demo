// Copyright The OpenTelemetry Authors
// SPDX-License-Identifier: Apache-2.0
import { ThemedView } from "@/components/ThemedView";
import { ThemedText } from "@/components/ThemedText";
import { StyleSheet, ScrollView, View, Pressable, Image, ActivityIndicator } from "react-native";
import { useQuery } from "@tanstack/react-query";
import ApiGateway from "@/gateways/Api.gateway";
import { useCart } from "@/providers/Cart.provider";
import Toast from "react-native-toast-message";
import { router } from "expo-router";

export default function Deals() {
  const { addItem } = useCart();
  const { data: ads = [], isLoading: adsLoading } = useQuery({
    queryKey: ["ads"],
    queryFn: () => ApiGateway.listAds([]),
  });

  const { data: deals = [], isLoading: dealsLoading } = useQuery({
    queryKey: ["deals", "USD"],
    queryFn: () => ApiGateway.getDeals("USD"),
  });

  const handleAddToCart = (productId: string, productName: string) => {
    addItem({ productId, quantity: 1 });
    Toast.show({
      type: "success",
      position: "bottom",
      text1: `${productName} added to cart!`,
    });
  };

  const renderStars = () => (
    <View style={styles.stars}>
      {[1, 2, 3, 4, 5].map((i) => (
        <ThemedText key={i} style={styles.star}>⭐</ThemedText>
      ))}
    </View>
  );

  return (
    <ThemedView style={styles.container}>
      <ScrollView showsVerticalScrollIndicator={false}>
        <ThemedText style={styles.title}>🔥 Special Offers</ThemedText>
        
        {/* Promo Banners */}
        {adsLoading ? (
          <ActivityIndicator style={styles.loader} />
        ) : (
          ads.map((ad, idx) => (
            <View key={idx} style={[styles.adBanner, idx === 0 && styles.firstBanner]}>
              <ThemedText style={styles.adText}>{ad.text}</ThemedText>
              <Pressable style={styles.adButton}>
                <ThemedText style={styles.adButtonText}>Shop Now</ThemedText>
              </Pressable>
            </View>
          ))
        )}

        {/* Featured Deal */}
        <View style={styles.featuredSection}>
          <View style={styles.featuredBadge}>
            <ThemedText style={styles.featuredBadgeText}>FEATURED DEAL</ThemedText>
          </View>
          <ThemedText style={styles.featuredTitle}>Flash Sale - 25% Off!</ThemedText>
          <ThemedText style={styles.featuredSubtitle}>Limited time offer on select space gear</ThemedText>
          <View style={styles.countdown}>
            <View style={styles.countdownBox}>
              <ThemedText style={styles.countdownNumber}>02</ThemedText>
              <ThemedText style={styles.countdownLabel}>hrs</ThemedText>
            </View>
            <ThemedText style={styles.countdownSeparator}>:</ThemedText>
            <View style={styles.countdownBox}>
              <ThemedText style={styles.countdownNumber}>45</ThemedText>
              <ThemedText style={styles.countdownLabel}>min</ThemedText>
            </View>
            <ThemedText style={styles.countdownSeparator}>:</ThemedText>
            <View style={styles.countdownBox}>
              <ThemedText style={styles.countdownNumber}>30</ThemedText>
              <ThemedText style={styles.countdownLabel}>sec</ThemedText>
            </View>
          </View>
        </View>

        {/* Deal Products */}
        <View style={styles.dealsSection}>
          <ThemedText style={styles.sectionTitle}>⚡ Lightning Deals</ThemedText>
          
          {dealsLoading ? (
            <ActivityIndicator style={styles.loader} />
          ) : (
            deals.map((product) => {
              // @ts-ignore - originalPrice is added by getDeals
              const originalPrice = product.originalPrice?.units || Math.floor((product.priceUsd?.units || 0) * 1.25);
              const currentPrice = product.priceUsd?.units || 0;
              const savings = originalPrice - currentPrice;
              const discountPercent = Math.round((savings / originalPrice) * 100);

              return (
                <View key={product.id} style={styles.dealCard}>
                  <Pressable 
                    style={styles.dealContent}
                    onPress={() => router.push(`/product/${product.id}`)}
                  >
                    {/* Discount Badge */}
                    <View style={styles.discountBadge}>
                      <ThemedText style={styles.discountText}>-{discountPercent}%</ThemedText>
                    </View>

                    {/* Product Image */}
                    <Image 
                      source={{ uri: product.picture }} 
                      style={styles.dealImage}
                    />

                    {/* Product Info */}
                    <View style={styles.dealInfo}>
                      <ThemedText style={styles.dealName} numberOfLines={2}>
                        {product.name}
                      </ThemedText>
                      {renderStars()}
                      <ThemedText style={styles.dealDescription} numberOfLines={2}>
                        {product.description}
                      </ThemedText>
                      
                      <View style={styles.priceContainer}>
                        <ThemedText style={styles.originalPrice}>
                          ${originalPrice.toFixed(2)}
                        </ThemedText>
                        <ThemedText style={styles.dealPrice}>
                          ${currentPrice.toFixed(2)}
                        </ThemedText>
                      </View>

                      {/* Progress Bar */}
                      <View style={styles.progressContainer}>
                        <View style={[styles.progressBar, { width: `${Math.random() * 40 + 40}%` }]} />
                        <ThemedText style={styles.progressText}>Selling fast!</ThemedText>
                      </View>
                    </View>
                  </Pressable>

                  {/* Add to Cart Button */}
                  <Pressable 
                    style={styles.addButton}
                    onPress={() => handleAddToCart(product.id, product.name)}
                  >
                    <ThemedText style={styles.addButtonText}>Add to Cart</ThemedText>
                  </Pressable>
                </View>
              );
            })
          )}
        </View>

        {/* Categories Quick Links */}
        <View style={styles.categoriesSection}>
          <ThemedText style={styles.sectionTitle}>Browse Categories</ThemedText>
          <View style={styles.categoryGrid}>
            {[
              { name: "Electronics", icon: "🔭", color: "#1e3a5f" },
              { name: "Toys", icon: "🚀", color: "#c1440e" },
              { name: "Home", icon: "🪐", color: "#2d1b69" },
              { name: "Clothing", icon: "👕", color: "#1a5490" },
            ].map((cat) => (
              <Pressable key={cat.name} style={[styles.categoryCard, { backgroundColor: cat.color }]}>
                <ThemedText style={styles.categoryIcon}>{cat.icon}</ThemedText>
                <ThemedText style={styles.categoryName}>{cat.name}</ThemedText>
              </Pressable>
            ))}
          </View>
        </View>

        <View style={styles.bottomPadding} />
      </ScrollView>
    </ThemedView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    padding: 15,
  },
  loader: {
    marginVertical: 20,
  },
  title: {
    fontSize: 28,
    fontWeight: "bold",
    marginBottom: 15,
  },
  adBanner: {
    backgroundColor: "#ff6b35",
    padding: 16,
    borderRadius: 12,
    marginBottom: 12,
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
  },
  firstBanner: {
    backgroundColor: "#6b5ce7",
  },
  adText: {
    color: "#fff",
    fontWeight: "bold",
    fontSize: 14,
    flex: 1,
  },
  adButton: {
    backgroundColor: "rgba(255,255,255,0.2)",
    paddingHorizontal: 12,
    paddingVertical: 6,
    borderRadius: 6,
    marginLeft: 10,
  },
  adButtonText: {
    color: "#fff",
    fontSize: 12,
    fontWeight: "600",
  },
  featuredSection: {
    backgroundColor: "#1a1a2e",
    padding: 20,
    borderRadius: 16,
    marginBottom: 20,
    alignItems: "center",
  },
  featuredBadge: {
    backgroundColor: "#e94560",
    paddingHorizontal: 12,
    paddingVertical: 4,
    borderRadius: 20,
    marginBottom: 12,
  },
  featuredBadgeText: {
    color: "#fff",
    fontSize: 10,
    fontWeight: "bold",
    letterSpacing: 1,
  },
  featuredTitle: {
    fontSize: 24,
    fontWeight: "bold",
    color: "#fff",
    marginBottom: 6,
  },
  featuredSubtitle: {
    fontSize: 14,
    color: "#888",
    marginBottom: 16,
  },
  countdown: {
    flexDirection: "row",
    alignItems: "center",
  },
  countdownBox: {
    backgroundColor: "#333",
    padding: 10,
    borderRadius: 8,
    alignItems: "center",
    minWidth: 50,
  },
  countdownNumber: {
    fontSize: 20,
    fontWeight: "bold",
    color: "#fff",
  },
  countdownLabel: {
    fontSize: 10,
    color: "#888",
  },
  countdownSeparator: {
    fontSize: 20,
    fontWeight: "bold",
    color: "#fff",
    marginHorizontal: 8,
  },
  dealsSection: {
    marginTop: 10,
  },
  sectionTitle: {
    fontSize: 20,
    fontWeight: "bold",
    marginBottom: 15,
  },
  dealCard: {
    backgroundColor: "rgba(128,128,128,0.08)",
    borderRadius: 16,
    marginBottom: 16,
    overflow: "hidden",
  },
  dealContent: {
    flexDirection: "row",
    padding: 12,
  },
  discountBadge: {
    position: "absolute",
    top: 8,
    left: 8,
    backgroundColor: "#e94560",
    paddingHorizontal: 8,
    paddingVertical: 4,
    borderRadius: 6,
    zIndex: 1,
  },
  discountText: {
    color: "#fff",
    fontSize: 12,
    fontWeight: "bold",
  },
  dealImage: {
    width: 100,
    height: 100,
    borderRadius: 12,
    backgroundColor: "#333",
  },
  dealInfo: {
    flex: 1,
    marginLeft: 12,
  },
  dealName: {
    fontSize: 14,
    fontWeight: "600",
    marginBottom: 4,
  },
  stars: {
    flexDirection: "row",
    marginBottom: 4,
  },
  star: {
    fontSize: 10,
  },
  dealDescription: {
    fontSize: 11,
    color: "#888",
    marginBottom: 8,
  },
  priceContainer: {
    flexDirection: "row",
    alignItems: "center",
  },
  originalPrice: {
    fontSize: 12,
    textDecorationLine: "line-through",
    color: "#888",
    marginRight: 8,
  },
  dealPrice: {
    fontSize: 16,
    fontWeight: "bold",
    color: "#4CAF50",
  },
  progressContainer: {
    marginTop: 8,
  },
  progressBar: {
    height: 4,
    backgroundColor: "#e94560",
    borderRadius: 2,
  },
  progressText: {
    fontSize: 10,
    color: "#e94560",
    marginTop: 4,
  },
  addButton: {
    backgroundColor: "#4CAF50",
    paddingVertical: 12,
    alignItems: "center",
  },
  addButtonText: {
    color: "#fff",
    fontWeight: "600",
  },
  categoriesSection: {
    marginTop: 10,
  },
  categoryGrid: {
    flexDirection: "row",
    flexWrap: "wrap",
    gap: 10,
  },
  categoryCard: {
    flex: 1,
    minWidth: "45%",
    padding: 16,
    borderRadius: 12,
    alignItems: "center",
  },
  categoryIcon: {
    fontSize: 32,
    marginBottom: 8,
  },
  categoryName: {
    color: "#fff",
    fontWeight: "600",
    fontSize: 12,
  },
  bottomPadding: {
    height: 40,
  },
});
