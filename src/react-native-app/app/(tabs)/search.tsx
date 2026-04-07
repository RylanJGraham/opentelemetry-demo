// Copyright The OpenTelemetry Authors
// SPDX-License-Identifier: Apache-2.0
import { ThemedView } from "@/components/ThemedView";
import { ThemedText } from "@/components/ThemedText";
import { StyleSheet, TextInput, ScrollView, View } from "react-native";
import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import ApiGateway from "@/gateways/Api.gateway";
import ProductList from "@/components/ProductList";

export default function Search() {
  const [searchQuery, setSearchQuery] = useState("");
  const { data: productList = [] } = useQuery({
    queryKey: ["products", "USD"],
    queryFn: () => ApiGateway.listProducts("USD"),
  });

  const filteredProducts = productList.filter((product) =>
    product.name.toLowerCase().includes(searchQuery.toLowerCase())
  );

  return (
    <ThemedView style={styles.container}>
      <View style={styles.searchBarContainer}>
        <TextInput
          style={styles.searchBar}
          placeholder="Search products..."
          placeholderTextColor="#888"
          value={searchQuery}
          onChangeText={setSearchQuery}
        />
      </View>
      <ScrollView>
        {filteredProducts.length > 0 ? (
          <ProductList productList={filteredProducts} />
        ) : (
          <ThemedText style={styles.noResults}>No products matched your search.</ThemedText>
        )}
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
    borderBottomColor: "#444",
  },
  searchBar: {
    height: 40,
    backgroundColor: "#eee",
    borderRadius: 8,
    paddingHorizontal: 15,
    color: "#000",
  },
  noResults: {
    marginTop: 20,
    textAlign: "center",
  },
});
