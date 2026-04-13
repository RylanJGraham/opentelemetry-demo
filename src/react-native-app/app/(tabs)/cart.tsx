// Copyright The OpenTelemetry Authors
// SPDX-License-Identifier: Apache-2.0
/**
 * Copied with modification from src/frontend/components/Cart/CartDetail.tsx
 */
import { router } from "expo-router";
import { ThemedView } from "@/components/ThemedView";
import { ThemedText } from "@/components/ThemedText";
import { Pressable, StyleSheet, View, Image } from "react-native";
import { useCart } from "@/providers/Cart.provider";
import CheckoutForm from "@/components/CheckoutForm";
import EmptyCart from "@/components/EmptyCart";
import { ThemedScrollView } from "@/components/ThemedScrollView";
import { useCallback, useMemo } from "react";
import { IFormData } from "@/components/CheckoutForm/CheckoutForm";
import Toast from "react-native-toast-message";
import SessionGateway from "@/gateways/Session.gateway";
import { useThemeColor } from "@/hooks/useThemeColor";

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

export default function Cart() {
  const tint = useThemeColor({}, "tint");
  const styles = useMemo(() => getStyles(tint), [tint]);
  const {
    cart: { items },
    updateItem,
    removeItem,
    emptyCart,
    placeOrder,
  } = useCart();

  const onEmptyCart = useCallback(() => {
    emptyCart();
    Toast.show({
      type: "success",
      position: "bottom",
      text1: "Your cart was emptied",
    });
  }, [emptyCart]);

  const onUpdateQuantity = (productId: string, newQuantity: number) => {
    updateItem(productId, newQuantity);
  };

  const onRemoveItem = (productId: string, productName: string) => {
    removeItem(productId);
    Toast.show({
      type: "info",
      position: "bottom",
      text1: `${productName} removed from cart`,
    });
  };

  const onPlaceOrder = useCallback(
    async ({
      email,
      state,
      streetAddress,
      country,
      city,
      zipCode,
      creditCardCvv,
      creditCardExpirationMonth,
      creditCardExpirationYear,
      creditCardNumber,
    }: IFormData) => {
      const { userId } = await SessionGateway.getSession();
      await placeOrder({
        userId,
        email,
        address: {
          streetAddress,
          state,
          country,
          city,
          zipCode,
        },
        // TODO simplify react native demo for now by hard-coding the selected currency
        userCurrency: "USD",
        creditCard: {
          creditCardNumber,
          creditCardCvv,
          creditCardExpirationYear,
          creditCardExpirationMonth,
        },
      });

      Toast.show({
        type: "success",
        position: "bottom",
        text1: "Your order is Complete!",
        text2: "We've sent you a confirmation email.",
      });

      router.replace("/");
    },
    [placeOrder],
  );

  const cartTotal = items.reduce((sum, item) => {
    const price = item.price?.units || item.product?.priceUsd?.units || 0;
    return sum + price * item.quantity;
  }, 0);

  if (!items.length) {
    return <EmptyCart />;
  }

  return (
    <ThemedView style={styles.container}>
      <ThemedScrollView>
        {/* Cart Items */}
        <View style={styles.itemsSection}>
          <ThemedText style={styles.sectionTitle}>
            Cart ({items.length} {items.length === 1 ? "item" : "items"})
          </ThemedText>
          
          {items.map((item) => (
            <View key={item.productId} style={styles.cartItem}>
              {/* Product Image */}
              <Image 
                source={{ uri: getAwesomeImage(item.product?.id || item.productId) }} 
                style={styles.itemImage}
                resizeMode="cover"
              />
              
              {/* Product Info */}
              <View style={styles.itemInfo}>
                <ThemedText style={styles.itemName} numberOfLines={2}>
                  {item.product?.name}
                </ThemedText>
                <ThemedText style={styles.itemPrice}>
                  ${(item.price?.units || item.product?.priceUsd?.units || 0).toFixed(2)}
                </ThemedText>
              </View>

              {/* Quantity Controls */}
              <View style={styles.quantitySection}>
                <View style={styles.quantityControls}>
                  <Pressable 
                    style={styles.quantityButton}
                    onPress={() => onUpdateQuantity(item.productId, item.quantity - 1)}
                  >
                    <ThemedText style={styles.quantityButtonText}>−</ThemedText>
                  </Pressable>
                  
                  <ThemedText style={styles.quantityText}>{item.quantity}</ThemedText>
                  
                  <Pressable 
                    style={styles.quantityButton}
                    onPress={() => onUpdateQuantity(item.productId, item.quantity + 1)}
                  >
                    <ThemedText style={styles.quantityButtonText}>+</ThemedText>
                  </Pressable>
                </View>
                
                <Pressable 
                  style={styles.removeButton}
                  onPress={() => onRemoveItem(item.productId, item.product?.name || "Item")}
                >
                  <ThemedText style={styles.removeButtonText}>Remove</ThemedText>
                </Pressable>
              </View>
            </View>
          ))}
        </View>

        {/* Cart Summary */}
        <View style={styles.summarySection}>
          <View style={styles.summaryRow}>
            <ThemedText>Subtotal</ThemedText>
            <ThemedText>${cartTotal.toFixed(2)}</ThemedText>
          </View>
          <View style={styles.summaryRow}>
            <ThemedText>Shipping</ThemedText>
            <ThemedText style={styles.freeShipping}>FREE</ThemedText>
          </View>
          <View style={[styles.summaryRow, styles.totalRow]}>
            <ThemedText style={styles.totalText}>Total</ThemedText>
            <ThemedText style={styles.totalAmount}>${cartTotal.toFixed(2)}</ThemedText>
          </View>
        </View>

        {/* Empty Cart Button */}
        <View style={styles.emptyCartContainer}>
          <Pressable style={styles.emptyCartButton} onPress={onEmptyCart}>
            <ThemedText style={styles.emptyCartText}>Empty Cart</ThemedText>
          </Pressable>
        </View>

        {/* Checkout Form */}
        <View style={styles.checkoutSection}>
          <ThemedText style={styles.sectionTitle}>Checkout</ThemedText>
          <CheckoutForm onSubmit={onPlaceOrder} />
        </View>
      </ThemedScrollView>
    </ThemedView>
  );
}

const getStyles = (tint: string) =>
  StyleSheet.create({
    container: {
      flex: 1,
    },
    itemsSection: {
      padding: 15,
    },
    sectionTitle: {
      fontSize: 20,
      fontWeight: "bold",
      marginBottom: 15,
    },
    cartItem: {
      flexDirection: "row",
      padding: 12,
      marginBottom: 12,
      backgroundColor: "rgba(128,128,128,0.1)",
      borderRadius: 8,
      alignItems: "center",
    },
    itemImage: {
      width: 60,
      height: 60,
      borderRadius: 8,
      backgroundColor: "#333",
    },
    itemInfo: {
      flex: 1,
      marginLeft: 12,
    },
    itemName: {
      fontSize: 14,
      marginBottom: 4,
    },
    itemPrice: {
      fontSize: 14,
      fontWeight: "bold",
      color: "#4CAF50",
    },
    quantitySection: {
      alignItems: "center",
    },
    quantityControls: {
      flexDirection: "row",
      alignItems: "center",
      backgroundColor: "rgba(128,128,128,0.2)",
      borderRadius: 8,
      marginBottom: 6,
    },
    quantityButton: {
      width: 32,
      height: 32,
      justifyContent: "center",
      alignItems: "center",
    },
    quantityButtonText: {
      fontSize: 18,
      fontWeight: "bold",
    },
    quantityText: {
      width: 30,
      textAlign: "center",
      fontSize: 14,
      fontWeight: "600",
    },
    removeButton: {
      paddingVertical: 4,
    },
    removeButtonText: {
      fontSize: 12,
      color: "#f44336",
    },
    summarySection: {
      padding: 15,
      backgroundColor: "rgba(128,128,128,0.05)",
      marginHorizontal: 15,
      borderRadius: 8,
      marginBottom: 15,
    },
    summaryRow: {
      flexDirection: "row",
      justifyContent: "space-between",
      marginBottom: 8,
    },
    totalRow: {
      marginTop: 8,
      paddingTop: 8,
      borderTopWidth: 1,
      borderTopColor: "rgba(128,128,128,0.3)",
    },
    totalText: {
      fontSize: 16,
      fontWeight: "bold",
    },
    totalAmount: {
      fontSize: 18,
      fontWeight: "bold",
      color: "#4CAF50",
    },
    freeShipping: {
      color: "#4CAF50",
    },
    emptyCartContainer: {
      alignItems: "flex-end",
      paddingHorizontal: 15,
      marginBottom: 15,
    },
    emptyCartButton: {
      backgroundColor: "#666",
      paddingVertical: 8,
      paddingHorizontal: 16,
      borderRadius: 6,
    },
    emptyCartText: {
      color: "white",
      fontSize: 12,
    },
    checkoutSection: {
      padding: 15,
      paddingBottom: 40,
    },
  });
