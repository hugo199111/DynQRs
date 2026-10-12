// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 OpenFollow Project
import SwiftUI

struct MarkerEntry: Decodable, Identifiable {
    let id: Int
    let name: String
    let color: String
}

@MainActor
final class ConnectionModel: ObservableObject {
    @Published var address = UserDefaults.standard.string(forKey: "pcAddress") ?? ""
    @Published var connected = false
    @Published var busy = false
    @Published var errorMessage = ""
    @Published var stationName = "OpenFollow"
    @Published var version = ""
    @Published var preview: UIImage?
    @Published var previewMessage = ""
    @Published var stats: JSONValue = .object([:])
    @Published var markers: [MarkerEntry] = []
    @Published var controlledIDs: [Int] = []
    @Published var viewerIDs: [Int] = []
    @Published var connectionID = UUID()
    @Published var selectionRevision = 0
    let client = OpenFollowClient()

    func connect(pin: String) async {
        guard !busy else { return }
        busy = true
        connected = false
        preview = nil
        stats = .object([:])
        markers = []
        controlledIDs = []
        viewerIDs = []
        errorMessage = ""
        defer { busy = false }
        do {
            let normalized = try OpenFollowClient.address(address).absoluteString
            let info = try await client.connect(address: normalized, pin: pin)
            guard !info["name"].text.isEmpty, !info["version"].text.isEmpty else {
                throw ConnectionError.unexpectedResponse
            }
            address = normalized
            stationName = info["name"].text
            version = info["version"].text
            try PINStore.save(pin, address: normalized)
            UserDefaults.standard.set(normalized, forKey: "pcAddress")
            connectionID = UUID()
            connected = true
        } catch {
            await client.disconnect()
            errorMessage = error.localizedDescription
        }
    }

    func disconnect() async {
        connectionID = UUID()
        connected = false
        preview = nil
        stats = .object([:])
        markers = []
        controlledIDs = []
        viewerIDs = []
        await client.disconnect()
    }

    func poll() async {
        let activeID = connectionID
        var cycle = 0
        while connected && activeID == connectionID && !Task.isCancelled {
            do {
                let latest = try await client.json("api/stats")
                guard activeID == connectionID, !Task.isCancelled else { return }
                stats = latest
                if cycle % 3 == 0 {
                    let revision = selectionRevision
                    let catalog = try await client.json("api/markers/catalog")
                    guard activeID == connectionID, !Task.isCancelled else { return }
                    let data = try JSONEncoder().encode(catalog["entries"])
                    markers = try JSONDecoder().decode([MarkerEntry].self, from: data)
                    if selectionRevision == revision {
                        controlledIDs = catalog["this_station"]["controlled_ids"].array.map { Int($0.number) }
                        viewerIDs = catalog["this_station"]["viewer_ids"].array.map { Int($0.number) }
                    }
                }
            } catch {
                guard activeID == connectionID, !Task.isCancelled else { return }
                errorMessage = error.localizedDescription
                connected = false
                preview = nil
                return
            }
            do {
                let data = try await client.preview()
                guard activeID == connectionID, !Task.isCancelled else { return }
                guard let frame = UIImage(data: data) else { throw ConnectionError.unexpectedResponse }
                preview = frame
                previewMessage = ""
            } catch ConnectionError.server(let code, _) where code == 503 {
                preview = nil
                previewMessage = "OpenFollow todavía no tiene una imagen de vídeo disponible."
            } catch {
                guard activeID == connectionID, !Task.isCancelled else { return }
                preview = nil
                previewMessage = error.localizedDescription
            }
            cycle += 1
            do { try await Task.sleep(for: .seconds(1)) }
            catch { return }
        }
    }

    func saveSelection(controlled: [Int], viewed: [Int]) async throws {
        let activeID = connectionID
        selectionRevision += 1
        let value: JSONValue = .object([
            "controlled_ids": .array(controlled.map { .number(Double($0)) }),
            "viewer_ids": .array(viewed.map { .number(Double($0)) })
        ])
        _ = try await client.json("api/markers/selection", method: "POST", value: value)
        guard connected, activeID == connectionID else { return }
        selectionRevision += 1
        controlledIDs = controlled
        viewerIDs = viewed + controlled.filter { !viewed.contains($0) }
    }
}

struct ConfigSection: Identifiable {
    let id: String
    let title: String
    let symbol: String

    static let all: [ConfigSection] = [
        .init(id: "video_source", title: "Fuente de vídeo", symbol: "video"),
        .init(id: "psn", title: "Salida PSN", symbol: "antenna.radiowaves.left.and.right"),
        .init(id: "osc", title: "OSC", symbol: "waveform.path"),
        .init(id: "otp_output", title: "Salida OTP", symbol: "network"),
        .init(id: "rttrpm_output", title: "Salida RTTrPM", symbol: "network"),
        .init(id: "camera", title: "Cámara y calibración", symbol: "camera"),
        .init(id: "grid", title: "Escenario y cuadrícula", symbol: "square.grid.3x3"),
        .init(id: "movement", title: "Movimiento", symbol: "move.3d"),
        .init(id: "marker", title: "Apariencia de marcadores", symbol: "scope"),
        .init(id: "controller", title: "Mandos, teclado y ratón", symbol: "gamecontroller"),
        .init(id: "mouse3d", title: "Ratón 3D", symbol: "computermouse"),
        .init(id: "detection", title: "Detección y seguimiento", symbol: "person.crop.rectangle"),
        .init(id: "trigger_zones", title: "Zonas de activación", symbol: "square.dashed"),
        .init(id: "operator_messages", title: "Mensajes del operador", symbol: "text.bubble")
    ]

    func editable(_ name: String) -> Bool {
        let local = ["source_iface", "listen_iface", "storage_path", "video_input_iface", "testpattern_selected_media"]
        if local.contains(name) { return false }
        let movement = ["min_speed", "max_speed", "move_speed", "default_pos_x", "default_pos_y", "default_pos_z", "invert_control_direction"]
        if id == "movement" { return movement.contains(name) }
        if id == "marker" { return !movement.contains(name) }
        return true
    }
}

@MainActor
final class ConfigDocument: ObservableObject {
    @Published var value: JSONValue = .object([:])
    @Published var loaded = false
    @Published var saving = false
    @Published var errorMessage = ""
    @Published var saved = false
    private var original: JSONValue = .object([:])
    private var loadedConnection: UUID?

    func load(_ section: ConfigSection, model: ConnectionModel) async {
        let activeID = model.connectionID
        do {
            let data = try await model.client.json("api/config/" + section.id)
            guard model.connected, model.connectionID == activeID, !Task.isCancelled else { return }
            value = .object(data.object.filter { section.editable($0.key) })
            original = value
            loadedConnection = activeID
            loaded = true
        } catch {
            guard !Task.isCancelled else { return }
            errorMessage = error.localizedDescription
        }
    }

    func save(_ section: ConfigSection, model: ConnectionModel) async {
        guard !saving, loadedConnection == model.connectionID, model.connected else { return }
        saving = true
        saved = false
        errorMessage = ""
        defer { saving = false }
        let pending = value
        let changed = pending.object.filter { original[$0.key] != $0.value }
        guard !changed.isEmpty else { saved = true; return }
        do {
            _ = try await model.client.json("api/config/" + section.id, method: "POST", value: .object(changed))
            guard loadedConnection == model.connectionID, model.connected else { return }
            let actual = try await model.client.json("api/config/" + section.id)
            value = .object(actual.object.filter { section.editable($0.key) })
            original = value
            saved = true
        } catch { errorMessage = error.localizedDescription }
    }
}
