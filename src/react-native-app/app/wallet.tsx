// Copyright The OpenTelemetry Authors
// SPDX-License-Identifier: Apache-2.0
import { ThemedView } from "@/components/ThemedView";
import { ThemedText } from "@/components/ThemedText";
import { StyleSheet, View, ScrollView, Pressable, TextInput, Modal } from "react-native";
import { useThemeColor } from "@/hooks/useThemeColor";
import { useState } from "react";
import Toast from "react-native-toast-message";

interface Transaction {
  id: string;
  date: string;
  description: string;
  amount: number;
  type: "credit" | "debit";
}

const MOCK_TRANSACTIONS: Transaction[] = [
  { id: "1", date: "2026-04-05", description: "Gift Card Redemption", amount: 100, type: "credit" },
  { id: "2", date: "2026-04-03", description: "Purchase - Space Station LEGO Set", amount: -79.99, type: "debit" },
  { id: "3", date: "2026-03-28", description: "Refund - Astronaut Figurine", amount: 25.99, type: "credit" },
  { id: "4", date: "2026-03-15", description: "Gift Card Redemption", amount: 50, type: "credit" },
  { id: "5", date: "2026-03-10", description: "Purchase - NASA Hoodie", amount: -55, type: "debit" },
];

export default function Wallet() {
  const tint = useThemeColor({}, "tint");
  const [balance, setBalance] = useState(450.00);
  const [giftCardCode, setGiftCardCode] = useState("");
  const [showRedeemModal, setShowRedeemModal] = useState(false);
  const [transactions, setTransactions] = useState(MOCK_TRANSACTIONS);

  const handleRedeem = () => {
    if (giftCardCode.length < 8) {
      Toast.show({
        type: "error",
        text1: "Invalid code",
        text2: "Please enter a valid gift card code",
      });
      return;
    }

    // Simulate redemption
    const amount = Math.floor(Math.random() * 50) + 25;
    setBalance(prev => prev + amount);
    
    const newTransaction: Transaction = {
      id: Date.now().toString(),
      date: new Date().toISOString().split("T")[0],
      description: "Gift Card Redemption",
      amount,
      type: "credit",
    };
    
    setTransactions(prev => [newTransaction, ...prev]);
    setGiftCardCode("");
    setShowRedeemModal(false);
    
    Toast.show({
      type: "success",
      text1: "Gift card applied!",
      text2: `$${amount.toFixed(2)} added to your balance`,
    });
  };

  const formatDate = (dateStr: string) => {
    const date = new Date(dateStr);
    return date.toLocaleDateString("en-US", { month: "short", day: "numeric" });
  };

  return (
    <ThemedView style={styles.container}>
      <ScrollView showsVerticalScrollIndicator={false}>
        {/* Balance Card */}
        <View style={styles.balanceCard}>
          <ThemedText style={styles.balanceLabel}>Available Balance</ThemedText>
          <ThemedText style={styles.balanceAmount}>${balance.toFixed(2)}</ThemedText>
          <View style={styles.balanceActions}>
            <Pressable 
              style={styles.actionButton}
              onPress={() => setShowRedeemModal(true)}
            >
              <ThemedText style={styles.actionButtonText}>🎁 Redeem</ThemedText>
            </Pressable>
            <Pressable style={styles.actionButton}>
              <ThemedText style={styles.actionButtonText}>➕ Add Funds</ThemedText>
            </Pressable>
          </View>
        </View>

        {/* Quick Stats */}
        <View style={styles.statsContainer}>
          <View style={styles.statBox}>
            <ThemedText style={styles.statValue}>{transactions.filter(t => t.type === "credit").length}</ThemedText>
            <ThemedText style={styles.statLabel}>Credits</ThemedText>
          </View>
          <View style={styles.statBox}>
            <ThemedText style={styles.statValue}>
              ${Math.abs(transactions.filter(t => t.type === "debit").reduce((sum, t) => sum + t.amount, 0)).toFixed(0)}
            </ThemedText>
            <ThemedText style={styles.statLabel}>Spent</ThemedText>
          </View>
          <View style={styles.statBox}>
            <ThemedText style={styles.statValue}>★</ThemedText>
            <ThemedText style={styles.statLabel}>Premium</ThemedText>
          </View>
        </View>

        {/* Gift Cards Section */}
        <View style={styles.section}>
          <ThemedText style={styles.sectionTitle}>Active Gift Cards</ThemedText>
          <View style={[styles.giftCard, { borderColor: tint }]}>
            <View style={styles.giftCardHeader}>
              <ThemedText style={styles.giftCardAmount}>$100.00</ThemedText>
              <ThemedText style={styles.giftCardStatus}>Active</ThemedText>
            </View>
            <ThemedText style={styles.giftCardCode}>•••• •••• •••• 4521</ThemedText>
            <ThemedText style={styles.giftCardExpiry}>Expires 12/2026</ThemedText>
          </View>
        </View>

        {/* Transaction History */}
        <View style={styles.section}>
          <ThemedText style={styles.sectionTitle}>Recent Transactions</ThemedText>
          {transactions.map((transaction) => (
            <View key={transaction.id} style={[styles.transaction, { borderColor: tint }]}>
              <View style={styles.transactionInfo}>
                <ThemedText style={styles.transactionDate}>
                  {formatDate(transaction.date)}
                </ThemedText>
                <ThemedText style={styles.transactionDesc} numberOfLines={1}>
                  {transaction.description}
                </ThemedText>
              </View>
              <ThemedText 
                style={[
                  styles.transactionAmount,
                  transaction.type === "credit" ? styles.credit : styles.debit
                ]}
              >
                {transaction.type === "credit" ? "+" : ""}${Math.abs(transaction.amount).toFixed(2)}
              </ThemedText>
            </View>
          ))}
        </View>

        {/* Payment Methods */}
        <View style={styles.section}>
          <ThemedText style={styles.sectionTitle}>Payment Methods</ThemedText>
          <View style={[styles.paymentMethod, { borderColor: tint }]}>
            <ThemedText style={styles.cardIcon}>💳</ThemedText>
            <View style={styles.cardInfo}>
              <ThemedText style={styles.cardName}>Visa ending in 4242</ThemedText>
              <ThemedText style={styles.cardExpiry}>Expires 12/2028</ThemedText>
            </View>
            <View style={styles.defaultBadge}>
              <ThemedText style={styles.defaultText}>Default</ThemedText>
            </View>
          </View>
          <Pressable style={styles.addCardButton}>
            <ThemedText style={styles.addCardText}>+ Add Payment Method</ThemedText>
          </Pressable>
        </View>

        <View style={styles.bottomPadding} />
      </ScrollView>

      {/* Redeem Modal */}
      <Modal
        visible={showRedeemModal}
        transparent
        animationType="slide"
        onRequestClose={() => setShowRedeemModal(false)}
      >
        <View style={styles.modalOverlay}>
          <View style={styles.modalContent}>
            <ThemedText style={styles.modalTitle}>🎁 Redeem Gift Card</ThemedText>
            <ThemedText style={styles.modalSubtitle}>
              Enter your 16-digit gift card code
            </ThemedText>
            <TextInput
              style={styles.codeInput}
              value={giftCardCode}
              onChangeText={setGiftCardCode}
              placeholder="XXXX-XXXX-XXXX-XXXX"
              placeholderTextColor="#666"
              maxLength={19}
              keyboardType="number-pad"
            />
            <View style={styles.modalButtons}>
              <Pressable 
                style={[styles.modalButton, styles.cancelButton]}
                onPress={() => setShowRedeemModal(false)}
              >
                <ThemedText>Cancel</ThemedText>
              </Pressable>
              <Pressable 
                style={[styles.modalButton, styles.redeemButton]}
                onPress={handleRedeem}
              >
                <ThemedText style={styles.redeemButtonText}>Redeem</ThemedText>
              </Pressable>
            </View>
          </View>
        </View>
      </Modal>
    </ThemedView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    padding: 15,
  },
  balanceCard: {
    backgroundColor: "#4CAF50",
    padding: 25,
    borderRadius: 16,
    alignItems: "center",
    marginBottom: 20,
  },
  balanceLabel: {
    color: "#fff",
    fontSize: 14,
    opacity: 0.9,
  },
  balanceAmount: {
    color: "#fff",
    fontSize: 42,
    fontWeight: "bold",
    marginVertical: 10,
  },
  balanceActions: {
    flexDirection: "row",
    gap: 12,
    marginTop: 10,
  },
  actionButton: {
    backgroundColor: "rgba(255,255,255,0.2)",
    paddingHorizontal: 16,
    paddingVertical: 10,
    borderRadius: 8,
  },
  actionButtonText: {
    color: "#fff",
    fontWeight: "600",
  },
  statsContainer: {
    flexDirection: "row",
    gap: 10,
    marginBottom: 25,
  },
  statBox: {
    flex: 1,
    backgroundColor: "rgba(128,128,128,0.1)",
    padding: 15,
    borderRadius: 12,
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
  section: {
    marginBottom: 25,
  },
  sectionTitle: {
    fontSize: 18,
    fontWeight: "bold",
    marginBottom: 12,
  },
  giftCard: {
    borderWidth: 1,
    borderStyle: "dashed",
    borderRadius: 12,
    padding: 16,
    backgroundColor: "rgba(76,175,80,0.1)",
  },
  giftCardHeader: {
    flexDirection: "row",
    justifyContent: "space-between",
    marginBottom: 8,
  },
  giftCardAmount: {
    fontSize: 20,
    fontWeight: "bold",
    color: "#4CAF50",
  },
  giftCardStatus: {
    fontSize: 12,
    color: "#4CAF50",
    fontWeight: "600",
  },
  giftCardCode: {
    fontSize: 14,
    fontFamily: "monospace",
    marginBottom: 4,
  },
  giftCardExpiry: {
    fontSize: 12,
    color: "#888",
  },
  transaction: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    paddingVertical: 12,
    borderBottomWidth: 1,
  },
  transactionInfo: {
    flex: 1,
  },
  transactionDate: {
    fontSize: 12,
    color: "#888",
  },
  transactionDesc: {
    fontSize: 14,
    marginTop: 2,
  },
  transactionAmount: {
    fontSize: 14,
    fontWeight: "600",
  },
  credit: {
    color: "#4CAF50",
  },
  debit: {
    color: "#f44336",
  },
  paymentMethod: {
    flexDirection: "row",
    alignItems: "center",
    padding: 16,
    borderWidth: 1,
    borderRadius: 12,
    marginBottom: 10,
  },
  cardIcon: {
    fontSize: 24,
    marginRight: 12,
  },
  cardInfo: {
    flex: 1,
  },
  cardName: {
    fontSize: 14,
    fontWeight: "600",
  },
  cardExpiry: {
    fontSize: 12,
    color: "#888",
    marginTop: 2,
  },
  defaultBadge: {
    backgroundColor: "#4CAF50",
    paddingHorizontal: 8,
    paddingVertical: 4,
    borderRadius: 4,
  },
  defaultText: {
    color: "#fff",
    fontSize: 10,
    fontWeight: "600",
  },
  addCardButton: {
    paddingVertical: 14,
    alignItems: "center",
  },
  addCardText: {
    color: "#4CAF50",
    fontWeight: "600",
  },
  bottomPadding: {
    height: 40,
  },
  modalOverlay: {
    flex: 1,
    backgroundColor: "rgba(0,0,0,0.7)",
    justifyContent: "center",
    alignItems: "center",
    padding: 20,
  },
  modalContent: {
    backgroundColor: "#1a1a1a",
    width: "100%",
    padding: 24,
    borderRadius: 16,
  },
  modalTitle: {
    fontSize: 22,
    fontWeight: "bold",
    textAlign: "center",
    marginBottom: 8,
  },
  modalSubtitle: {
    fontSize: 14,
    color: "#888",
    textAlign: "center",
    marginBottom: 20,
  },
  codeInput: {
    backgroundColor: "#333",
    padding: 16,
    borderRadius: 8,
    fontSize: 18,
    textAlign: "center",
    letterSpacing: 2,
    color: "#fff",
    marginBottom: 20,
  },
  modalButtons: {
    flexDirection: "row",
    gap: 12,
  },
  modalButton: {
    flex: 1,
    paddingVertical: 14,
    borderRadius: 8,
    alignItems: "center",
  },
  cancelButton: {
    backgroundColor: "#333",
  },
  redeemButton: {
    backgroundColor: "#4CAF50",
  },
  redeemButtonText: {
    color: "#fff",
    fontWeight: "600",
  },
});
