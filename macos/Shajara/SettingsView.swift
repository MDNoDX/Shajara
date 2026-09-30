import SwiftUI

struct SettingsView: View {
    @EnvironmentObject var browser: Browser
    @AppStorage("server") private var server = Browser.defaultServer
    @AppStorage("notifications") private var notifications = true

    var body: some View {
        Form {
            Section {
                TextField("Sayt manzili", text: $server, prompt: Text(Browser.defaultServer))
                    .textFieldStyle(.roundedBorder)
                    .frame(minWidth: 380)
                HStack {
                    Button("Standart manzil") { server = Browser.defaultServer }
                    Spacer()
                    Button("Saqlash va ochish") { browser.goHome() }.keyboardShortcut(.defaultAction)
                }
            } header: {
                Text("Server")
            } footer: {
                Text("Saytni boshqa serverga koʻchirsangiz, bu yerga yangi manzilni yozing.")
                    .font(.caption).foregroundStyle(.secondary)
            }
            Section("Bildirishnomalar") {
                Toggle("Tugʻilgan kunlar va voqealar haqida xabar berish", isOn: $notifications)
                    .onChange(of: notifications) { value in Notifier.shared.enabled = value }
            }
        }
        .formStyle(.grouped)
        .padding(8)
        .frame(width: 520)
    }
}
