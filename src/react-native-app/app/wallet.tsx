// Copyright The OpenTelemetry Authors
// SPDX-License-Identifier: Apache-2.0
import { ThemedView } from "@/components/ThemedView";
import { ThemedText } from "@/components/ThemedText";
import { StyleSheet, View, ScrollView, Button } from "react-native";
import { useThemeColor } from "@/hooks/useThemeColor";
import Toast from "react-native-toast-message";

export default function Wallet() {
  const tint = useThemeColor({}, "tint");
  
  const handleRedeem = () => {
    Toast.show({
      type: "success",
      text1: "Gift card applied!",
    });
  };

  return (
    <ThemedView style={styles.container}>
      <ScrollView>
        <ThemedText style={styles.title}>My Wallet</ThemedText>
        
        <View style={styles.balanceCard}>
          <ThemedText style={styles.balanceLabel}>Current Store Credit</ThemedText>
          <ThemedText style={styles.balanceAmount}>$450.00</ThemedText>
        </View>

        <View style={styles.section}>
          <ThemedText style={styles.subtitle}>Redeem Gift Card</ThemedText>
          <View style={[styles.card, { borderColor: tint }]}>
            <ThemedText style={styles.instructions}>Enter your 16-digit gift card code below to add funds your wallet.</ThemedText>
            <View style={styles.buttonContainer}>
               <Button title="Scan Code" onPress={() => {}} />
               <View style={{ width: 10 }} />
               <Button title="Apply Manually" onPress={handleRedeem} />
            </View>
          </View>
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
    fontWeight: "600",
    marginBottom: 10,
  },
  balanceCard: {
    backgroundColor: "green",
    padding: 25,
    borderRadius: 12,
    alignItems: "center",
    marginBottom: 30,
  },
  balanceLabel: {
    color: "#fff",
    fontSize: 18,
    opacity: 0.9,
  },
  balanceAmount: {
    color: "#fff",
    fontSize: 36,
    fontWeight: "bold",
    marginTop: 10,
  },
  section: {
    marginBottom: 25,
  },
  card: {
    borderWidth: 1,
    borderRadius: 8,
    padding: 15,
  },
  instructions: {
    marginBottom: 15,
    lineHeight: 22,
  },
  buttonContainer: {
    flexDirection: "row",
    justifyContent: "space-between",
  },
});
