// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 OpenFollow Project
import SwiftUI

enum AppTheme {
    static let background = Color(red: 7 / 255, green: 19 / 255, blue: 13 / 255)
    static let accent = Color(red: 1, green: 188 / 255, blue: 0)
}

@main
struct OpenFollowMobileApp: App {
    @StateObject private var model = ConnectionModel()

    var body: some Scene {
        WindowGroup {
            RootView()
                .environmentObject(model)
                .tint(AppTheme.accent)
                .preferredColorScheme(.dark)
        }
    }
}

struct RootView: View {
    @EnvironmentObject private var model: ConnectionModel
    @Environment(\.scenePhase) private var scenePhase
    @State private var showingConnection = false

    var body: some View {
        TabView {
            NavigationStack { DashboardView(showingConnection: $showingConnection) }
                .tabItem { Label("Inicio", systemImage: "scope") }
            NavigationStack { VideoView() }
                .tabItem { Label("Vídeo", systemImage: "video") }
            NavigationStack { MarkersView() }
                .tabItem { Label("Marcadores", systemImage: "mappin.and.ellipse") }
            NavigationStack { SettingsView() }
                .tabItem { Label("Ajustes", systemImage: "slider.horizontal.3") }
        }
        .sheet(isPresented: $showingConnection) { ConnectionView() }
        .task(id: "\(model.connectionID)-\(model.connected)-\(scenePhase)") {
            if model.connected && scenePhase == .active { await model.poll() }
        }
    }
}

struct DashboardView: View {
    @EnvironmentObject private var model: ConnectionModel
    @Binding var showingConnection: Bool

    var body: some View {
        List {
            Section {
                HStack(spacing: 14) {
                    Image(systemName: "scope").font(.system(size: 38)).foregroundStyle(AppTheme.accent)
                    VStack(alignment: .leading, spacing: 4) {
                        Text(model.stationName).font(.title2.bold())
                        Label(model.connected ? "Conectado al PC" : "Sin conexión", systemImage: model.connected ? "checkmark.circle.fill" : "wifi.slash")
                            .foregroundStyle(model.connected ? .green : .secondary)
                    }
                }
                Button(model.connected ? "Cambiar conexión" : "Conectar al PC") { showingConnection = true }
                if !model.errorMessage.isEmpty {
                    Text(model.errorMessage).foregroundStyle(.orange)
                }
            }
            if model.connected {
                Section("Vista del vídeo") {
                    PreviewFrame()
                    NavigationLink("Abrir vídeo", destination: VideoView())
                }
                Section("Estado") {
                    LabeledContent("Vídeo", value: model.stats["video"]["connected"].bool ? "Conectado" : "Sin señal")
                    LabeledContent("Fuente", value: model.stats["video"]["source_type"].text)
                    LabeledContent("FPS de la fuente", value: model.stats["video"]["source_fps"].text)
                    LabeledContent("Mandos conectados", value: model.stats["controllers"]["connected_count"].text)
                    LabeledContent("Seguimiento", value: model.stats["tracking"]["running"].bool ? "Activo" : "Inactivo")
                    LabeledContent("CPU", value: model.stats["system"]["cpu_percent"].text + "%")
                    LabeledContent("Versión del PC", value: model.version)
                }
                Section("Accesos") {
                    ForEach(ConfigSection.all.filter { ["psn", "osc", "detection", "grid"].contains($0.id) }) { section in
                        NavigationLink(destination: ConfigSectionView(section: section)) {
                            Label(section.title, systemImage: section.symbol)
                        }
                    }
                }
            } else {
                Section {
                    Text("Conectá OpenFollow con la dirección de tu PC. Por Internet, activá Tailscale en ambos dispositivos y usá la IP de Tailscale del PC.")
                        .foregroundStyle(.secondary)
                }
            }
        }
        .scrollContentBackground(.hidden)
        .background(AppTheme.background)
        .navigationTitle("OpenFollow")
    }
}

struct ConnectionView: View {
    @EnvironmentObject private var model: ConnectionModel
    @Environment(\.dismiss) private var dismiss
    @State private var address = ""
    @State private var pin = ""

    var body: some View {
        NavigationStack {
            Form {
                Section("Tu PC") {
                    TextField("http://IP_DEL_PC:8080", text: $address)
                        .keyboardType(.URL).textContentType(.URL)
                        .textInputAutocapitalization(.never).autocorrectionDisabled()
                    SecureField("PIN de OpenFollow, si está configurado", text: $pin)
                        .keyboardType(.numberPad)
                }
                Section {
                    Button {
                        Task {
                            model.address = address
                            await model.connect(pin: pin)
                            if model.connected { dismiss() }
                        }
                    } label: {
                        HStack {
                            Text("Conectar")
                            if model.busy { Spacer(); ProgressView() }
                        }
                    }
                    .disabled(model.busy || address.trimmingCharacters(in: .whitespaces).isEmpty)
                    if model.connected {
                        Button("Desconectar", role: .destructive) {
                            Task { await model.disconnect(); dismiss() }
                        }
                        .disabled(model.busy)
                    }
                    if !model.errorMessage.isEmpty { Text(model.errorMessage).foregroundStyle(.orange) }
                }
                Section("Conexión por Internet") {
                    Text("Activá Tailscale en Windows y en el iPhone con la misma cuenta. Escribí arriba la IP de Tailscale del PC y el puerto de OpenFollow. El PC debe estar encendido con OpenFollow abierto.")
                    Link("Tailscale para Windows", destination: URL(string: "https://tailscale.com/download/windows")!)
                    Link("Tailscale para iPhone", destination: URL(string: "https://tailscale.com/download/ios")!)
                }
            }
            .scrollContentBackground(.hidden)
            .background(AppTheme.background)
            .navigationTitle("Conexión")
            .toolbar {
                ToolbarItem(placement: .cancellationAction) { Button("Cerrar") { dismiss() }.disabled(model.busy) }
            }
            .onAppear {
                address = model.address
                pin = PINStore.read(address: model.address)
            }
            .onChange(of: address) { _, updated in
                let normalized = (try? OpenFollowClient.address(updated))?.absoluteString ?? updated
                pin = PINStore.read(address: normalized)
            }
            .interactiveDismissDisabled(model.busy)
        }
    }
}

struct PreviewFrame: View {
    @EnvironmentObject private var model: ConnectionModel

    var body: some View {
        Group {
            if let frame = model.preview, model.connected {
                Image(uiImage: frame).resizable().scaledToFit()
                    .accessibilityLabel("Fotograma del vídeo de OpenFollow")
            } else {
                VStack(spacing: 12) {
                    Image(systemName: "video.slash").font(.largeTitle)
                    Text(model.connected ? (model.previewMessage.isEmpty ? "Esperando imagen del PC" : model.previewMessage) : "Conectá el PC para ver el vídeo")
                        .multilineTextAlignment(.center).foregroundStyle(.secondary)
                }
                .frame(maxWidth: .infinity, minHeight: 180)
            }
        }
        .background(.black)
        .clipShape(RoundedRectangle(cornerRadius: 12))
    }
}

struct VideoView: View {
    @EnvironmentObject private var model: ConnectionModel
    var body: some View {
        ScrollView {
            VStack(spacing: 20) {
                PreviewFrame()
                if model.connected {
                    Text("Vista actualizada por fotogramas desde tu PC.").font(.footnote).foregroundStyle(.secondary)
                    Text(model.stats["video"]["source_label"].text)
                    if !model.stats["video"]["error_message"].text.isEmpty {
                        Text(model.stats["video"]["error_message"].text).foregroundStyle(.orange)
                    }
                }
            }
            .padding()
        }
        .background(AppTheme.background)
        .navigationTitle("Vídeo")
    }
}

struct MarkersView: View {
    @EnvironmentObject private var model: ConnectionModel
    @State private var saving = false
    @State private var error = ""

    var body: some View {
        List {
            if !model.connected {
                Text("Conectá el PC para acceder a sus marcadores.").foregroundStyle(.secondary)
            } else {
                if !error.isEmpty { Text(error).foregroundStyle(.orange) }
                if model.markers.isEmpty { Text("Todavía no hay marcadores registrados en el PC.") }
                ForEach(model.markers) { marker in
                    Section("\(marker.id) · \(marker.name)") {
                        Toggle("Controlar en este PC", isOn: Binding(
                            get: { model.controlledIDs.contains(marker.id) },
                            set: { selected in update(marker.id, selected: selected, controlling: true) }
                        ))
                        Toggle("Mostrar en este PC", isOn: Binding(
                            get: { model.viewerIDs.contains(marker.id) },
                            set: { selected in update(marker.id, selected: selected, controlling: false) }
                        ))
                        .disabled(model.controlledIDs.contains(marker.id))
                    }
                    .disabled(saving)
                }
                Section {
                    Text("Los marcadores controlados también se muestran. La selección se aplica al OpenFollow del PC.")
                        .font(.footnote).foregroundStyle(.secondary)
                }
            }
        }
        .scrollContentBackground(.hidden)
        .background(AppTheme.background)
        .navigationTitle("Marcadores")
    }

    private func update(_ id: Int, selected: Bool, controlling: Bool) {
        guard !saving, model.connected else { return }
        var controlled = model.controlledIDs
        var viewed = model.viewerIDs
        if controlling {
            if selected && !controlled.contains(id) { controlled.append(id) }
            if !selected { controlled.removeAll { $0 == id } }
        } else {
            if selected && !viewed.contains(id) { viewed.append(id) }
            if !selected { viewed.removeAll { $0 == id } }
        }
        saving = true
        error = ""
        Task {
            defer { saving = false }
            do { try await model.saveSelection(controlled: controlled, viewed: viewed) }
            catch { self.error = error.localizedDescription }
        }
    }
}

struct SettingsView: View {
    @EnvironmentObject private var model: ConnectionModel
    var body: some View {
        List {
            Section("OpenFollow en el PC") {
                ForEach(ConfigSection.all) { section in
                    NavigationLink(destination: ConfigSectionView(section: section)) {
                        Label(section.title, systemImage: section.symbol)
                    }
                    .disabled(!model.connected)
                }
            }
            Section("Acerca de") {
                Text("OpenFollow para iPhone").font(.headline)
                Text("Cliente nativo de OpenFollow. El vídeo, el seguimiento y las salidas se procesan en el PC.")
                Link("Código fuente y licencia", destination: URL(string: "https://github.com/hugo199111/DynQRs/tree/openfollow-windows/openfollow")!)
                Text("AGPL-3.0-or-later · OpenFollow Project").font(.footnote).foregroundStyle(.secondary)
            }
        }
        .scrollContentBackground(.hidden)
        .background(AppTheme.background)
        .navigationTitle("Ajustes")
    }
}

struct ConfigSectionView: View {
    @EnvironmentObject private var model: ConnectionModel
    @StateObject private var document = ConfigDocument()
    let section: ConfigSection

    var body: some View {
        Form {
            if !model.connected {
                Text("El PC se desconectó. Volvé a conectarlo antes de guardar cambios.").foregroundStyle(.orange)
            } else if !document.loaded && document.errorMessage.isEmpty {
                ProgressView("Cargando ajustes del PC")
            }
            if document.loaded {
                JSONFields(value: $document.value)
                    .disabled(document.saving || !model.connected)
                Section {
                    Button("Guardar en el PC") { Task { await document.save(section, model: model) } }
                        .disabled(document.saving || !model.connected)
                    if document.saving { ProgressView() }
                    if document.saved { Text("Respuesta recibida. Se muestran los valores actuales del PC.").foregroundStyle(.green) }
                }
            }
            if !document.errorMessage.isEmpty { Text(document.errorMessage).foregroundStyle(.orange) }
        }
        .scrollContentBackground(.hidden)
        .background(AppTheme.background)
        .navigationTitle(section.title)
        .task(id: model.connectionID) { await document.load(section, model: model) }
    }
}

struct JSONFields: View {
    @Binding var value: JSONValue

    var body: some View {
        ForEach(value.object.keys.sorted(), id: \.self) { key in
            JSONField(title: fieldTitle(key), value: Binding(
                get: { value[key] }, set: { value[key] = $0 }
            ))
        }
    }
}

struct JSONField: View {
    let title: String
    @Binding var value: JSONValue

    var body: some View {
        switch value {
        case .bool:
            Toggle(title, isOn: Binding(get: { value.bool }, set: { value = .bool($0) }))
        case .number:
            NumberField(title: title, value: $value)
        case .string:
            VStack(alignment: .leading, spacing: 4) {
                Text(title).font(.caption).foregroundStyle(.secondary)
                TextField(title, text: Binding(get: { value.text }, set: { value = .string($0) }))
                    .textInputAutocapitalization(.never).autocorrectionDisabled()
            }
        case .object:
            NavigationLink(title) {
                AnyView(Form { JSONFields(value: $value) }.navigationTitle(title))
            }
        case .array:
            NavigationLink(title) {
                AnyView(Form {
                    ForEach(value.array.indices, id: \.self) { index in
                        JSONField(title: "\(index + 1)", value: Binding(
                            get: { value.array.indices.contains(index) ? value.array[index] : .null },
                            set: { updated in
                                var array = value.array
                                guard array.indices.contains(index) else { return }
                                array[index] = updated
                                value = .array(array)
                            }
                        ))
                    }
                }.navigationTitle(title))
            }
        case .null:
            LabeledContent(title, value: "Sin definir")
        }
    }
}

struct NumberField: View {
    let title: String
    @Binding var value: JSONValue
    @State private var text = ""
    @State private var invalid = false

    var body: some View {
        VStack(alignment: .leading, spacing: 4) {
            Text(title).font(.caption).foregroundStyle(.secondary)
            TextField(title, text: $text)
                .keyboardType(.numbersAndPunctuation)
                .onAppear { text = value.text }
                .onChange(of: text) { _, updated in
                    if let number = Double(updated.replacingOccurrences(of: ",", with: ".")), number.isFinite {
                        invalid = false
                        value = .number(number)
                    } else { invalid = true }
                }
                .onChange(of: value) { _, updated in
                    if !invalid, Double(text.replacingOccurrences(of: ",", with: ".")) != updated.number {
                        text = updated.text
                    }
                }
            if invalid { Text("Escribí un número válido.").font(.caption).foregroundStyle(.orange) }
        }
    }
}

private func fieldTitle(_ key: String) -> String {
    let labels = [
        "enabled": "Activado", "visible": "Visible", "psn_system_name": "Nombre del sistema",
        "psn_mcast_ip": "Dirección multicast PSN", "video_source_type": "Tipo de fuente de vídeo",
        "width": "Ancho", "depth": "Profundidad", "spacing": "Separación", "color": "Color",
        "move_speed": "Velocidad de movimiento", "min_speed": "Velocidad mínima",
        "max_speed": "Velocidad máxima", "port": "Puerto", "listen_port": "Puerto de entrada",
        "model": "Modelo", "interval_ms": "Intervalo (ms)", "transparency": "Transparencia"
    ]
    return labels[key] ?? key.replacingOccurrences(of: "_", with: " ").capitalized
}
