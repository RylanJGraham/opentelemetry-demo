// Copyright The OpenTelemetry Authors
// SPDX-License-Identifier: Apache-2.0
import { ThemedView } from "@/components/ThemedView";
import { ThemedText } from "@/components/ThemedText";
import { StyleSheet, View, ScrollView, Pressable, Image } from "react-native";
import { useThemeColor } from "@/hooks/useThemeColor";
import { useQuery } from "@tanstack/react-query";
import ApiGateway from "@/gateways/Api.gateway";
import { router } from "expo-router";
import { useState } from "react";

interface OrderItem {
  productId: string;
  quantity: number;
  product: {
    id: string;
    name: string;
    picture: string;
    priceUsd: { units: number; nanos: number };
  };
}

interface Order {
  id: string;
  date: string;
  total: { units: number; nanos: number; currencyCode: string };
  status: "Delivered" | "Shipped" | "Processing";
  items: OrderItem[];
}

export default function Orders() {
  const tint = useThemeColor({}, "tint");
  const [expandedOrder, setExpandedOrder] = useState<string | null>(null);
  
  const { data: orders = [], isLoading } = useQuery<Order[]>({
    queryKey: ["orders"],
    queryFn: () => ApiGateway.getOrders(),
  });

  const formatPrice = (money: { units: number; nanos: number }) => {
    const dollars = money.units;
    const cents = Math.floor(money.nanos / 10000000);
    return `$${dollars}.${cents.toString().padStart(2, "0")}`;
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case "Delivered":
        return "#4CAF50";
      case "Shipped":
        return "#2196F3";
      case "Processing":
        return "#FF9800";
      default:
        return "#888";
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case "Delivered":
        return "✅";
      case "Shipped":
        return "🚚";
      case "Processing":
        return "⏳";
      default:
        return "📦";
    }
  };

  if (isLoading) {
    return (
      <ThemedView style={styles.container}>
        <ThemedText>Loading orders...</ThemedText>
      </ThemedView>
    );
  }

  return (
    <ThemedView style={styles.container}>
      <ScrollView showsVerticalScrollIndicator={false}>
        <View style={styles.header}>
          <ThemedText style={styles.title}>📦 Order History</ThemedText>
          <ThemedText style={styles.subtitle}>
            {orders.length} {orders.length === 1 ? "order" : "orders"} placed
          </ThemedText>
        </View>

        {orders.map((order) => {
          const isExpanded = expandedOrder === order.id;
          const itemCount = order.items.reduce((sum, item) => sum + item.quantity, 0);

          return (
            <View key={order.id} style={[styles.orderCard, { borderColor: tint }]}>
              {/* Order Header */}
              <Pressable 
                style={styles.orderHeader}
                onPress={() => setExpandedOrder(isExpanded ? null : order.id)}
              >
                <View style={styles.orderInfo}>
                  <ThemedText style={styles.orderId}>{order.id}</ThemedText>
                  <ThemedText style={styles.orderDate}>
                    Placed on {new Date(order.date).toLocaleDateString("en-US", {
                      year: "numeric",
                      month: "long",
                      day: "numeric",
                    })}
                  </ThemedText>
                </View>
                <View style={styles.orderMeta}>
                  <View style={[styles.statusBadge, { backgroundColor: getStatusColor(order.status) }]}>
                    <ThemedText style={styles.statusText}>
                      {getStatusIcon(order.status)} {order.status}
                    </ThemedText>
                  </View>
                  <ThemedText style={styles.orderTotal}>
                    {formatPrice(order.total)}
                  </ThemedText>
                </View>
              </Pressable>

              {/* Order Summary */}
              <View style={styles.orderSummary}>
                <ThemedText style={styles.itemCount}>
                  {itemCount} {itemCount === 1 ? "item" : "items"}
                </ThemedText>
                <ThemedText style={styles.expandHint}>
                  {isExpanded ? "▼ Tap to collapse" : "▶ Tap to view details"}
                </ThemedText>
              </View>

              {/* Expanded Order Details */}
              {isExpanded && (
                <View style={styles.orderDetails}>
                  <View style={[styles.divider, { backgroundColor: tint }]} />
                  
                  {/* Tracking Info */}
                  {order.status !== "Processing" && (
                    <View style={styles.trackingSection}>
                      <ThemedText style={styles.sectionLabel}>Tracking</ThemedText>
                      <ThemedText style={styles.trackingNumber}>
                        TRACK-{Math.random().toString(36).substr(2, 9).toUpperCase()}
                      </ThemedText>
                    </View>
                  )}

                  {/* Order Items */}
                  <ThemedText style={styles.sectionLabel}>Items</ThemedText>
                  {order.items.map((item) => (
                    <View key={item.productId} style={styles.itemRow}>
                      <Image 
                        source={{ uri: item.product.picture }} 
                        style={styles.itemImage}
                      />
                      <View style={styles.itemDetails}>
                        <ThemedText style={styles.itemName} numberOfLines={1}>
                          {item.product.name}
                        </ThemedText>
                        <ThemedText style={styles.itemPrice}>
                          Qty: {item.quantity} × {formatPrice(item.product.priceUsd)}
                        </ThemedText>
                      </View>
                      <ThemedText style={styles.itemTotal}>
                        {formatPrice({
                          units: item.product.priceUsd.units * item.quantity,
                          nanos: item.product.priceUsd.nanos * item.quantity,
                        })}
                      </ThemedText>
                    </View>
                  ))}

                  {/* Order Actions */}
                  <View style={styles.actions}>
                    {order.status === "Delivered" && (
                      <Pressable style={styles.reorderButton}>
                        <ThemedText style={styles.reorderText}>🔄 Reorder</ThemedText>
                      </Pressable>
                    )}
                    <Pressable 
                      style={styles.supportButton}
                      onPress={() => router.push("/support")}
                    >
                      <ThemedText style={styles.supportText}>❓ Need Help?</ThemedText>
                    </Pressable>
                  </View>
                </View>
              )}
            </View>
          );
        })}

        {/* Empty State */}
        {orders.length === 0 && (
          <View style={styles.emptyState}>
            <ThemedText style={styles.emptyIcon}>📭</ThemedText>
            <ThemedText style={styles.emptyTitle}>No orders yet</ThemedText>
            <ThemedText style={styles.emptySubtitle}>
              Start shopping to see your orders here
            </ThemedText>
            <Pressable 
              style={styles.shopButton}
              onPress={() => router.push("/")}
            >
              <ThemedText style={styles.shopButtonText}>Browse Products</ThemedText>
            </Pressable>
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
    padding: 15,
  },
  header: {
    marginBottom: 20,
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
  orderCard: {
    borderWidth: 1,
    borderRadius: 12,
    marginBottom: 16,
    overflow: "hidden",
    backgroundColor: "rgba(128,128,128,0.05)",
  },
  orderHeader: {
    flexDirection: "row",
    justifyContent: "space-between",
    padding: 16,
  },
  orderInfo: {
    flex: 1,
  },
  orderId: {
    fontSize: 16,
    fontWeight: "bold",
  },
  orderDate: {
    fontSize: 12,
    color: "#888",
    marginTop: 4,
  },
  orderMeta: {
    alignItems: "flex-end",
  },
  statusBadge: {
    paddingHorizontal: 10,
    paddingVertical: 4,
    borderRadius: 12,
    marginBottom: 6,
  },
  statusText: {
    color: "#fff",
    fontSize: 11,
    fontWeight: "600",
  },
  orderTotal: {
    fontSize: 16,
    fontWeight: "bold",
  },
  orderSummary: {
    flexDirection: "row",
    justifyContent: "space-between",
    paddingHorizontal: 16,
    paddingBottom: 12,
  },
  itemCount: {
    fontSize: 13,
    color: "#888",
  },
  expandHint: {
    fontSize: 12,
    color: "#666",
  },
  orderDetails: {
    paddingHorizontal: 16,
    paddingBottom: 16,
  },
  divider: {
    height: 1,
    marginBottom: 12,
  },
  trackingSection: {
    marginBottom: 16,
  },
  sectionLabel: {
    fontSize: 12,
    fontWeight: "600",
    color: "#888",
    textTransform: "uppercase",
    marginBottom: 6,
  },
  trackingNumber: {
    fontSize: 14,
    fontFamily: "monospace",
  },
  itemRow: {
    flexDirection: "row",
    alignItems: "center",
    paddingVertical: 10,
    borderBottomWidth: 1,
    borderBottomColor: "rgba(128,128,128,0.1)",
  },
  itemImage: {
    width: 50,
    height: 50,
    borderRadius: 8,
    backgroundColor: "#333",
  },
  itemDetails: {
    flex: 1,
    marginLeft: 12,
  },
  itemName: {
    fontSize: 14,
  },
  itemPrice: {
    fontSize: 12,
    color: "#888",
    marginTop: 2,
  },
  itemTotal: {
    fontSize: 14,
    fontWeight: "600",
  },
  actions: {
    flexDirection: "row",
    marginTop: 16,
    gap: 10,
  },
  reorderButton: {
    flex: 1,
    backgroundColor: "#4CAF50",
    paddingVertical: 12,
    borderRadius: 8,
    alignItems: "center",
  },
  reorderText: {
    color: "#fff",
    fontWeight: "600",
  },
  supportButton: {
    flex: 1,
    backgroundColor: "rgba(128,128,128,0.2)",
    paddingVertical: 12,
    borderRadius: 8,
    alignItems: "center",
  },
  supportText: {
    fontWeight: "600",
  },
  emptyState: {
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
    marginBottom: 24,
    textAlign: "center",
  },
  shopButton: {
    backgroundColor: "#4CAF50",
    paddingHorizontal: 24,
    paddingVertical: 14,
    borderRadius: 8,
  },
  shopButtonText: {
    color: "#fff",
    fontWeight: "600",
    fontSize: 16,
  },
  bottomPadding: {
    height: 40,
  },
});
