// Copyright The OpenTelemetry Authors
// SPDX-License-Identifier: Apache-2.0
import { ThemedView } from "@/components/ThemedView";
import { ThemedText } from "@/components/ThemedText";
import { StyleSheet, View, Button, Dimensions } from "react-native";
import { useState } from "react";
import { router } from "expo-router";

const { width } = Dimensions.get("window");

export default function Onboarding() {
  const [step, setStep] = useState(0);

  const steps = [
    { title: "Welcome to OpenTelemetry", desc: "Start exploring our demo e-commerce app to learn how traces work." },
    { title: "Browse Products", desc: "Find top gear, telescopes, and recommendations based on your preferences." },
    { title: "Easy Checkout", desc: "Seamless cart handling and mocked order fulfillment for testing." },
  ];

  const handleNext = () => {
    if (step < steps.length - 1) {
      setStep(step + 1);
    } else {
      router.replace("/");
    }
  };

  return (
    <ThemedView style={styles.container}>
      <View style={styles.slide}>
        <ThemedText style={styles.title}>{steps[step].title}</ThemedText>
        <ThemedText style={styles.desc}>{steps[step].desc}</ThemedText>
        <View style={styles.dots}>
          {steps.map((_, i) => (
            <View key={i} style={[styles.dot, step === i && styles.activeDot]} />
          ))}
        </View>
        <View style={styles.buttonContainer}>
          <Button title={step === steps.length - 1 ? "Get Started" : "Next"} onPress={handleNext} />
        </View>
      </View>
    </ThemedView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    justifyContent: "center",
    alignItems: "center",
  },
  slide: {
    width: width * 0.8,
    alignItems: "center",
    padding: 20,
  },
  title: {
    fontSize: 24,
    fontWeight: "bold",
    marginBottom: 20,
    textAlign: "center",
  },
  desc: {
    fontSize: 16,
    textAlign: "center",
    marginBottom: 40,
  },
  dots: {
    flexDirection: "row",
    marginBottom: 30,
  },
  dot: {
    width: 10,
    height: 10,
    borderRadius: 5,
    backgroundColor: "#888",
    marginHorizontal: 5,
  },
  activeDot: {
    backgroundColor: "#fff",
  },
  buttonContainer: {
    width: "100%",
  },
});
