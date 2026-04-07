// Copyright The OpenTelemetry Authors
// SPDX-License-Identifier: Apache-2.0
import { ThemedView } from "@/components/ThemedView";
import { ThemedText } from "@/components/ThemedText";
import { StyleSheet, View, Button, ScrollView } from "react-native";
import { useThemeColor } from "@/hooks/useThemeColor";

export default function Profile() {
  const tint = useThemeColor({}, "tint");
  
  return (
    <ThemedView style={styles.container}>
      <ScrollView>
        <View style={styles.header}>
          <ThemedText style={styles.title}>My Profile</ThemedText>
        </View>
        <View style={styles.section}>
          <ThemedText style={styles.sectionTitle}>User Info</ThemedText>
          <ThemedText>Name: Alex Explorer</ThemedText>
          <ThemedText>Email: alex@example.com</ThemedText>
          <ThemedText>Membership: Premium</ThemedText>
        </View>
        
        <View style={styles.section}>
          <ThemedText style={styles.sectionTitle}>Saved Addresses</ThemedText>
          <View style={[styles.card, { borderColor: tint }]}>
            <ThemedText style={styles.bold}>Home</ThemedText>
            <ThemedText>123 Explorer Lane</ThemedText>
            <ThemedText>Tech City, TX 75001</ThemedText>
          </View>
        </View>

        <View style={styles.section}>
          <ThemedText style={styles.sectionTitle}>Payment Methods</ThemedText>
          <View style={[styles.card, { borderColor: tint }]}>
            <ThemedText style={styles.bold}>Visa ending in 4242</ThemedText>
            <ThemedText>Expires 12/28</ThemedText>
          </View>
        </View>
        
        <View style={styles.buttonContainer}>
          <Button title="Edit Profile" onPress={() => {}} />
          <View style={{ height: 10 }} />
          <Button title="Logout" color="red" onPress={() => {}} />
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
  header: {
    marginBottom: 20,
  },
  title: {
    fontSize: 28,
    fontWeight: "bold",
  },
  section: {
    marginBottom: 25,
  },
  sectionTitle: {
    fontSize: 20,
    fontWeight: "600",
    marginBottom: 10,
  },
  card: {
    borderWidth: 1,
    borderRadius: 8,
    padding: 15,
    marginBottom: 10,
  },
  bold: {
    fontWeight: "bold",
    marginBottom: 5,
  },
  buttonContainer: {
    marginTop: 20,
    marginBottom: 40,
  },
});
