// Copyright The OpenTelemetry Authors
// SPDX-License-Identifier: Apache-2.0
import { ThemedView } from "@/components/ThemedView";
import { ThemedText } from "@/components/ThemedText";
import { StyleSheet, View, Pressable, ScrollView, Image } from "react-native";
import { useThemeColor } from "@/hooks/useThemeColor";
import { router } from "expo-router";
import { useCart } from "@/providers/Cart.provider";

export default function Profile() {
  const tint = useThemeColor({}, "tint");
  const { cart } = useCart();
  
  const menuItems = [
    { 
      icon: "📦", 
      title: "My Orders", 
      subtitle: "View order history & tracking",
      route: "/orders",
      badge: null 
    },
    { 
      icon: "🛒", 
      title: "Shopping Cart", 
      subtitle: `${cart.items.reduce((sum, i) => sum + i.quantity, 0)} items`,
      route: "/cart",
      badge: cart.items.length > 0 ? cart.items.reduce((sum, i) => sum + i.quantity, 0).toString() : null 
    },
    { 
      icon: "💰", 
      title: "Wallet & Gift Cards", 
      subtitle: "$450.00 available",
      route: "/wallet",
      badge: null 
    },
    { 
      icon: "🏷️", 
      title: "Deals & Offers", 
      subtitle: "Special discounts for you",
      route: "/deals",
      badge: "NEW" 
    },
    { 
      icon: "❤️", 
      title: "Wishlist", 
      subtitle: "12 saved items",
      route: "/",
      badge: null 
    },
    { 
      icon: "📍", 
      title: "Saved Addresses", 
      subtitle: "Manage delivery locations",
      route: null,
      badge: null 
    },
    { 
      icon: "💳", 
      title: "Payment Methods", 
      subtitle: "Visa •••• 4242",
      route: "/wallet",
      badge: null 
    },
    { 
      icon: "🔔", 
      title: "Notifications", 
      subtitle: "3 unread messages",
      route: "/notifications",
      badge: "3" 
    },
    { 
      icon: "❓", 
      title: "Help & Support", 
      subtitle: "FAQs, contact us",
      route: "/support",
      badge: null 
    },
  ];

  const stats = [
    { label: "Orders", value: "12" },
    { label: "Wishlist", value: "8" },
    { label: "Reviews", value: "5" },
    { label: "Points", value: "1,240" },
  ];

  return (
    <ThemedView style={styles.container}>
      <ScrollView showsVerticalScrollIndicator={false}>
        {/* Profile Header */}
        <View style={styles.header}>
          <View style={styles.avatarContainer}>
            <View style={styles.avatar}>
              <ThemedText style={styles.avatarText}>👨‍🚀</ThemedText>
            </View>
            <View style={styles.statusBadge}>
              <ThemedText style={styles.statusText}>★</ThemedText>
            </View>
          </View>
          
          <ThemedText style={styles.name}>Alex Explorer</ThemedText>
          <ThemedText style={styles.email}>alex@example.com</ThemedText>
          
          <View style={styles.memberBadge}>
            <ThemedText style={styles.memberText}>⭐ Premium Member</ThemedText>
          </View>
        </View>

        {/* Stats Row */}
        <View style={[styles.statsContainer, { borderColor: tint }]}>
          {stats.map((stat, index) => (
            <View key={stat.label} style={styles.statItem}>
              <ThemedText style={styles.statValue}>{stat.value}</ThemedText>
              <ThemedText style={styles.statLabel}>{stat.label}</ThemedText>
            </View>
          ))}
        </View>

        {/* Menu Items */}
        <View style={styles.menuSection}>
          {menuItems.map((item, index) => (
            <Pressable 
              key={item.title}
              style={[styles.menuItem, { borderColor: tint }]}
              onPress={() => item.route && router.push(item.route)}
            >
              <ThemedText style={styles.menuIcon}>{item.icon}</ThemedText>
              <View style={styles.menuInfo}>
                <ThemedText style={styles.menuTitle}>{item.title}</ThemedText>
                <ThemedText style={styles.menuSubtitle}>{item.subtitle}</ThemedText>
              </View>
              {item.badge && (
                <View style={[styles.badge, item.badge === "NEW" && styles.newBadge]}>
                  <ThemedText style={[styles.badgeText, item.badge === "NEW" && styles.newBadgeText]}>
                    {item.badge}
                  </ThemedText>
                </View>
              )}
              <ThemedText style={styles.chevron}>›</ThemedText>
            </Pressable>
          ))}
        </View>

        {/* Account Actions */}
        <View style={styles.actionsSection}>
          <Pressable style={[styles.actionButton, styles.editButton]}>
            <ThemedText style={styles.editButtonText}>✏️ Edit Profile</ThemedText>
          </Pressable>
          
          <Pressable style={[styles.actionButton, styles.logoutButton]}>
            <ThemedText style={styles.logoutButtonText}>🚪 Logout</ThemedText>
          </Pressable>
        </View>

        {/* App Version */}
        <View style={styles.footer}>
          <ThemedText style={styles.version}>SpaceShop v2.0.1</ThemedText>
          <ThemedText style={styles.legal}>Privacy Policy • Terms of Service</ThemedText>
        </View>
      </ScrollView>
    </ThemedView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
  },
  header: {
    alignItems: "center",
    paddingVertical: 30,
    paddingHorizontal: 20,
  },
  avatarContainer: {
    position: "relative",
    marginBottom: 16,
  },
  avatar: {
    width: 100,
    height: 100,
    borderRadius: 50,
    backgroundColor: "#1e3a5f",
    justifyContent: "center",
    alignItems: "center",
  },
  avatarText: {
    fontSize: 50,
  },
  statusBadge: {
    position: "absolute",
    bottom: 0,
    right: 0,
    backgroundColor: "#FFD700",
    width: 32,
    height: 32,
    borderRadius: 16,
    justifyContent: "center",
    alignItems: "center",
    borderWidth: 3,
    borderColor: "#000",
  },
  statusText: {
    fontSize: 16,
  },
  name: {
    fontSize: 24,
    fontWeight: "bold",
  },
  email: {
    fontSize: 14,
    color: "#888",
    marginTop: 4,
  },
  memberBadge: {
    backgroundColor: "rgba(255,215,0,0.2)",
    paddingHorizontal: 12,
    paddingVertical: 6,
    borderRadius: 16,
    marginTop: 12,
  },
  memberText: {
    color: "#FFD700",
    fontWeight: "600",
    fontSize: 12,
  },
  statsContainer: {
    flexDirection: "row",
    justifyContent: "space-around",
    paddingVertical: 20,
    marginHorizontal: 20,
    marginBottom: 20,
    borderTopWidth: 1,
    borderBottomWidth: 1,
  },
  statItem: {
    alignItems: "center",
  },
  statValue: {
    fontSize: 20,
    fontWeight: "bold",
  },
  statLabel: {
    fontSize: 12,
    color: "#888",
    marginTop: 4,
  },
  menuSection: {
    paddingHorizontal: 15,
  },
  menuItem: {
    flexDirection: "row",
    alignItems: "center",
    paddingVertical: 14,
    paddingHorizontal: 12,
    borderBottomWidth: 1,
  },
  menuIcon: {
    fontSize: 22,
    width: 36,
  },
  menuInfo: {
    flex: 1,
  },
  menuTitle: {
    fontSize: 15,
    fontWeight: "500",
  },
  menuSubtitle: {
    fontSize: 12,
    color: "#888",
    marginTop: 2,
  },
  badge: {
    backgroundColor: "#f44336",
    paddingHorizontal: 8,
    paddingVertical: 3,
    borderRadius: 12,
    marginRight: 8,
  },
  badgeText: {
    color: "#fff",
    fontSize: 10,
    fontWeight: "bold",
  },
  newBadge: {
    backgroundColor: "#4CAF50",
  },
  newBadgeText: {
    fontSize: 9,
  },
  chevron: {
    fontSize: 20,
    color: "#888",
  },
  actionsSection: {
    padding: 20,
    gap: 10,
  },
  actionButton: {
    paddingVertical: 14,
    borderRadius: 10,
    alignItems: "center",
  },
  editButton: {
    backgroundColor: "rgba(128,128,128,0.2)",
  },
  editButtonText: {
    fontWeight: "600",
  },
  logoutButton: {
    backgroundColor: "rgba(244,67,54,0.1)",
  },
  logoutButtonText: {
    color: "#f44336",
    fontWeight: "600",
  },
  footer: {
    alignItems: "center",
    paddingVertical: 20,
  },
  version: {
    fontSize: 12,
    color: "#666",
  },
  legal: {
    fontSize: 11,
    color: "#888",
    marginTop: 6,
  },
});
