"""Text rules applied by branding.py. Data only.

Each rule is (file, text in upstream, replacement[, expected count]). The replacement may use
@APP@, @APP_LOWER@, @ANDROID_ID@ and @BUNDLE@. Anchors are literal blocks of the upstream file;
when upstream changes one, branding.py fails and names the rule.

Grouped by what the rule does:
  captive wiring   src/*            the client is locked to our server (code in magodesk/captive.rs)
  Windows          flutter/windows, libs/portable, build.py, src/platform/windows.rs
  Android          flutter/android, flutter/lib/mobile
  macOS            flutter/macos, Cargo.toml bundle metadata
  desktop UI       flutter/lib/desktop
"""

RULES = [
    # build.py
    ('build.py',
     r'''flutter_build_dir_2 = f'flutter/{flutter_build_dir}'
skip_cargo = False''',
     r'''flutter_build_dir_2 = f'flutter/{flutter_build_dir}'
# Rebranded builds name the executable after RD_APP_NAME (see flutter/windows/CMakeLists.txt).
app_exe_name = (os.environ.get('RD_APP_NAME') or 'rustdesk') + ('.exe' if windows else '')
# macOS: the .app bundle is named after PRODUCT_NAME (see res/branding.py)
mac_app_name = (os.environ.get('RD_APP_NAME') or 'RustDesk') + '.app'
skip_cargo = False'''),
    ('build.py',
     r'''    system2('cp -rf ../target/release/service ./build/macos/Build/Products/Release/RustDesk.app/Contents/MacOS/')''',
     r'''    system2(f'cp -rf ../target/release/service ./build/macos/Build/Products/Release/{mac_app_name}/Contents/MacOS/')'''),
    ('build.py',
     r'''        f'python3 ./generate.py -f ../../{flutter_build_dir_2} -o . -e ../../{flutter_build_dir_2}/rustdesk.exe')''',
     r'''        f'python3 ./generate.py -f ../../{flutter_build_dir_2} -o . -e ../../{flutter_build_dir_2}/{app_exe_name}')'''),
    # flutter/android/app/build.gradle
    ('flutter/android/app/build.gradle',
     r'''    }
}

def flutterVersionCode = localProperties.getProperty('flutter.versionCode')''',
     r'''    }
}

// RD_APP_NAME is the same product name the desktop builds use; it renames the visible app.
def rdAppName = System.getenv('RD_APP_NAME') ?: '@APP@'

def flutterVersionCode = localProperties.getProperty('flutter.versionCode')'''),
    ('flutter/android/app/build.gradle',
     r'''
    compileOptions {''',
     r'''
    buildFeatures {
        buildConfig true
    }

    compileOptions {'''),
    ('flutter/android/app/build.gradle',
     r'''        applicationId "com.carriez.flutter_hbb"''',
     r'''        // The code keeps the upstream namespace above (only the ffi package must not move);
        // the installed identity is the app id, so it must differ from the stock RustDesk.
        applicationId "@ANDROID_ID@"
        manifestPlaceholders = [appLabel: rdAppName, uriScheme: rdAppName.toLowerCase()]
        buildConfigField "String", "RD_APP_NAME", "\"${rdAppName}\""
        resValue "string", "app_name", rdAppName'''),
    # flutter/android/app/src/main/AndroidManifest.xml
    ('flutter/android/app/src/main/AndroidManifest.xml',
     r'''        android:label="RustDesk"''',
     r'''        android:label="${appLabel}"'''),
    ('flutter/android/app/src/main/AndroidManifest.xml',
     r'''            android:label="RustDesk Input"''',
     r'''            android:label="${appLabel} Input"'''),
    ('flutter/android/app/src/main/AndroidManifest.xml',
     r'''                <data android:scheme="rustdesk" />''',
     r'''                <data android:scheme="${uriScheme}" />'''),
    # flutter/android/app/src/main/kotlin/com/carriez/flutter_hbb/BootReceiver.kt
    ('flutter/android/app/src/main/kotlin/com/carriez/flutter_hbb/BootReceiver.kt',
     r'''            Toast.makeText(context, "RustDesk is Open", Toast.LENGTH_LONG).show()''',
     r'''            Toast.makeText(context, "${BuildConfig.RD_APP_NAME} is Open", Toast.LENGTH_LONG).show()'''),
    # flutter/android/app/src/main/kotlin/com/carriez/flutter_hbb/FloatingWindowService.kt
    ('flutter/android/app/src/main/kotlin/com/carriez/flutter_hbb/FloatingWindowService.kt',
     r'''         popupMenu.menu.add(0, idShowRustDesk, 0, translate("Show RustDesk"))''',
     r'''         popupMenu.menu.add(0, idShowRustDesk, 0, translate("Show RustDesk").replace("RustDesk", BuildConfig.RD_APP_NAME))'''),
    # flutter/android/app/src/main/kotlin/com/carriez/flutter_hbb/MainService.kt
    ('flutter/android/app/src/main/kotlin/com/carriez/flutter_hbb/MainService.kt',
     r'''const val DEFAULT_NOTIFY_TITLE = "RustDesk"''',
     r'''val DEFAULT_NOTIFY_TITLE = BuildConfig.RD_APP_NAME'''),
    ('flutter/android/app/src/main/kotlin/com/carriez/flutter_hbb/MainService.kt',
     r'''                    "RustDeskVD",''',
     r'''                    "${BuildConfig.RD_APP_NAME}VD",'''),
    ('flutter/android/app/src/main/kotlin/com/carriez/flutter_hbb/MainService.kt',
     r'''            val channelId = "RustDesk"
            val channelName = "RustDesk Service"''',
     r'''            val channelId = BuildConfig.RD_APP_NAME
            val channelName = "${BuildConfig.RD_APP_NAME} Service"'''),
    ('flutter/android/app/src/main/kotlin/com/carriez/flutter_hbb/MainService.kt',
     r'''                description = "RustDesk Service Channel"''',
     r'''                description = "${BuildConfig.RD_APP_NAME} Service Channel"'''),
    # flutter/android/app/src/main/res/values/strings.xml
    ('flutter/android/app/src/main/res/values/strings.xml',
     r'''    <string name="app_name">RustDesk</string>
    <string name="accessibility_service_description">Allow other devices to control your phone using virtual touch, when RustDesk screen sharing is established</string>
    <string name="foreground_service_special_use_subtype">Keeps the RustDesk remote desktop host available for authorized unattended connections and foreground notifications without starting screen capture before user approval.</string>''',
     r'''    <string name="accessibility_service_description">Allow other devices to control your phone using virtual touch, when screen sharing is established</string>
    <string name="foreground_service_special_use_subtype">Keeps the remote desktop host available for authorized unattended connections and foreground notifications without starting screen capture before user approval.</string>'''),
    # flutter/lib/desktop/widgets/tabbar_widget.dart
    ('flutter/lib/desktop/widgets/tabbar_widget.dart',
     r'''                            child: const Text(
                              "RustDesk",
                              style: TextStyle(fontSize: 13),''',
     r'''                            child: Text(
                              appName,
                              style: const TextStyle(fontSize: 13),'''),
    # flutter/lib/mobile/pages/server_page.dart
    ('flutter/lib/mobile/pages/server_page.dart',
     r'''  int _countdown = bind.isCustomClient() ? 0 : 12;''',
     r'''  // Kept at 12s even though a rebranded app is a "custom client" (which would skip the wait).
  int _countdown = 12;'''),
    # flutter/windows/CMakeLists.txt
    ('flutter/windows/CMakeLists.txt',
     r'''set(BINARY_NAME "rustdesk")''',
     r'''# RD_APP_NAME comes from the environment so a rebranded build produces <name>.exe.
if(DEFINED ENV{RD_APP_NAME} AND NOT "$ENV{RD_APP_NAME}" STREQUAL "")
  set(BINARY_NAME "$ENV{RD_APP_NAME}")
  set(RD_PRODUCT_NAME "$ENV{RD_APP_NAME}")
else()
  set(BINARY_NAME "rustdesk")
  set(RD_PRODUCT_NAME "RustDesk")
endif()'''),
    # flutter/windows/runner/CMakeLists.txt
    ('flutter/windows/runner/CMakeLists.txt',
     r'''target_compile_definitions(${BINARY_NAME} PRIVATE "FLUTTER_VERSION=\"${FLUTTER_VERSION}\"")
target_compile_definitions(${BINARY_NAME} PRIVATE "FLUTTER_VERSION_MAJOR=${FLUTTER_VERSION_MAJOR}")''',
     r'''target_compile_definitions(${BINARY_NAME} PRIVATE "FLUTTER_VERSION=\"${FLUTTER_VERSION}\"")
target_compile_definitions(${BINARY_NAME} PRIVATE "RD_PRODUCT_NAME=\"${RD_PRODUCT_NAME}\"")
target_compile_definitions(${BINARY_NAME} PRIVATE "RD_EXE_NAME=\"${BINARY_NAME}.exe\"")
target_compile_definitions(${BINARY_NAME} PRIVATE "FLUTTER_VERSION_MAJOR=${FLUTTER_VERSION_MAJOR}")'''),
    # flutter/windows/runner/Runner.rc
    ('flutter/windows/runner/Runner.rc',
     r'''
#if defined(FLUTTER_VERSION_MAJOR) && defined(FLUTTER_VERSION_MINOR) && defined(FLUTTER_VERSION_PATCH) && defined(FLUTTER_VERSION_BUILD)''',
     r'''
#ifndef RD_PRODUCT_NAME
#define RD_PRODUCT_NAME "RustDesk"
#endif
#ifndef RD_EXE_NAME
#define RD_EXE_NAME "rustdesk.exe"
#endif

#if defined(FLUTTER_VERSION_MAJOR) && defined(FLUTTER_VERSION_MINOR) && defined(FLUTTER_VERSION_PATCH) && defined(FLUTTER_VERSION_BUILD)'''),
    ('flutter/windows/runner/Runner.rc',
     r'''            VALUE "FileDescription", "RustDesk Remote Desktop" "\0"''',
     r'''            VALUE "FileDescription", RD_PRODUCT_NAME " Remote Desktop" "\0"'''),
    ('flutter/windows/runner/Runner.rc',
     r'''            VALUE "InternalName", "rustdesk" "\0"''',
     r'''            VALUE "InternalName", RD_PRODUCT_NAME "\0"'''),
    ('flutter/windows/runner/Runner.rc',
     r'''            VALUE "OriginalFilename", "rustdesk.exe" "\0"
            VALUE "ProductName", "RustDesk" "\0"''',
     r'''            VALUE "OriginalFilename", RD_EXE_NAME "\0"
            VALUE "ProductName", RD_PRODUCT_NAME "\0"'''),
    # flutter/windows/runner/main.cpp
    ('flutter/windows/runner/main.cpp',
     r'''  std::wstring app_name = L"RustDesk";''',
     r'''#ifndef RD_PRODUCT_NAME
#define RD_PRODUCT_NAME "RustDesk"
#endif
  // Fallback only: get_rustdesk_app_name below returns the real name.
  std::wstring app_name = L"" RD_PRODUCT_NAME;'''),
    # libs/portable/build.rs
    ('libs/portable/build.rs',
     r'''            .set_manifest_file("../../res/manifest.xml");
        match res.compile() {''',
     r'''            .set_manifest_file("../../res/manifest.xml");
        // Rebranded builds: the self-extracting exe must not claim to be RustDesk.
        if let Some(name) = option_env!("RD_APP_NAME").filter(|n| !n.trim().is_empty()) {
            let name = name.trim();
            res.set("ProductName", name)
                .set("InternalName", name)
                .set("FileDescription", &format!("{name} Remote Desktop"))
                .set("OriginalFilename", &format!("{name}.exe"));
        }
        match res.compile() {'''),
    # src/client.rs
    ('src/client.rs',
     r'''        let mut id = id;''',
     r'''        let mut id = crate::captive::peer_id(&id).to_owned();'''),
    # src/common.rs
    ('src/common.rs',
     r'''pub async fn do_check_software_update() -> hbb_common::ResultType<()> {
    let (request, url) =''',
     r'''pub async fn do_check_software_update() -> hbb_common::ResultType<()> {
    // a captive build must never fetch (and then install) a stock RustDesk
    if crate::captive::is_captive() {
        return Ok(());
    }
    let (request, url) ='''),
    ('src/common.rs',
     r'''pub fn load_custom_client() {
    #[cfg(debug_assertions)]''',
     r'''pub fn load_custom_client() {
    crate::captive::apply();
    #[cfg(debug_assertions)]'''),
    # src/flutter_ffi.rs
    ('src/flutter_ffi.rs',
     r'''        crate::common::init_sodium();
        let mut env = env;''',
     r'''        crate::common::init_sodium();
        // The app name decides the config paths, so the captive settings go in before them.
        crate::captive::apply();
        let mut env = env;'''),
    # src/lib.rs
    ('src/lib.rs',
     r'''pub mod core_main;
mod custom_server;''',
     r'''pub mod core_main;
#[path = "../magodesk/captive.rs"]
mod captive;
mod custom_server;'''),
    # src/platform/windows.rs
    ('src/platform/windows.rs',
     r'''        .join("RustDesk")
        .join("RustDeskCustomClientStaging")''',
     r'''        .join(crate::get_app_name())
        .join(format!("{}CustomClientStaging", crate::get_app_name()))'''),
    ('src/platform/windows.rs',
     r'''pub fn get_license_from_exe_name() -> ResultType<CustomServer> {
    let mut exe = std::env::current_exe()?.to_str().unwrap_or("").to_owned();''',
     r'''pub fn get_license_from_exe_name() -> ResultType<CustomServer> {
    if crate::captive::is_captive() {
        bail!("captive build ignores the server in the exe name");
    }
    let mut exe = std::env::current_exe()?.to_str().unwrap_or("").to_owned();'''),
    ('src/platform/windows.rs',
     r'''            "RustDesk service control failed: {}",''',
     r'''            "{} service control failed: {}",
            crate::get_app_name(),'''),
    ('src/platform/windows.rs',
     r'''    let caption = "RustDesk Output"''',
     r'''    let caption = format!("{} Output", crate::get_app_name())'''),
    # src/ipc.rs
    ('src/ipc.rs',
     r'''                    Config::set_socks(None);''',
     r'''                    crate::captive::set_socks(None);'''),
    ('src/ipc.rs',
     r'''                    Config::set_socks(Some(data));''',
     r'''                    crate::captive::set_socks(Some(data));'''),
    ('src/ipc.rs',
     r'''        Config::set_socks(value.clone());''',
     r'''        crate::captive::set_socks(value.clone());'''),
    ('src/ipc.rs',
     r'''    Config::set_socks(if value.proxy.is_empty() {''',
     r'''    crate::captive::set_socks(if value.proxy.is_empty() {'''),
    ('src/ipc.rs',
     r'''        Config::set_socks(value.0.clone());''',
     r'''        crate::captive::set_socks(value.0.clone());'''),
    # src/ui_interface.rs
    ('src/ui_interface.rs',
     r'''            Config::set_socks(None);''',
     r'''            crate::captive::set_socks(None);'''),
    ('src/ui_interface.rs',
     r'''            Config::set_socks(Some(socks));''',
     r'''            crate::captive::set_socks(Some(socks));'''),
    # flutter/macos/Runner/Configs/AppInfo.xcconfig
    ('flutter/macos/Runner/Configs/AppInfo.xcconfig',
     r'''PRODUCT_NAME = RustDesk''',
     r'''PRODUCT_NAME = @APP@'''),
    ('flutter/macos/Runner/Configs/AppInfo.xcconfig',
     r'''PRODUCT_BUNDLE_IDENTIFIER = com.carriez.flutterHbb''',
     r'''PRODUCT_BUNDLE_IDENTIFIER = @BUNDLE@'''),
    # flutter/macos/Runner.xcodeproj/project.pbxproj
    ('flutter/macos/Runner.xcodeproj/project.pbxproj',
     r'''PRODUCT_BUNDLE_IDENTIFIER = com.carriez.rustdesk;''',
     r'''PRODUCT_BUNDLE_IDENTIFIER = @BUNDLE@;''',
     3),
    # flutter/macos/Runner/Info.plist
    ('flutter/macos/Runner/Info.plist',
     r'''<string>com.carriez.rustdesk</string>''',
     r'''<string>@BUNDLE@</string>'''),
    ('flutter/macos/Runner/Info.plist',
     r'''<array>
				<string>rustdesk</string>''',
     r'''<array>
				<string>@APP_LOWER@</string>'''),
    # Cargo.toml
    ('Cargo.toml',
     r'''[package.metadata.bundle]
name = "RustDesk"
identifier = "com.carriez.rustdesk"''',
     r'''[package.metadata.bundle]
name = "@APP@"
identifier = "@BUNDLE@"'''),
]
