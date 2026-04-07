// Copyright The OpenTelemetry Authors
// SPDX-License-Identifier: Apache-2.0
import { ThemedView } from "@/components/ThemedView";
import { ThemedText } from "@/components/ThemedText";
import { StyleSheet, TextInput, ScrollView, View, Button } from "react-native";
import { useState } from "react";
import Toast from "react-native-toast-message";

export default function Support() {
  const [message, setMessage] = useState("");

  const sendMessage = () => {
    if (message.trim()) {
      Toast.show({
        type: "success",
        text1: "Message Sent",
        text2: "A support agent will respond shortly.",
      });
      setMessage("");
    }
  };

  return (
    <ThemedView style={styles.container}>
      <ScrollView>
        <ThemedText style={styles.title}>Customer Support</ThemedText>
        
        <View style={styles.faqSection}>
          <ThemedText style={styles.subtitle}>Frequently Asked Questions</ThemedText>
          <View style={styles.faqCard}>
            <ThemedText style={styles.bold}>How do I track my order?</ThemedText>
            <ThemedText>Go to your Profile and click on Order History to see real-time status.</ThemedText>
          </View>
          <View style={styles.faqCard}>
            <ThemedText style={styles.bold}>What is your return policy?</ThemedText>
            <ThemedText>We accept returns within 30 days of delivery.</ThemedText>
          </View>
        </View>

        <View style={styles.chatSection}>
          <ThemedText style={styles.subtitle}>Live Chat</ThemedText>
          <ThemedText style={styles.infoText}>Describe your issue below:</ThemedText>
          <TextInput
            style={styles.input}
            multiline
            numberOfLines={4}
            value={message}
            onChangeText={setMessage}
            placeholder="Type your message here..."
            placeholderTextColor="#888"
          />
          <Button title="Send Message" onPress={sendMessage} />
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
  faqSection: {
    marginBottom: 30,
  },
  faqCard: {
    backgroundColor: "rgba(128,128,128,0.2)",
    padding: 15,
    borderRadius: 8,
    marginBottom: 10,
  },
  bold: {
    fontWeight: "bold",
    marginBottom: 5,
  },
  chatSection: {
    marginTop: 10,
  },
  infoText: {
    marginBottom: 10,
  },
  input: {
    backgroundColor: "rgba(128,128,128,0.1)",
    borderRadius: 8,
    padding: 15,
    minHeight: 100,
    textAlignVertical: "top",
    color: "#fff",
    marginBottom: 15,
  },
});
