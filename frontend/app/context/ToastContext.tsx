import React, { createContext, useContext, useState, ReactNode } from 'react';
import { View, Text, StyleSheet } from 'react-native';
import { Ionicons } from '@expo/vector-icons';

type ToastType = 'success' | 'error' | 'info';

interface ToastState {
  type: ToastType;
  message: string;
}

interface ToastContextType {
  showToast: (type: ToastType, message: string, durationMs?: number) => void;
}

const ToastContext = createContext<ToastContextType | undefined>(undefined);

const COLORS: Record<ToastType, string> = {
  success: '#00A551',
  error: '#DC143C',
  info: '#0047AB',
};

const ICONS: Record<ToastType, keyof typeof Ionicons.glyphMap> = {
  success: 'checkmark-circle',
  error: 'alert-circle',
  info: 'information-circle',
};

// Alert.alert() de react-native no muestra ninguna UI en web (react-native-web
// no lo implementa) — este toast global reemplaza los Alert.alert informativos
// (error/éxito de un solo botón) en toda la app, sin que cada pantalla tenga
// que reimplementar su propio estado/JSX de toast.
export function ToastProvider({ children }: { children: ReactNode }) {
  const [toast, setToast] = useState<ToastState | null>(null);

  const showToast = (type: ToastType, message: string, durationMs = 2800) => {
    setToast({ type, message });
    setTimeout(() => setToast(null), durationMs);
  };

  return (
    <ToastContext.Provider value={{ showToast }}>
      {children}
      {toast && (
        <View style={styles.overlay} pointerEvents="box-none">
          <View style={[styles.toast, { backgroundColor: COLORS[toast.type] }]}>
            <Ionicons name={ICONS[toast.type]} size={18} color="#FFFFFF" />
            <Text style={styles.text}>{toast.message}</Text>
          </View>
        </View>
      )}
    </ToastContext.Provider>
  );
}

export function useToast() {
  const ctx = useContext(ToastContext);
  if (!ctx) {
    throw new Error('useToast must be used within a ToastProvider');
  }
  return ctx;
}

const styles = StyleSheet.create({
  overlay: {
    position: 'absolute',
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
    paddingTop: 56,
    paddingHorizontal: 16,
    zIndex: 999,
  },
  toast: {
    flexDirection: 'row',
    alignItems: 'center',
    borderRadius: 10,
    padding: 12,
    gap: 8,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.3,
    shadowRadius: 8,
    elevation: 8,
  },
  text: {
    flex: 1,
    color: '#FFFFFF',
    fontSize: 13,
    fontWeight: '600',
  },
});
