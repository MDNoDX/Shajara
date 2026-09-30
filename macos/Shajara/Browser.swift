import AppKit
import AuthenticationServices
import Combine
import WebKit

/// Owns the web view and everything the app does around it.
final class Browser: NSObject, ObservableObject {
    static let shared = Browser()
    static let defaultServer = "https://shajara-liard.vercel.app"

    @Published var title = ""
    @Published var canGoBack = false
    @Published var canGoForward = false
    @Published var isLoading = false
    @Published var progress = 0.0
    @Published var errorMessage: String?
    @Published var language: AppLanguage

    let webView: WKWebView
    private var observers: [NSKeyValueObservation] = []
    private var authSession: ASWebAuthenticationSession?
    private let defaults = UserDefaults.standard

    var server: URL {
        let saved = defaults.string(forKey: "server") ?? Browser.defaultServer
        var text = saved.trimmingCharacters(in: .whitespacesAndNewlines)
        if !text.contains("://") { text = "https://" + text }
        return URL(string: text) ?? URL(string: Browser.defaultServer)!
    }

    override init() {
        language = AppLanguage(rawValue: UserDefaults.standard.string(forKey: "language") ?? "") ?? .system
        let config = WKWebViewConfiguration()
        config.websiteDataStore = .default()          // keeps you signed in between launches
        config.preferences.isElementFullscreenEnabled = true
        config.applicationNameForUserAgent = "ShajaraMac/1.1"
        webView = WKWebView(frame: .zero, configuration: config)
        webView.allowsBackForwardNavigationGestures = true
        webView.allowsMagnification = true
        if #available(macOS 13.3, *) { webView.isInspectable = true }
        super.init()
        let zoom = defaults.double(forKey: "zoom")
        if zoom > 0 { webView.pageZoom = zoom }
        observers = [
            webView.observe(\.title) { [weak self] v, _ in self?.title = v.title ?? "" },
            webView.observe(\.canGoBack) { [weak self] v, _ in self?.canGoBack = v.canGoBack },
            webView.observe(\.canGoForward) { [weak self] v, _ in self?.canGoForward = v.canGoForward },
            webView.observe(\.isLoading) { [weak self] v, _ in self?.isLoading = v.isLoading },
            webView.observe(\.estimatedProgress) { [weak self] v, _ in self?.progress = v.estimatedProgress },
        ]
        restore()
    }

    // MARK: Navigation

    /// Reopen the page you were on last time (on the same site), else the home page.
    private func restore() {
        if let last = defaults.url(forKey: "lastURL"), last.host == server.host, !last.path.hasPrefix("/ilova/") {
            load(last)
        } else {
            goHome()
        }
    }

    func open(path: String) { load(URL(string: path, relativeTo: server)!.absoluteURL) }
    func load(_ url: URL) { errorMessage = nil; webView.load(URLRequest(url: url)) }
    func goHome() { open(path: "/") }
    func goBack() { webView.goBack() }
    func goForward() { webView.goForward() }
    func reload() {
        errorMessage = nil
        if webView.url == nil { goHome() } else { webView.reload() }
    }
    func zoom(by delta: CGFloat) { setZoom(webView.pageZoom + delta) }
    func resetZoom() { setZoom(1) }
    private func setZoom(_ value: CGFloat) {
        webView.pageZoom = max(0.5, min(2.5, value))
        defaults.set(Double(webView.pageZoom), forKey: "zoom")
    }
    func openInBrowser() { NSWorkspace.shared.open(webView.url ?? server) }

    func isOwnSite(_ url: URL) -> Bool {
        url.host == server.host || ["blob", "data", "about"].contains(url.scheme ?? "")
    }

    /// Called when a page has finished loading.
    func pageLoaded() {
        errorMessage = nil
        if let url = webView.url, url.host == server.host { defaults.set(url, forKey: "lastURL") }
        webView.evaluateJavaScript("document.documentElement.lang") { [weak self] result, _ in
            guard let self, let lang = (result as? String).flatMap(AppLanguage.init(htmlLang:)), lang != self.language else { return }
            self.language = lang
            self.defaults.set(lang.rawValue, forKey: "language")
        }
    }

    func printPage() {
        guard let window = webView.window else { return }
        let info = NSPrintInfo.shared
        info.horizontalPagination = .fit
        info.verticalPagination = .automatic
        info.isHorizontallyCentered = true
        let operation = webView.printOperation(with: info)
        operation.view?.frame = webView.bounds
        operation.runModal(for: window, delegate: nil, didRun: nil, contextInfo: nil)
    }

    // MARK: Sign in with Google (in the system sign-in window)

    func signInWithGoogle() {
        var parts = URLComponents(url: URL(string: "/ilova/kirish/boshlash/", relativeTo: server)!.absoluteURL,
                                  resolvingAgainstBaseURL: true)!
        parts.queryItems = [URLQueryItem(name: "provider", value: "google")]
        let session = ASWebAuthenticationSession(url: parts.url!, callbackURLScheme: "shajara") { [weak self] url, error in
            guard let self else { return }
            if let error = error as? ASWebAuthenticationSessionError, error.code == .canceledLogin { return }
            guard let url,
                  let token = URLComponents(url: url, resolvingAgainstBaseURL: false)?
                    .queryItems?.first(where: { $0.name == "token" })?.value else {
                DispatchQueue.main.async { self.alert(L.t("loginFailed")) }
                return
            }
            var login = URLComponents(url: URL(string: "/ilova/kirish/", relativeTo: self.server)!.absoluteURL,
                                      resolvingAgainstBaseURL: true)!
            login.queryItems = [URLQueryItem(name: "token", value: token)]
            DispatchQueue.main.async { self.load(login.url!) }
        }
        session.presentationContextProvider = self
        session.prefersEphemeralWebBrowserSession = false
        authSession = session
        session.start()
    }

    /// Linking Google to an existing account needs the site session, which
    /// the system sign-in window does not have: that step is done in the browser.
    func connectGoogleInBrowser() {
        alert(L.t("connectGoogleInBrowser"))
        NSWorkspace.shared.open(URL(string: "/sozlamalar/xavfsizlik/#google", relativeTo: server)!.absoluteURL)
    }

    func alert(_ text: String) {
        let alert = NSAlert()
        alert.messageText = text
        alert.addButton(withTitle: L.t("ok"))
        if let window = webView.window { alert.beginSheetModal(for: window) } else { alert.runModal() }
    }
}

extension Browser: ASWebAuthenticationPresentationContextProviding {
    func presentationAnchor(for session: ASWebAuthenticationSession) -> ASPresentationAnchor {
        NSApp.keyWindow ?? NSApp.windows.first ?? ASPresentationAnchor()
    }
}
