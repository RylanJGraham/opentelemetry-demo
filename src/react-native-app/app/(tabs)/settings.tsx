// Copyright The OpenTelemetry Authors
// SPDX-License-Identifier: Apache-2.0
import { useState } from 'react';
import { useQueryClient } from '@tanstack/react-query'
import { ThemedView } from "@/components/ThemedView";
import { StyleSheet, ScrollView, View, Pressable, Switch, Alert } from "react-native";
import { getFrontendProxyURL, setFrontendProxyURL } from "@/utils/Settings";
import { setupTracerProvider } from "@/hooks/useTracer";
import { trace } from "@opentelemetry/api";
import { ThemedText } from "@/components/ThemedText";
import Toast from "react-native-toast-message";

export default function Settings() {
  const queryClient = useQueryClient();
  const [isDarkMode, setIsDarkMode] = useState(true);
  const [pushEnabled, setPushEnabled] = useState(true);
  const [emailEnabled, setEmailEnabled] = useState(true);
  const [autoUpdate, setAutoUpdate] = useState(true);
  const [dataSaver, setDataSaver] = useState(false);

  const onSetFrontendProxyURL = async (value: string) => {
    await setFrontendProxyURL(value);
    await queryClient.invalidateQueries();
    trace.disable();
    const provider = setupTracerProvider(value);
    trace.setGlobalTracerProvider(provider);
  };

  const handleClearCache = () => {
    Alert.alert(
      "Clear Cache",
      "This will clear all cached data. Are you sure?",
      [
        { text: "Cancel", style: "cancel" },
        { 
          text: "Clear", 
          style: "destructive",
          onPress: () => {
            queryClient.clear();
            Toast.show({
              type: "success",
              text1: "Cache cleared",
            });
          }
        },
      ]
    );
  };

  const handleResetOnboarding = () => {
    Alert.alert(
      "Reset Onboarding",
      "This will show the onboarding screens on next launch.",
      [
        { text: "Cancel", style: "cancel" },
        { 
          text: "Reset", 
          onPress: () => {
            Toast.show({
              type: "success",
              text1: "Onboarding will be shown on next launch",
            });
          }
        },
      ]
    );
  };

  const SettingItem = ({ 
    icon, 
    title, 
    subtitle, 
    value, 
    onValueChange,
    destructive = false 
  }: { 
    icon: string; 
    title: string; 
    subtitle?: string; 
    value?: boolean; 
    onValueChange?: (val: boolean) => void;
    destructive?: boolean;
  }) => (
    <View style={styles.settingItem}>
      <View style={styles.settingLeft}>
        <ThemedText style={styles.settingIcon}>{icon}</ThemedText>
        <View>
          <ThemedText style={[styles.settingTitle, destructive && styles.destructiveText]}>
            {title}
          </ThemedText>
          {subtitle && (
            <ThemedText style={styles.settingSubtitle}>{subtitle}</ThemedText>
          )}
        </View>
      </View>
      {onValueChange && (
        <Switch 
          value={value} 
          onValueChange={onValueChange}
          trackColor={{ false: "#444", true: "#4CAF50" }}
        />
      )}
    </View>
  );

  const ActionItem = ({ 
    icon, 
    title, 
    subtitle, 
    onPress,
    destructive = false 
  }: { 
    icon: string; 
    title: string; 
    subtitle?: string; 
    onPress: () => void;
    destructive?: boolean;
  }) => (
    <Pressable style={styles.settingItem} onPress={onPress}>
      <View style={styles.settingLeft}>
        <ThemedText style={styles.settingIcon}>{icon}</ThemedText>
        <View>
          <ThemedText style={[styles.settingTitle, destructive && styles.destructiveText]}>
            {title}
          </ThemedText>
          {subtitle && (
            <ThemedText style={styles.settingSubtitle}>{subtitle}</ThemedText>
          )}
        </View>
      </View>
      <ThemedText style={styles.chevron}>›</ThemedText>
    </Pressable>
  );

  return (
    <ThemedView style={styles.container}>
      <ScrollView showsVerticalScrollIndicator={false}>
        {/* Account Section */}
        <View style={styles.section}>
          <ThemedText style={styles.sectionTitle}>Account</ThemedText>
          <View style={styles.card}>
            <ActionItem 
              icon="👤" 
              title="Edit Profile" 
              subtitle="Change name, email, avatar"
              onPress={() => {}}
            />
            <ActionItem 
              icon="🔒" 
              title="Change Password" 
              subtitle="Update your security"
              onPress={() => {}}
            />
            <ActionItem 
              icon="📍" 
              title="Manage Addresses" 
              subtitle="2 saved addresses"
              onPress={() => {}}
            />
          </View>
        </View>

        {/* Notifications Section */}
        <View style={styles.section}>
          <ThemedText style={styles.sectionTitle}>Notifications</ThemedText>
          <View style={styles.card}>
            <SettingItem 
              icon="🔔" 
              title="Push Notifications" 
              subtitle="Order updates, promotions"
              value={pushEnabled}
              onValueChange={setPushEnabled}
            />
            <SettingItem 
              icon="📧" 
              title="Email Notifications" 
              subtitle="Weekly digest, offers"
              value={emailEnabled}
              onValueChange={setEmailEnabled}
            />
          </View>
        </View>

        {/* App Preferences */}
        <View style={styles.section}>
          <ThemedText style={styles.sectionTitle}>App Preferences</ThemedText>
          <View style={styles.card}>
            <SettingItem 
              icon="🌙" 
              title="Dark Mode" 
              value={isDarkMode}
              onValueChange={setIsDarkMode}
            />
            <SettingItem 
              icon="📶" 
              title="Data Saver" 
              subtitle="Reduce image quality"
              value={dataSaver}
              onValueChange={setDataSaver}
            />
            <SettingItem 
              icon="🔄" 
              title="Auto-Update" 
              subtitle="Keep app up to date"
              value={autoUpdate}
              onValueChange={setAutoUpdate}
            />
          </View>
        </View>

        {/* Support Section */}
        <View style={styles.section}>
          <ThemedText style={styles.sectionTitle}>Support</ThemedText>
          <View style={styles.card}>
            <ActionItem 
              icon="❓" 
              title="Help Center" 
              subtitle="FAQs and guides"
              onPress={() => {}}
            />
            <ActionItem 
              icon="💬" 
              title="Contact Support" 
              subtitle="Chat with our team"
              onPress={() => {}}
            />
            <ActionItem 
              icon="⭐" 
              title="Rate App" 
              subtitle="Share your feedback"
              onPress={() => {}}
            />
          </View>
        </View>

        {/* Advanced Section */}
        <View style={styles.section}>
          <ThemedText style={styles.sectionTitle}>Advanced</ThemedText>
          <View style={styles.card}>
            <ActionItem 
              icon="🗑️" 
              title="Clear Cache" 
              subtitle="Free up space"
              onPress={handleClearCache}
            />
            <ActionItem 
              icon="🎓" 
              title="Reset Onboarding" 
              subtitle="Show welcome screens again"
              onPress={handleResetOnboarding}
            />
          </View>
        </View>

        {/* Debug Section (for development) */}
        <View style={styles.section}>
          <ThemedText style={styles.sectionTitle}>Developer</ThemedText>
          <View style={styles.card}>
            <View style={styles.debugInfo}>
              <ThemedText style={styles.debugLabel}>App Version</ThemedText>
              <ThemedText style={styles.debugValue}>2.0.1 (Build 245)</ThemedText>
            </View>
            <View style={styles.debugInfo}>
              <ThemedText style={styles.debugLabel}>Environment</ThemedText>
              <ThemedText style={styles.debugValue}>Production</ThemedText>
            </View>
            <View style={styles.debugInfo}>
              <ThemedText style={styles.debugLabel}>User ID</ThemedText>
              <ThemedText style={styles.debugValue}>mock-user-001</ThemedText>
            </View>
          </View>
        </View>

        {/* Logout Button */}
        <Pressable style={styles.logoutButton}>
          <ThemedText style={styles.logoutText}>Log Out</ThemedText>
        </Pressable>

        <View style={styles.bottomPadding} />
      </ScrollView>
    </ThemedView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
  },
  section: {
    marginBottom: 24,
    paddingHorizontal: 15,
  },
  sectionTitle: {
    fontSize: 13,
    fontWeight: "600",
    color: "#888",
    textTransform: "uppercase",
    marginBottom: 8,
    marginLeft: 4,
  },
  card: {
    backgroundColor: "rgba(128,128,128,0.05)",
    borderRadius: 12,
    overflow: "hidden",
  },
  settingItem: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    paddingVertical: 14,
    paddingHorizontal: 16,
    borderBottomWidth: 1,
    borderBottomColor: "rgba(128,128,128,0.1)",
  },
  settingLeft: {
    flexDirection: "row",
    alignItems: "center",
    flex: 1,
  },
  settingIcon: {
    fontSize: 20,
    width: 32,
  },
  settingTitle: {
    fontSize: 16,
    fontWeight: "500",
  },
  settingSubtitle: {
    fontSize: 12,
    color: "#888",
    marginTop: 2,
  },
  destructiveText: {
    color: "#f44336",
  },
  chevron: {
    fontSize: 20,
    color: "#888",
  },
  debugInfo: {
    flexDirection: "row",
    justifyContent: "space-between",
    paddingVertical: 12,
    paddingHorizontal: 16,
    borderBottomWidth: 1,
    borderBottomColor: "rgba(128,128,128,0.1)",
  },
  debugLabel: {
    fontSize: 14,
    color: "#888",
  },
  debugValue: {
    fontSize: 14,
    fontFamily: "monospace",
  },
  logoutButton: {
    backgroundColor: "rgba(244,67,54,0.1)",
    marginHorizontal: 15,
    paddingVertical: 16,
    borderRadius: 12,
    alignItems: "center",
    marginTop: 8,
    marginBottom: 24,
  },
  logoutText: {
    color: "#f44336",
    fontSize: 16,
    fontWeight: "600",
  },
  bottomPadding: {
    height: 20,
  },
});
