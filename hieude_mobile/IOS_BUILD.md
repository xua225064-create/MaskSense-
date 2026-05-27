# iOS IPA Build

This Expo app is configured for EAS cloud builds and GitHub Actions.

## One-time setup

1. Create or sign in to an Expo account.
2. From `hieude_mobile`, run:

```powershell
npx --yes eas-cli@latest login
npx --yes eas-cli@latest init
```

3. Create an Expo access token:

```powershell
npx --yes eas-cli@latest account:view
```

Then create a token from the Expo dashboard and add it to GitHub repository secrets as:

```text
EXPO_TOKEN
```

4. Make sure the iOS bundle identifier is correct in `app.json`:

```text
com.hieude.marksense
```

## Build locally from this machine

```powershell
npm run build:ios:preview
```

The `preview` profile creates an internal iOS IPA build. EAS will ask for Apple credentials or use saved credentials from your Expo account.

## Build from GitHub Actions

Open GitHub Actions, run `Build HieuDe Mobile iOS IPA`, and choose:

- `preview` for internal testing and AltStore/TestFlight-style testing flows
- `production` for App Store/TestFlight release builds

When the workflow finishes, EAS prints the build URL in the logs. Download the `.ipa` from that EAS build page.
