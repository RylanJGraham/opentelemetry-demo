// Copyright The OpenTelemetry Authors
// SPDX-License-Identifier: Apache-2.0
import { ThemedView } from "@/components/ThemedView";
import { ThemedText } from "@/components/ThemedText";
import { StyleSheet, ScrollView, View } from "react-native";
import { useQuery } from "@tanstack/react-query";
import ApiGateway from "@/gateways/Api.gateway";
import ProductList from "@/components/ProductList";

export default function Deals() {
  const { data: ads = [] } = useQuery({
    queryKey: ["ads"],
    queryFn: () => ApiGateway.listAds([]),
  });

  const { data: productList = [] } = useQuery({
    queryKey: ["products", "USD"],
    queryFn: () => ApiGateway.listProducts("USD"),
  });

  // Pick random subset of products as "deals"
  const dealProducts = productList.slice(0, 3);

  return (
    <ThemedView style={styles.container}>
      <ScrollView>
        <ThemedText style={styles.title}>Special Offers</ThemedText>
        
        {ads.map((ad, idx) => (
          <View key={idx} style={styles.adBanner}>
            <ThemedText style={styles.adText}>{ad.text}</ThemedText>
            <ThemedText style={styles.adLink}>Tap to view</ThemedText>
          </View>
        ))}

        <View style={styles.dealsSection}>
          <ThemedText style={styles.subtitle}>Lightning Deals</ThemedText>
          <ProductList productList={dealProducts} />
        </View>
      </ScrollView>
    </ThemedView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    padding: 20,
  },
  title: {
    fontSize: 28,
    fontWeight: "bold",
    marginBottom: 20,
  },
  subtitle: {
    fontSize: 22,
    fontWeight: "bold",
    marginTop: 20,
    marginBottom: 10,
  },
  adBanner: {
    backgroundColor: "#ffeb3b",
    padding: 15,
    borderRadius: 8,
    marginBottom: 15,
    alignItems: "center",
  },
  adText: {
    color: "#000",
    fontWeight: "bold",
    fontSize: 16,
  },
  adLink: {
    color: "#000",
    textDecorationLine: "underline",
    marginTop: 5,
  },
  dealsSection: {
    marginTop: 10,
  },
});
