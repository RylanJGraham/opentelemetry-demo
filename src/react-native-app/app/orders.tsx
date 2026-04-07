// Copyright The OpenTelemetry Authors
// SPDX-License-Identifier: Apache-2.0
import { ThemedView } from "@/components/ThemedView";
import { ThemedText } from "@/components/ThemedText";
import { StyleSheet, View, ScrollView } from "react-native";
import { useThemeColor } from "@/hooks/useThemeColor";

export default function Orders() {
  const tint = useThemeColor({}, "tint");
  
  const mockOrders = [
    { id: "ORD-9912", date: "2026-03-15", total: "$124.99", status: "Delivered" },
    { id: "ORD-9945", date: "2026-04-01", total: "$55.00", status: "Shipped" },
    { id: "ORD-9988", date: "2026-04-05", total: "$210.50", status: "Processing" },
  ];

  return (
    <ThemedView style={styles.container}>
      <ScrollView>
        <ThemedText style={styles.title}>Order History</ThemedText>
        {mockOrders.map((order) => (
          <View key={order.id} style={[styles.card, { borderColor: tint }]}>
            <View style={styles.row}>
              <ThemedText style={styles.bold}>Order {order.id}</ThemedText>
              <ThemedText style={getStatusStyle(order.status)}>{order.status}</ThemedText>
            </View>
            <View style={styles.row}>
              <ThemedText>{order.date}</ThemedText>
              <ThemedText style={styles.bold}>{order.total}</ThemedText>
            </View>
          </View>
        ))}
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
  card: {
    borderWidth: 1,
    borderRadius: 8,
    padding: 15,
    marginBottom: 15,
  },
  row: {
    flexDirection: "row",
    justifyContent: "space-between",
    marginBottom: 10,
  },
  bold: {
    fontWeight: "bold",
  },
});

const getStatusStyle = (status: string) => ({
  color: status === "Delivered" ? "green" : status === "Shipped" ? "blue" : "orange",
  fontWeight: "600" as const,
});
