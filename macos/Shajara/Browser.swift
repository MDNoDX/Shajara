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

    let webView: WKWebView
    private var observers: [NSKeyValueObservation] = []
    private var authSession: ASWebAuthenticationSession?

    var server: URL {
        let saved = UserDefaults.standard.string(forKey: "server") ?? Browser.defaultServer
        return URL(string: saved.trimmingCharacters(in: .whitespaces)) ?? URL(string: Browser.defaultServer)!
    }

    override init() {
        let config = WKWebViewConfiguration()
        config.websiteDataStore = .default()          // keeps you signed in between launches
        config.preferences.isElementFullscreenEnabled = true
        webView = WKWebView(frame: .zero, configuration: config)
        webView.customUserAgent = nil
        webView.allowsBackForwardNavigationGestures = true
        webView.allowsMagnification = true
        if #available(macOS 13.3, *) { webView.isInspectable = true }
        super.init()
        webView.evaluateJavaScript("navigator.userAgent") { [weak self] result, _ in
            if let ua = result as? String { self?.webView.customUserAgent = ua + " ShajaraMac/1.0" }
        }
        observers = [
            webView.observe(\.title) { [weak self] v, _ in self?.title = v.title ?? "" },
            webView.observe(\.canGoBack) { [weak self] v, _ in self?.canGoBack = v.canGoBack },
            webView.observe(\.canGoForward) { [weak self] v, _ in self?.canGoForward = v.canGoForward },
            webView.observe(\.isLoading) { [weak self] v, _ in self?.isLoading = v.isLoading },
            webView.observe(\.estimatedProgress) { [weak self] v, _ in self?.progress = v.estimatedProgress },
        ]
        goHome()
    }

    // MARK: Navigation

    func open(path: String) { load(URL(string: path, relativeTo: server)!.absoluteURL) }
    func load(_ url: URL) { errorMessage = nil; webView.load(URLRequest(url: url)) }
    func goHome() { open(path: "/") }
    func goBack() { webView.goBack() }
    func goForward() { webView.goForward() }
    func reload() {
        errorMessage = nil
        if webView.url == nil { goHome() } else { webView.reload() }
    }
    func zoom(by delta: CGFloat) { webView.pageZoom = max(0.5, min(2.5, webView.pageZoom + delta)) }
    func resetZoom() { webView.pageZoom = 1 }
    func openInBrowser() { NSWorkspace.shared.open(webView.url ?? server) }

    func isOwnSite(_ url: URL) -> Bool {
        url.host == server.host || url.scheme == "blob" || url.scheme == "data" || url.scheme == "about"
    }

    // MARK: Sign in with Google (in the system sign-in window)

    func signInWithGoogle() {
        var parts = URLComponents(url: URL(string: "/ilova/kirish/boshlash/", relativeTo: server)!.absoluteURL,
                                  resolvingAgainstBaseURL: true)!
        parts.queryItems = [URLQueryItem(name: "provider", value: "google")]
        let session = ASWebAuthenticationSession(url: parts.url!, callbackURLScheme: "shajara") { [weak self] url, _ in
            guard let self, let url,
                  let token = URLComponents(url: url, resolvingAgainstBaseURL: false)?
                    .queryItems?.first(where: { $0.name == "token" })?.value else { return }
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
}

extension Browser: ASWebAuthenticationPresentationContextProviding {
    func presentationAnchor(for session: ASWebAuthenticationSession) -> ASPresentationAnchor {
        NSApp.keyWindow ?? NSApp.windows.first ?? ASPresentationAnchor()
    }
}
