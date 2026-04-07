// Copyright The OpenTelemetry Authors
// SPDX-License-Identifier: Apache-2.0
import { useState } from 'react';
import { useQueryClient } from '@tanstack/react-query'
import { ThemedView } from "@/components/ThemedView";
import { StyleSheet } from "react-native";
import { getFrontendProxyURL, setFrontendProxyURL } from "@/utils/Settings";
import { setupTracerProvider } from "@/hooks/useTracer";
import { trace } from "@opentelemetry/api";
import { Setting } from "@/components/Setting";
import { ThemedText } from "@/components/ThemedText";
import { Switch, View, Button, ScrollView } from "react-native";

export default function Settings() {
  const queryClient = useQueryClient()
  const [isDarkMode, setIsDarkMode] = useState(true);
  const [PushEnabled, setPushEnabled] = useState(true);

  const onSetFrontendProxyURL = async (value: string) => {
    await setFrontendProxyURL(value);

    // Clear any cached queries since we now have a new endpoint to hit for everything
    await queryClient.invalidateQueries();

    // Need to setup a new tracer provider since the export URL for traces has now changed
    trace.disable();
    const provider = setupTracerProvider(value);
    trace.setGlobalTracerProvider(provider);
  };

  return (
    <ThemedView style={styles.container}>
      <ScrollView>
        <ThemedText style={styles.header}>Backend Config</ThemedText>
        <Setting name="Frontend Proxy URL" get={getFrontendProxyURL} set={onSetFrontendProxyURL} />
        
        <View style={styles.spacer} />
        <ThemedText style={styles.header}>App Preferences</ThemedText>
        
        <View style={styles.settingRow}>
          <ThemedText style={styles.settingLabel}>Dark Mode</ThemedText>
          <Switch value={isDarkMode} onValueChange={setIsDarkMode} />
        </View>

        <View style={styles.settingRow}>
          <ThemedText style={styles.settingLabel}>Push Notifications</ThemedText>
          <Switch value={PushEnabled} onValueChange={setPushEnabled} />
        </View>

        <View style={styles.spacer} />
        <Button title="Clear App Cache" color="red" onPress={() => {}} />
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
    fontSize: 22,
    fontWeight: "bold",
    marginBottom: 10,
  },
  spacer: {
    height: 30,
  },
  settingRow: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    paddingVertical: 15,
    borderBottomWidth: 1,
    borderBottomColor: "#444",
  },
  settingLabel: {
    fontSize: 16,
  },
});
