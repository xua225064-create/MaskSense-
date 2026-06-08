const { AndroidConfig, withAndroidManifest, withDangerousMod } = require('@expo/config-plugins');
const fs = require('fs');
const path = require('path');

const NETWORK_SECURITY_XML = `<?xml version="1.0" encoding="utf-8"?>
<network-security-config>
  <base-config cleartextTrafficPermitted="true" />
</network-security-config>
`;

function withAndroidCleartext(config) {
  config = withAndroidManifest(config, (modConfig) => {
    const mainApplication = AndroidConfig.Manifest.getMainApplicationOrThrow(modConfig.modResults);
    mainApplication.$['android:usesCleartextTraffic'] = 'true';
    mainApplication.$['android:networkSecurityConfig'] = '@xml/network_security_config';
    return modConfig;
  });

  return withDangerousMod(config, [
    'android',
    (modConfig) => {
      const xmlDir = path.join(modConfig.modRequest.platformProjectRoot, 'app/src/main/res/xml');
      fs.mkdirSync(xmlDir, { recursive: true });
      fs.writeFileSync(path.join(xmlDir, 'network_security_config.xml'), NETWORK_SECURITY_XML);
      return modConfig;
    },
  ]);
}

module.exports = withAndroidCleartext;
