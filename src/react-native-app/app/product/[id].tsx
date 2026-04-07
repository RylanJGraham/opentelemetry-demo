// Copyright The OpenTelemetry Authors
// SPDX-License-Identifier: Apache-2.0
import { ThemedView } from "@/components/ThemedView";
import { ThemedText } from "@/components/ThemedText";
import { useLocalSearchParams, Stack } from "expo-router";
import { ActivityIndicator, Image, StyleSheet, ScrollView, View, Button } from "react-native";
import { useQuery } from "@tanstack/react-query";
import ApiGateway from "@/gateways/Api.gateway";
import { useCart } from "@/providers/Cart.provider";
import ProductList from "@/components/ProductList";
import Toast from "react-native-toast-message";
import { useState, useEffect } from "react";
import getFrontendProxyURL from "@/utils/Settings";

async function getImageURL(picture: string) {
  const proxyURL = await getFrontendProxyURL();
  return `${proxyURL}/images/products/${picture}`;
}

export default function ProductDetails() {
  const { id } = useLocalSearchParams();
  const productId = Array.isArray(id) ? id[0] : id;
  const { addItem } = useCart();

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

  const [imageSrc, setImageSrc] = useState<string>("");

  useEffect(() => {
    if (product?.picture) {
      getImageURL(product.picture)
        .then(setImageSrc)
        .catch((reason) => {
          console.warn("Failed to get image URL: ", reason);
        });
    }
  }, [product?.picture]);

  const onAddToCart = () => {
    if (product) {
      addItem({
        productId: product.id,
        quantity: 1,
      });
      Toast.show({
        type: "success",
        position: "bottom",
        text1: "Added to Cart!",
      });
    }
  };

  if (isLoading || !product) {
    return (
      <ThemedView style={styles.center}>
        <ActivityIndicator size="large" />
      </ThemedView>
    );
  }

  return (
    <ThemedView style={styles.container}>
      <Stack.Screen options={{ title: product.name }} />
      <ScrollView>
        {imageSrc ? <Image style={styles.image} source={{ uri: imageSrc }} /> : null}
        <View style={styles.content}>
          <ThemedText style={styles.title}>{product.name}</ThemedText>
          <ThemedText style={styles.price}>
            {product.priceUsd?.units}.{(product.priceUsd?.nanos || 0).toString().substring(0, 2)} USD
          </ThemedText>
          <ThemedText style={styles.description}>{product.description}</ThemedText>
          <View style={styles.buttonContainer}>
            <Button title="Add to Cart" onPress={onAddToCart} />
          </View>
        </View>

        {recommendations && recommendations.length > 0 && (
          <View style={styles.recommendationsContainer}>
            <ThemedText style={styles.sectionTitle}>You might also like</ThemedText>
            <ProductList productList={recommendations} />
          </View>
        )}
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
  image: {
    width: "100%",
    height: 300,
    resizeMode: "cover",
  },
  content: {
    padding: 20,
  },
  title: {
    fontSize: 24,
    fontWeight: "bold",
    marginBottom: 10,
  },
  price: {
    fontSize: 20,
    fontWeight: "600",
    color: "green",
    marginBottom: 15,
  },
  description: {
    fontSize: 16,
    lineHeight: 24,
  },
  buttonContainer: {
    marginTop: 20,
  },
  recommendationsContainer: {
    marginTop: 20,
    paddingTop: 20,
    borderTopWidth: 1,
    borderTopColor: "#ccc",
  },
  sectionTitle: {
    fontSize: 20,
    fontWeight: "bold",
    marginLeft: 20,
    marginBottom: 10,
  },
});
