#!/bin/bash
#
# Setup script for extracting the native library from Y-Trac APK
#
# This script downloads the Y-Trac APK and extracts libSensorsRecordIF.so
# for use with the CTRK Converter Android app.
#

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ANDROID_APP_DIR="$SCRIPT_DIR/../android_app/app/src/main/jniLibs"
APK_FILE="$SCRIPT_DIR/ytrac.apk"
EXTRACT_DIR="$SCRIPT_DIR/ytrac_extracted"

echo "=== Y-Trac Native Library Setup ==="
echo

# Check for required tools
check_tool() {
    if ! command -v "$1" &> /dev/null; then
        echo "ERROR: $1 is required but not installed."
        echo "Install with: $2"
        exit 1
    fi
}

check_tool unzip "brew install unzip (or apt install unzip)"
check_tool curl "brew install curl (or apt install curl)"

# Download APK if not present
if [ ! -f "$APK_FILE" ]; then
    echo "APK not found. Attempting download from APKPure..."
    echo
    echo "NOTE: APKPure may require manual download due to CAPTCHA."
    echo "If this fails, please download manually from:"
    echo "  https://apkpure.com/y-trac/com.yamaha.jp.dataviewer"
    echo
    echo "Or pull from a device with Y-Trac installed:"
    echo "  adb shell pm path com.yamaha.jp.dataviewer"
    echo "  adb pull <path> $APK_FILE"
    echo

    # Try direct download (may not work due to dynamic URLs)
    # This is a placeholder - APKPure uses dynamic download URLs
    echo "Automatic download not available. Please download manually."
    echo "Place the APK file at: $APK_FILE"
    exit 1
fi

echo "Found APK: $APK_FILE"

# Clean previous extraction
rm -rf "$EXTRACT_DIR"
mkdir -p "$EXTRACT_DIR"

# Extract APK
echo "Extracting APK..."
unzip -q "$APK_FILE" -d "$EXTRACT_DIR"

# Check for native libraries
if [ ! -d "$EXTRACT_DIR/lib" ]; then
    echo "ERROR: No native libraries found in APK"
    exit 1
fi

echo "Found architectures:"
ls "$EXTRACT_DIR/lib/"

# Copy libraries to Android app
echo
echo "Installing native libraries..."

for arch in arm64-v8a armeabi-v7a x86 x86_64; do
    SRC="$EXTRACT_DIR/lib/$arch/libSensorsRecordIF.so"
    if [ -f "$SRC" ]; then
        DEST_DIR="$ANDROID_APP_DIR/$arch"
        mkdir -p "$DEST_DIR"
        cp "$SRC" "$DEST_DIR/"
        echo "  Installed: $arch/libSensorsRecordIF.so"
    fi
done

# Verify arm64-v8a was installed (required for most devices)
if [ ! -f "$ANDROID_APP_DIR/arm64-v8a/libSensorsRecordIF.so" ]; then
    echo
    echo "WARNING: arm64-v8a library not found. Most modern devices need this."
fi

# Cleanup
echo
echo "Cleaning up extracted files..."
rm -rf "$EXTRACT_DIR"

echo
echo "=== Setup Complete ==="
echo
echo "Native library installed to:"
ls -la "$ANDROID_APP_DIR"/*/libSensorsRecordIF.so 2>/dev/null || echo "  (no libraries found)"
echo
echo "You can now build the Android app:"
echo "  cd ../android_app && ./gradlew assembleDebug"
