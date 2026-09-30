import SwiftUI
import WebKit

/// Shajara for macOS: the family-tree site in a native window, with system
/// notifications, a dock badge, file downloads and Google sign-in.
@main
struct ShajaraApp: App {
    @NSApplicationDelegateAdaptor(AppDelegate.self) private var appDelegate
    @StateObject private var browser = Browser.shared

    var body: some Scene {
        WindowGroup {
            ContentView()
                .environmentObject(browser)
                .frame(minWidth: 960, minHeight: 640)
        }
        .defaultSize(width: 1320, height: 860)
        .windowToolbarStyle(.unified(showsTitle: true))
        .commands {
            CommandGroup(replacing: .newItem) {}
            CommandMenu("Koʻrinish") {
                Button("Yangilash") { browser.reload() }.keyboardShortcut("r")
                Button("Orqaga") { browser.goBack() }.keyboardShortcut("[")
                Button("Oldinga") { browser.goForward() }.keyboardShortcut("]")
                Button("Bosh sahifa") { browser.goHome() }.keyboardShortcut("h", modifiers: [.command, .shift])
                Divider()
                Button("Kattalashtirish") { browser.zoom(by: 0.1) }.keyboardShortcut("+")
                Button("Kichiklashtirish") { browser.zoom(by: -0.1) }.keyboardShortcut("-")
                Button("Asl oʻlcham") { browser.resetZoom() }.keyboardShortcut("0")
            }
            CommandMenu("Shajara") {
                Button("Shajaram") { browser.open(path: "/shajara/") }.keyboardShortcut("1")
                Button("Qarindoshlarim") { browser.open(path: "/qarindoshlar/") }.keyboardShortcut("2")
                Button("Voqealar") { browser.open(path: "/voqealar/") }.keyboardShortcut("3")
                Button("Doʻstlarim") { browser.open(path: "/dostlar/") }.keyboardShortcut("4")
                Button("Qidiruv") { browser.open(path: "/qidiruv/") }.keyboardShortcut("f")
                Divider()
                Button("Brauzerda ochish") { browser.openInBrowser() }
            }
        }

        Settings {
            SettingsView().environmentObject(browser)
        }
    }
}

final class AppDelegate: NSObject, NSApplicationDelegate {
    func applicationDidFinishLaunching(_ notification: Notification) {
        Notifier.shared.start()
    }

    func applicationShouldTerminateAfterLastWindowClosed(_ sender: NSApplication) -> Bool { true }

    func applicationDidBecomeActive(_ notification: Notification) {
        Notifier.shared.checkSoon()
    }
}

struct ContentView: View {
    @EnvironmentObject var browser: Browser

    var body: some View {
        ZStack(alignment: .top) {
            WebView(browser: browser)
                .ignoresSafeArea()
            if browser.isLoading {
                ProgressView(value: browser.progress)
                    .progressViewStyle(.linear)
                    .tint(Color(red: 0.36, green: 0.28, blue: 0.79))
                    .frame(height: 2)
            }
            if let message = browser.errorMessage {
                OfflineView(message: message) { browser.reload() }
            }
        }
        .navigationTitle(browser.title.isEmpty ? "Shajara" : browser.title)
        .toolbar {
            ToolbarItemGroup(placement: .navigation) {
                Button(action: browser.goBack) { Image(systemName: "chevron.left") }
                    .disabled(!browser.canGoBack).help("Orqaga")
                Button(action: browser.goForward) { Image(systemName: "chevron.right") }
                    .disabled(!browser.canGoForward).help("Oldinga")
            }
            ToolbarItemGroup(placement: .primaryAction) {
                Button(action: browser.goHome) { Image(systemName: "house") }.help("Bosh sahifa")
                Button { browser.open(path: "/shajara/") } label: { Image(systemName: "tree") }.help("Shajaram")
                Button(action: browser.reload) { Image(systemName: "arrow.clockwise") }.help("Yangilash")
            }
        }
    }
}

struct OfflineView: View {
    let message: String
    let retry: () -> Void

    var body: some View {
        VStack(spacing: 14) {
            Image(systemName: "wifi.exclamationmark").font(.system(size: 44)).foregroundStyle(.secondary)
            Text("Saytga ulanib boʻlmadi").font(.title2.bold())
            Text(message).foregroundStyle(.secondary).multilineTextAlignment(.center).frame(maxWidth: 420)
            Button("Qayta urinish", action: retry).keyboardShortcut(.defaultAction)
        }
        .padding(40)
        .frame(maxWidth: .infinity, maxHeight: .infinity)
        .background(.background)
    }
}
