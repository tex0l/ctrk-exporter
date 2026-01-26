#!/bin/bash
# Build and run CTRK Converter on Android emulator

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
ANDROID_HOME="${ANDROID_HOME:-$HOME/Library/Android/sdk}"

export PATH="$ANDROID_HOME/emulator:$ANDROID_HOME/platform-tools:$ANDROID_HOME/cmdline-tools/latest/bin:$PATH"

echo "=== CTRK Converter - Build and Run ==="
echo ""

# Check for emulator
AVD_NAME=$($ANDROID_HOME/emulator/emulator -list-avds | head -1)
if [ -z "$AVD_NAME" ]; then
    echo "ERROR: No AVD found. Please create one in Android Studio."
    exit 1
fi
echo "Found AVD: $AVD_NAME"

# Check if emulator is running
if ! adb devices | grep -q "emulator"; then
    echo ""
    echo "Starting emulator..."
    $ANDROID_HOME/emulator/emulator -avd "$AVD_NAME" -no-snapshot-load &
    EMULATOR_PID=$!

    echo "Waiting for emulator to boot..."
    adb wait-for-device

    # Wait for boot animation to complete
    while [ "$(adb shell getprop sys.boot_completed 2>/dev/null)" != "1" ]; do
        sleep 2
        echo -n "."
    done
    echo ""
    echo "Emulator ready!"
else
    echo "Emulator already running"
fi

# Download Gradle wrapper jar if needed
WRAPPER_JAR="$SCRIPT_DIR/gradle/wrapper/gradle-wrapper.jar"
if [ ! -f "$WRAPPER_JAR" ]; then
    echo ""
    echo "Downloading Gradle wrapper..."
    mkdir -p "$SCRIPT_DIR/gradle/wrapper"
    curl -L -o "$WRAPPER_JAR" "https://services.gradle.org/distributions/gradle-8.2-bin.zip" 2>/dev/null || true

    # Actually we need the jar, not the distribution. Let's use gradle init
    cd "$SCRIPT_DIR"
    if command -v gradle &> /dev/null; then
        gradle wrapper --gradle-version 8.2
    else
        echo "Gradle not found. Please install Gradle or download the wrapper manually."
        echo "You can also build the project from Android Studio."
        exit 1
    fi
fi

# Build the APK
echo ""
echo "Building APK..."
cd "$SCRIPT_DIR"

# Check if we can use gradle directly
if command -v gradle &> /dev/null; then
    gradle assembleDebug
elif [ -f "$SCRIPT_DIR/gradlew" ]; then
    ./gradlew assembleDebug
else
    echo "ERROR: Cannot find gradle or gradlew"
    exit 1
fi

# Find the APK
APK_PATH="$SCRIPT_DIR/app/build/outputs/apk/debug/app-debug.apk"
if [ ! -f "$APK_PATH" ]; then
    echo "ERROR: APK not found at $APK_PATH"
    exit 1
fi
echo "APK built: $APK_PATH"

# Install the APK
echo ""
echo "Installing APK..."
adb install -r "$APK_PATH"

# Push test CTRK file
echo ""
echo "Pushing test CTRK file..."
CTRK_FILE="$PROJECT_ROOT/assets/original/20250729-170818.CTRK"
if [ -f "$CTRK_FILE" ]; then
    adb push "$CTRK_FILE" /sdcard/Download/
    echo "Pushed: $CTRK_FILE"
else
    echo "Warning: Test file not found at $CTRK_FILE"
fi

# Launch the app
echo ""
echo "Launching app..."
adb shell am start -n com.ctrk.converter/.MainActivity

echo ""
echo "=== Done ==="
echo ""
echo "The app should now be running on the emulator."
echo "Press the 'Convert CTRK Files' button to start conversion."
echo ""
echo "To view logs:"
echo "  adb logcat -s CTRKConverter:* JNISupport:* SensorsRecordIF:*"
echo ""
echo "To pull output files:"
echo "  adb pull /sdcard/Download/20250729-170818_native.csv ."
