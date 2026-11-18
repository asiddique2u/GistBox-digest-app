# GistBox Android app

The Flutter client submits public URLs and PDFs to the GistBox API, displays
the returned Markdown digest, and keeps digest history in a private JSON file
on the device. It does not create accounts or sync history.

## Requirements

- Flutter 3.50 stable or newer
- Android SDK and an emulator or Android device

## Configure and run

From this directory, install Dart dependencies:

```shell
flutter pub get
```

The default API URL targets the Android emulator's host machine at
`http://10.0.2.2:8000`. For another development backend, supply its base URL:

```shell
flutter run --dart-define=GISTBOX_API_BASE_URL=http://10.0.2.2:8000
```

For a physical device, use a backend URL reachable from that device. Release
builds require an HTTPS URL. Cleartext traffic is enabled only for debug builds.

## Google Play release

The Android host project is included. It currently uses the placeholder
application ID `com.example.gistbox_mobile`; choose a unique, permanent ID
before the first Play Store upload because it cannot be changed after release.

Create and safeguard an upload keystore outside source control, then create
`android/key.properties` (already ignored by Git) with these values:

```properties
storePassword=YOUR_STORE_PASSWORD
keyPassword=YOUR_KEY_PASSWORD
keyAlias=YOUR_KEY_ALIAS
storeFile=C:\\absolute\\path\\to\\upload-keystore.jks
```

Release builds fail until all signing values and the keystore are present.
Build the Android App Bundle with the production HTTPS API URL:

```shell
flutter build appbundle --release --dart-define=GISTBOX_API_BASE_URL=https://your-api.example
```

## Checks

```shell
flutter analyze
flutter test
```

Before uploading to Google Play, set the final application ID, configure an
upload signing key outside source control, and complete the Play Console
listing and data-safety declarations. Submitted URLs and PDFs are sent to the
GistBox backend for processing; only digest metadata and summaries are stored
in the app's local history. Android cloud backup and device-to-device transfer
exclude the local history directory.
