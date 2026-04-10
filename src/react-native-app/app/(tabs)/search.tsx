// Copyright The OpenTelemetry Authors
// SPDX-License-Identifier: Apache-2.0
import { ThemedView } from "@/components/ThemedView";
import { ThemedText } from "@/components/ThemedText";
import { StyleSheet, TextInput, ScrollView, View, Pressable, ActivityIndicator } from "react-native";
import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import ApiGateway from "@/gateways/Api.gateway";
import ProductList from "@/components/ProductList";
import { useThemeColor } from "@/hooks/useThemeColor";
import { router } from "expo-router";

const RECENT_SEARCHES = [
  "telescope",
  "nasa hoodie",
  "lego",
  "mars rover",
];

const POPULAR_SEARCHES = [
  "astronaut",
  "space station",
  "planet lamp",
  "meteorite",
];

export default function Search() {
  const tint = useThemeColor({}, "tint");
  const [searchQuery, setSearchQuery] = useState("");
  const [recentSearches, setRecentSearches] = useState(RECENT_SEARCHES);

  const { data: productList = [], isLoading } = useQuery({
    queryKey: ["products", "USD"],
    queryFn: () => ApiGateway.listProducts("USD"),
  });

  const filteredProducts = productList.filter((product) =>
    product.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
    product.description?.toLowerCase().includes(searchQuery.toLowerCase()) ||
    product.categories?.some(c => c.toLowerCase().includes(searchQuery.toLowerCase()))
  );

  const handleSearch = (query: string) => {
    setSearchQuery(query);
    if (query && !recentSearches.includes(query)) {
      setRecentSearches(prev => [query, ...prev].slice(0, 5));
    }
  };

  const clearSearch = () => {
    setSearchQuery("");
  };

  const removeRecentSearch = (search: string) => {
    setRecentSearches(prev => prev.filter(s => s !== search));
  };

  return (
    <ThemedView style={styles.container}>
      {/* Search Bar */}
      <View style={styles.searchBarContainer}>
        <View style={styles.searchInputContainer}>
          <ThemedText style={styles.searchIcon}>🔍</ThemedText>
          <TextInput
            style={styles.searchBar}
            placeholder="Search products, categories..."
            placeholderTextColor="#888"
            value={searchQuery}
            onChangeText={handleSearch}
            autoFocus
          />
          {searchQuery.length > 0 && (
            <Pressable onPress={clearSearch} style={styles.clearButton}>
              <ThemedText style={styles.clearIcon}>✕</ThemedText>
            </Pressable>
          )}
        </View>
      </View>

      <ScrollView showsVerticalScrollIndicator={false}>
        {searchQuery === "" ? (
          // Empty State - Show suggestions
          <View style={styles.suggestionsContainer}>
            {/* Recent Searches */}
            {recentSearches.length > 0 && (
              <View style={styles.section}>
                <View style={styles.sectionHeader}>
                  <ThemedText style={styles.sectionTitle}>Recent Searches</ThemedText>
                  <Pressable onPress={() => setRecentSearches([])}>
                    <ThemedText style={styles.clearAll}>Clear All</ThemedText>
                  </Pressable>
                </View>
                <View style={styles.chipContainer}>
                  {recentSearches.map((search) => (
                    <View key={search} style={styles.chipWrapper}>
                      <Pressable 
                        style={[styles.chip, { borderColor: tint }]}
                        onPress={() => handleSearch(search)}
                      >
                        <ThemedText style={styles.chipText}>{search}</ThemedText>
                      </Pressable>
                      <Pressable 
                        style={styles.chipRemove}
                        onPress={() => removeRecentSearch(search)}
                      >
                        <ThemedText style={styles.chipRemoveText}>✕</ThemedText>
                      </Pressable>
                    </View>
                  ))}
                </View>
              </View>
            )}

            {/* Popular Searches */}
            <View style={styles.section}>
              <ThemedText style={styles.sectionTitle}>Popular Searches</ThemedText>
              <View style={styles.chipContainer}>
                {POPULAR_SEARCHES.map((search) => (
                  <Pressable 
                    key={search}
                    style={[styles.popularChip, { backgroundColor: tint }]}
                    onPress={() => handleSearch(search)}
                  >
                    <ThemedText style={styles.popularChipText}>{search}</ThemedText>
                  </Pressable>
                ))}
              </View>
            </View>

            {/* Browse Categories */}
            <View style={styles.section}>
              <ThemedText style={styles.sectionTitle}>Browse Categories</ThemedText>
              <View style={styles.categoryGrid}>
                {[
                  { name: "Electronics", icon: "🔭", count: 5 },
                  { name: "Toys & Games", icon: "🚀", count: 4 },
                  { name: "Home & Decor", icon: "🪐", count: 4 },
                  { name: "Clothing", icon: "👕", count: 2 },
                  { name: "Collectibles", icon: "☄️", count: 3 },
                  { name: "Accessories", icon: "👜", count: 3 },
                ].map((cat) => (
                  <Pressable 
                    key={cat.name}
                    style={[styles.categoryCard, { borderColor: tint }]}
                    onPress={() => handleSearch(cat.name.toLowerCase())}
                  >
                    <ThemedText style={styles.categoryIcon}>{cat.icon}</ThemedText>
                    <ThemedText style={styles.categoryName}>{cat.name}</ThemedText>
                    <ThemedText style={styles.categoryCount}>{cat.count} items</ThemedText>
                  </Pressable>
                ))}
              </View>
            </View>
          </View>
        ) : (
          // Search Results
          <View style={styles.resultsContainer}>
            <View style={styles.resultsHeader}>
              <ThemedText style={styles.resultsTitle}>
                {isLoading ? "Searching..." : `${filteredProducts.length} results for "${searchQuery}"`}
              </ThemedText>
            </View>

            {isLoading ? (
              <ActivityIndicator style={styles.loader} size="large" />
            ) : filteredProducts.length > 0 ? (
              <ProductList productList={filteredProducts} />
            ) : (
              <View style={styles.noResults}>
                <ThemedText style={styles.noResultsIcon}>🔭</ThemedText>
                <ThemedText style={styles.noResultsTitle}>No products found</ThemedText>
                <ThemedText style={styles.noResultsSubtitle}>
                  Try searching with different keywords or browse categories
                </ThemedText>
                <Pressable 
                  style={[styles.browseButton, { backgroundColor: tint }]}
                  onPress={() => router.push("/")}
                >
                  <ThemedText style={styles.browseButtonText}>Browse All Products</ThemedText>
                </Pressable>
              </View>
            )}
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
  searchBarContainer: {
    padding: 15,
    borderBottomWidth: 1,
    borderBottomColor: "rgba(128,128,128,0.1)",
  },
  searchInputContainer: {
    flexDirection: "row",
    alignItems: "center",
    backgroundColor: "rgba(128,128,128,0.1)",
    borderRadius: 10,
    paddingHorizontal: 12,
  },
  searchIcon: {
    fontSize: 16,
    marginRight: 8,
  },
  searchBar: {
    flex: 1,
    height: 44,
    color: "#fff",
    fontSize: 16,
  },
  clearButton: {
    padding: 6,
  },
  clearIcon: {
    fontSize: 14,
    color: "#888",
  },
  suggestionsContainer: {
    padding: 15,
  },
  section: {
    marginBottom: 24,
  },
  sectionHeader: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    marginBottom: 12,
  },
  sectionTitle: {
    fontSize: 18,
    fontWeight: "600",
  },
  clearAll: {
    fontSize: 13,
    color: "#4CAF50",
  },
  chipContainer: {
    flexDirection: "row",
    flexWrap: "wrap",
    gap: 10,
  },
  chipWrapper: {
    flexDirection: "row",
    alignItems: "center",
  },
  chip: {
    flexDirection: "row",
    alignItems: "center",
    paddingHorizontal: 14,
    paddingVertical: 8,
    borderRadius: 20,
    borderWidth: 1,
    borderColor: "rgba(128,128,128,0.3)",
  },
  chipText: {
    fontSize: 14,
  },
  chipRemove: {
    marginLeft: 6,
    padding: 4,
  },
  chipRemoveText: {
    fontSize: 12,
    color: "#888",
  },
  popularChip: {
    paddingHorizontal: 14,
    paddingVertical: 8,
    borderRadius: 20,
  },
  popularChipText: {
    color: "#fff",
    fontSize: 14,
    fontWeight: "500",
  },
  categoryGrid: {
    flexDirection: "row",
    flexWrap: "wrap",
    gap: 10,
  },
  categoryCard: {
    width: "47%",
    padding: 16,
    borderRadius: 12,
    borderWidth: 1,
    alignItems: "center",
  },
  categoryIcon: {
    fontSize: 32,
    marginBottom: 8,
  },
  categoryName: {
    fontSize: 14,
    fontWeight: "600",
    marginBottom: 4,
  },
  categoryCount: {
    fontSize: 12,
    color: "#888",
  },
  resultsContainer: {
    padding: 15,
  },
  resultsHeader: {
    marginBottom: 15,
  },
  resultsTitle: {
    fontSize: 16,
    color: "#888",
  },
  loader: {
    marginTop: 40,
  },
  noResults: {
    alignItems: "center",
    paddingVertical: 60,
  },
  noResultsIcon: {
    fontSize: 64,
    marginBottom: 16,
  },
  noResultsTitle: {
    fontSize: 20,
    fontWeight: "bold",
    marginBottom: 8,
  },
  noResultsSubtitle: {
    fontSize: 14,
    color: "#888",
    textAlign: "center",
    marginBottom: 24,
    paddingHorizontal: 30,
  },
  browseButton: {
    paddingHorizontal: 24,
    paddingVertical: 14,
    borderRadius: 8,
  },
  browseButtonText: {
    color: "#fff",
    fontWeight: "600",
  },
  bottomPadding: {
    height: 20,
  },
});
