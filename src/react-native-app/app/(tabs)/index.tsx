// Copyright The OpenTelemetry Authors
// SPDX-License-Identifier: Apache-2.0
import { ThemedView } from "@/components/ThemedView";
import ProductList from "@/components/ProductList";
import { useQuery } from "@tanstack/react-query";
import { ScrollView, StyleSheet, View, Pressable } from "react-native";
import { ThemedText } from "@/components/ThemedText";
import ApiGateway from "@/gateways/Api.gateway";
import { useState } from "react";
import { useThemeColor } from "@/hooks/useThemeColor";
import { router } from "expo-router";

const CATEGORIES = [
  { id: "all", name: "All", icon: "🚀" },
  { id: "electronics", name: "Tech", icon: "🔭" },
  { id: "toys", name: "Toys", icon: "🧱" },
  { id: "home", name: "Home", icon: "🪐" },
  { id: "clothing", name: "Wear", icon: "👕" },
  { id: "collectibles", name: "Collect", icon: "☄️" },
];

export default function Index() {
  const tint = useThemeColor({}, "tint");
  const [selectedCategory, setSelectedCategory] = useState("all");

  const { data: productList = [], isLoading } = useQuery({
    queryKey: ["products", "USD"],
    queryFn: () => ApiGateway.listProducts("USD"),
  });

  const { data: categories = [] } = useQuery({
    queryKey: ["categories"],
    queryFn: () => ApiGateway.getCategories(),
  });

  const filteredProducts = selectedCategory === "all" 
    ? productList 
    : productList.filter((p) => p.categories?.includes(selectedCategory));

  return (
    <ThemedView style={styles.container}>
      {/* Header */}
      <View style={styles.header}>
        <ThemedText style={styles.title}>🌌 SpaceShop</ThemedText>
        <ThemedText style={styles.subtitle}>Explore the universe of space gear</ThemedText>
      </View>

      {/* Category Pills */}
      <ScrollView 
        horizontal 
        showsHorizontalScrollIndicator={false}
        style={styles.categoryScroll}
        contentContainerStyle={styles.categoryContainer}
      >
        {CATEGORIES.map((cat) => (
          <Pressable
            key={cat.id}
            style={[
              styles.categoryPill,
              selectedCategory === cat.id && [styles.activePill, { backgroundColor: tint }],
            ]}
            onPress={() => setSelectedCategory(cat.id)}
          >
            <ThemedText style={styles.categoryIcon}>{cat.icon}</ThemedText>
            <ThemedText 
              style={[
                styles.categoryText,
                selectedCategory === cat.id && styles.activeCategoryText,
              ]}
            >
              {cat.name}
            </ThemedText>
          </Pressable>
        ))}
      </ScrollView>

      {/* Results Count */}
      <View style={styles.resultsBar}>
        <ThemedText style={styles.resultsText}>
          {filteredProducts.length} {filteredProducts.length === 1 ? "product" : "products"}
          {selectedCategory !== "all" && ` in ${selectedCategory}`}
        </ThemedText>
        <Pressable style={styles.filterButton}>
          <ThemedText>Filter ▼</ThemedText>
        </Pressable>
      </View>

      {/* Product List */}
      <ScrollView showsVerticalScrollIndicator={false}>
        {isLoading ? (
          <ThemedText style={styles.loading}>Loading products...</ThemedText>
        ) : filteredProducts.length ? (
          <ProductList productList={filteredProducts} />
        ) : (
          <View style={styles.empty}>
            <ThemedText style={styles.emptyIcon}>🔭</ThemedText>
            <ThemedText style={styles.emptyTitle}>No products found</ThemedText>
            <ThemedText style={styles.emptySubtitle}>
              Try selecting a different category
            </ThemedText>
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
  header: {
    padding: 20,
    paddingBottom: 10,
  },
  title: {
    fontSize: 28,
    fontWeight: "bold",
  },
  subtitle: {
    fontSize: 14,
    color: "#888",
    marginTop: 4,
  },
  categoryScroll: {
    maxHeight: 60,
    marginBottom: 10,
  },
  categoryContainer: {
    paddingHorizontal: 15,
    gap: 10,
  },
  categoryPill: {
    flexDirection: "row",
    alignItems: "center",
    paddingHorizontal: 16,
    paddingVertical: 10,
    borderRadius: 25,
    backgroundColor: "rgba(128,128,128,0.1)",
    borderWidth: 1,
    borderColor: "rgba(128,128,128,0.2)",
  },
  activePill: {
    borderWidth: 0,
  },
  categoryIcon: {
    fontSize: 16,
    marginRight: 6,
  },
  categoryText: {
    fontSize: 14,
    fontWeight: "500",
  },
  activeCategoryText: {
    color: "#fff",
    fontWeight: "600",
  },
  resultsBar: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    paddingHorizontal: 20,
    paddingVertical: 10,
    borderBottomWidth: 1,
    borderBottomColor: "rgba(128,128,128,0.1)",
  },
  resultsText: {
    fontSize: 14,
    color: "#888",
  },
  filterButton: {
    paddingHorizontal: 12,
    paddingVertical: 6,
    backgroundColor: "rgba(128,128,128,0.1)",
    borderRadius: 6,
  },
  loading: {
    textAlign: "center",
    marginTop: 40,
    color: "#888",
  },
  empty: {
    alignItems: "center",
    paddingVertical: 60,
  },
  emptyIcon: {
    fontSize: 64,
    marginBottom: 16,
  },
  emptyTitle: {
    fontSize: 20,
    fontWeight: "bold",
    marginBottom: 8,
  },
  emptySubtitle: {
    fontSize: 14,
    color: "#888",
  },
  bottomPadding: {
    height: 20,
  },
});
