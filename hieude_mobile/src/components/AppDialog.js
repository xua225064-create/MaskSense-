import React from 'react';
import { Modal, StyleSheet, Text, TouchableOpacity, View } from 'react-native';
import { Feather } from '@expo/vector-icons';

const ICONS = {
  success: 'check-circle',
  danger: 'alert-triangle',
  warning: 'alert-circle',
  info: 'info',
};

export default function AppDialog({ visible, title, message, variant = 'info', actions = [], onClose }) {
  const safeActions = actions.length ? actions : [{ label: 'OK', onPress: onClose, primary: true }];

  return (
    <Modal visible={visible} transparent animationType="fade" onRequestClose={onClose}>
      <View style={s.overlay}>
        <View style={s.card}>
          <View style={[s.iconWrap, s[`${variant}Icon`]]}>
            <Feather name={ICONS[variant] || ICONS.info} size={26} color="#fff" />
          </View>

          <Text style={s.title}>{title}</Text>
          {!!message && <Text style={s.message}>{message}</Text>}

          <View style={s.actions}>
            {safeActions.map((action, index) => (
              <TouchableOpacity
                key={`${action.label}-${index}`}
                style={[s.actionBtn, action.primary && s.primaryBtn, action.danger && s.dangerBtn]}
                activeOpacity={0.85}
                onPress={action.onPress || onClose}
              >
                <Text style={[s.actionText, (action.primary || action.danger) && s.primaryText]}>
                  {action.label}
                </Text>
              </TouchableOpacity>
            ))}
          </View>
        </View>
      </View>
    </Modal>
  );
}

const s = StyleSheet.create({
  overlay: {
    flex: 1,
    backgroundColor: 'rgba(28, 25, 23, 0.45)',
    alignItems: 'center',
    justifyContent: 'center',
    padding: 24,
  },
  card: {
    width: '100%',
    maxWidth: 360,
    backgroundColor: '#fff',
    borderRadius: 24,
    padding: 24,
    alignItems: 'center',
    shadowColor: '#000',
    shadowOpacity: 0.18,
    shadowRadius: 24,
    shadowOffset: { width: 0, height: 12 },
    elevation: 12,
  },
  iconWrap: {
    width: 58,
    height: 58,
    borderRadius: 29,
    alignItems: 'center',
    justifyContent: 'center',
    marginBottom: 16,
  },
  infoIcon: { backgroundColor: '#065f46' },
  successIcon: { backgroundColor: '#059669' },
  warningIcon: { backgroundColor: '#d97706' },
  dangerIcon: { backgroundColor: '#dc2626' },
  title: {
    color: '#1c1917',
    fontSize: 21,
    lineHeight: 27,
    fontWeight: '900',
    textAlign: 'center',
    marginBottom: 8,
  },
  message: {
    color: '#57534e',
    fontSize: 14,
    lineHeight: 21,
    textAlign: 'center',
    marginBottom: 22,
  },
  actions: {
    width: '100%',
    flexDirection: 'row',
    gap: 10,
  },
  actionBtn: {
    flex: 1,
    minHeight: 48,
    borderRadius: 16,
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: '#f5f5f4',
    borderWidth: 1,
    borderColor: '#e7e5e4',
    paddingHorizontal: 12,
  },
  primaryBtn: {
    backgroundColor: '#065f46',
    borderColor: '#065f46',
  },
  dangerBtn: {
    backgroundColor: '#dc2626',
    borderColor: '#dc2626',
  },
  actionText: {
    color: '#44403c',
    fontSize: 14,
    fontWeight: '900',
  },
  primaryText: {
    color: '#fff',
  },
});
