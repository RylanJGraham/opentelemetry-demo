// Copyright The OpenTelemetry Authors
// SPDX-License-Identifier: Apache-2.0
import { ThemedView } from "@/components/ThemedView";
import { ThemedText } from "@/components/ThemedText";
import { StyleSheet, View, ScrollView } from "react-native";

export default function Notifications() {
  const notifications = [
    { id: 1, title: "Order Shipped!", desc: "Your order ORD-9912 is on the way.", time: "2 hours ago" },
    { id: 2, title: "Flash Sale!", desc: "Save 50% on all telescopes today.", time: "1 day ago" },
    { id: 3, title: "Welcome back!", desc: "Check out the new arrivals.", time: "3 days ago" },
  ];

  return (
    <ThemedView style={styles.container}>
      <ScrollView>
        <ThemedText style={styles.title}>Notifications</ThemedText>
        
        {notifications.map((notif) => (
          <View key={notif.id} style={styles.notificationCard}>
            <View style={styles.row}>
              <ThemedText style={styles.notifTitle}>{notif.title}</ThemedText>
              <ThemedText style={styles.time}>{notif.time}</ThemedText>
            </View>
            <ThemedText>{notif.desc}</ThemedText>
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
  notificationCard: {
    backgroundColor: "rgba(128,128,128,0.15)",
    padding: 15,
    borderRadius: 8,
    marginBottom: 15,
  },
  row: {
    flexDirection: "row",
    justifyContent: "space-between",
    marginBottom: 5,
  },
  notifTitle: {
    fontWeight: "bold",
    fontSize: 16,
  },
  time: {
    color: "#888",
    fontSize: 12,
  },
});
