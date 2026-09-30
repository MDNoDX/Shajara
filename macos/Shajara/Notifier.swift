import AppKit
import UserNotifications

/// Checks the site for unread reminders (birthdays, events …), shows them as
/// macOS notifications and keeps the dock badge up to date.
final class Notifier: NSObject, UNUserNotificationCenterDelegate {
    static let shared = Notifier()
    private var timer: Timer?
    private var pending: DispatchWorkItem?
    private let seenKey = "seenNotificationIDs"

    var enabled: Bool {
        get { UserDefaults.standard.object(forKey: "notifications") as? Bool ?? true }
        set { UserDefaults.standard.set(newValue, forKey: "notifications"); if newValue { requestPermission() } }
    }

    func start() {
        UNUserNotificationCenter.current().delegate = self
        if enabled { requestPermission() }
        timer = Timer.scheduledTimer(withTimeInterval: 15 * 60, repeats: true) { [weak self] _ in self?.check() }
    }

    func requestPermission() {
        UNUserNotificationCenter.current().requestAuthorization(options: [.alert, .sound, .badge]) { _, _ in }
    }

    /// Several triggers (page loads, app activation) are merged into one check.
    func checkSoon() {
        pending?.cancel()
        let work = DispatchWorkItem { [weak self] in self?.check() }
        pending = work
        DispatchQueue.main.asyncAfter(deadline: .now() + 2, execute: work)
    }

    func check() {
        let js = """
        const r = await fetch('/xabarlar/holat.json', {credentials: 'same-origin', headers: {Accept: 'application/json'}});
        if (!r.ok || r.redirected) return null;
        return await r.text();
        """
        Browser.shared.webView.callAsyncJavaScript(js, arguments: [:], in: nil, in: .page) { [weak self] result in
            guard let self, case .success(let value) = result, let text = value as? String,
                  let data = text.data(using: .utf8),
                  let status = try? JSONDecoder().decode(Status.self, from: data) else { return }
            NSApp.dockTile.badgeLabel = status.unread > 0 ? String(status.unread) : nil
            guard self.enabled else { return }
            var seen = Set(UserDefaults.standard.array(forKey: self.seenKey) as? [Int] ?? [])
            for item in status.items where !seen.contains(item.id) {
                let content = UNMutableNotificationContent()
                content.title = "\(item.icon) \(item.title)"
                content.body = item.body
                content.sound = .default
                content.userInfo = ["url": item.url]
                UNUserNotificationCenter.current().add(
                    UNNotificationRequest(identifier: "shajara-\(item.id)", content: content, trigger: nil))
                seen.insert(item.id)
            }
            UserDefaults.standard.set(Array(seen.suffix(500)), forKey: self.seenKey)
        }
    }

    // Clicking a notification opens it in the app.
    func userNotificationCenter(_ center: UNUserNotificationCenter, didReceive response: UNNotificationResponse,
                                withCompletionHandler completionHandler: @escaping () -> Void) {
        if let link = response.notification.request.content.userInfo["url"] as? String, let url = URL(string: link) {
            DispatchQueue.main.async {
                NSApp.activate(ignoringOtherApps: true)
                Browser.shared.load(url)
            }
        }
        completionHandler()
    }

    func userNotificationCenter(_ center: UNUserNotificationCenter, willPresent notification: UNNotification,
                                withCompletionHandler completionHandler: @escaping (UNNotificationPresentationOptions) -> Void) {
        completionHandler([.banner, .sound])
    }

    private struct Status: Decodable {
        let unread: Int
        let items: [Item]
        struct Item: Decodable { let id: Int; let url: String; let title: String; let body: String; let icon: String }
    }
}
