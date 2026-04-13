// Copyright The OpenTelemetry Authors
// SPDX-License-Identifier: Apache-2.0
/**
 * Copied with modification from src/frontend/components/ProductCard/ProductCard.tsx
 */
import { Product } from "@/protos/demo";
import { ThemedView } from "@/components/ThemedView";
import { useMemo } from "react";
import { Image, Pressable, StyleSheet, View } from "react-native";
import { ThemedText } from "@/components/ThemedText";
import { useThemeColor } from "@/hooks/useThemeColor";
import { router } from "expo-router";

interface IProps {
  product: Product;
  onClickAdd: () => void;
}

const SAMPLE_IMAGES = [
  "https://images.unsplash.com/photo-1518709268805-4e9042af9f23?q=80&w=800&auto=format&fit=crop",
  "https://images.unsplash.com/photo-1614729939124-032f0b56c9ce?q=80&w=800&auto=format&fit=crop",
  "https://images.unsplash.com/photo-1541185933-ef5d8ed016c2?q=80&w=800&auto=format&fit=crop",
  "https://images.unsplash.com/photo-1628126235206-5260b9ea6441?q=80&w=800&auto=format&fit=crop",
  "https://images.unsplash.com/photo-1610296669228-602fa827fc1f?q=80&w=800&auto=format&fit=crop",
  "https://images.unsplash.com/photo-1635322966219-b75ed372fba1?q=80&w=800&auto=format&fit=crop",
  "https://images.unsplash.com/photo-1454789548928-9efd52dc4031?q=80&w=800&auto=format&fit=crop"
];

function getAwesomeImage(id: string) {
  if (!id) return SAMPLE_IMAGES[0];
  let hash = 0;
  for (let i = 0; i < id.length; i++) hash += id.charCodeAt(i);
  return SAMPLE_IMAGES[hash % SAMPLE_IMAGES.length];
}

const ProductCard = ({
  product: { id, picture, name, priceUsd = { currencyCode: "USD", units: 0, nanos: 0 } },
  onClickAdd,
}: IProps) => {
  const tint = useThemeColor({}, "tint");
  const styles = useMemo(() => getStyles(tint), [tint]);
  const imageSrc = getAwesomeImage(id);

  const price = (priceUsd?.units + priceUsd?.nanos / 100000000).toFixed(2);

  return (
    <Pressable onPress={() => router.push(`/product/${id}`)}>
      <ThemedView style={styles.container}>
        <View style={styles.imageContainer}>
          <Image style={styles.image} source={{ uri: imageSrc }} resizeMode="cover" />
          <View style={styles.badge}>
            <ThemedText style={styles.badgeText}>HOT</ThemedText>
          </View>
        </View>
        
        <View style={styles.productInfo}>
          <View>
            <ThemedText style={styles.name} numberOfLines={2}>{name}</ThemedText>
            <ThemedText style={styles.description} numberOfLines={1}>Premium Quality Space Gear</ThemedText>
          </View>
          
          <View style={styles.bottomRow}>
            <View style={styles.priceContainer}>
              <ThemedText style={styles.priceSymbol}>$</ThemedText>
              <ThemedText style={styles.price}>{price}</ThemedText>
            </View>
            
            <Pressable style={styles.addButton} onPress={onClickAdd}>
              <ThemedText style={styles.addButtonText}>Add 🛒</ThemedText>
            </Pressable>
          </View>
        </View>
      </ThemedView>
    </Pressable>
  );
};

function getStyles(tint: string) {
  return StyleSheet.create({
    container: {
      flexDirection: "row",
      marginHorizontal: 16,
      marginBottom: 16,
      backgroundColor: "rgba(30, 30, 35, 0.4)",
      borderRadius: 20,
      borderWidth: 1,
      borderColor: "rgba(255, 255, 255, 0.05)",
      overflow: "hidden",
    },
    imageContainer: {
      position: "relative",
    },
    image: {
      width: 140,
      height: 140,
      backgroundColor: "#1a1a1a",
    },
    badge: {
      position: "absolute",
      top: 10,
      left: 10,
      backgroundColor: "rgba(233, 69, 96, 0.9)",
      paddingHorizontal: 8,
      paddingVertical: 4,
      borderRadius: 6,
    },
    badgeText: {
      color: "white",
      fontSize: 10,
      fontWeight: "900",
      letterSpacing: 1,
    },
    productInfo: {
      flex: 1,
      padding: 16,
      justifyContent: "space-between",
    },
    name: {
      fontSize: 18,
      fontWeight: "700",
      color: "#ffffff",
      marginBottom: 4,
      lineHeight: 24,
    },
    description: {
      fontSize: 13,
      color: "#888888",
    },
    bottomRow: {
      flexDirection: "row",
      justifyContent: "space-between",
      alignItems: "flex-end",
    },
    priceContainer: {
      flexDirection: "row",
      alignItems: "baseline",
    },
    priceSymbol: {
      fontSize: 14,
      fontWeight: "600",
      color: "#ffffff",
      marginRight: 2,
    },
    price: {
      fontSize: 22,
      fontWeight: "800",
      color: "#ffffff",
    },
    addButton: {
      backgroundColor: "#4CAF50",
      paddingHorizontal: 16,
      paddingVertical: 10,
      borderRadius: 12,
      elevation: 2,
    },
    addButtonText: {
      color: "#ffffff",
      fontWeight: "700",
      fontSize: 14,
    },
  });
}

export default ProductCard;
