// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 OpenFollow Project
import Foundation
import Security

enum ConnectionError: LocalizedError {
    case invalidAddress
    case privateNetworkRequired
    case authentication
    case server(Int, String)
    case unexpectedResponse

    var errorDescription: String? {
        switch self {
        case .invalidAddress: return "Escribí la dirección del PC y su puerto, por ejemplo http://IP_DEL_PC:8080."
        case .privateNetworkRequired: return "Para HTTP usá la IP privada o la IP de Tailscale del PC. Para una dirección pública se requiere HTTPS."
        case .authentication: return "El PIN de OpenFollow falta o es incorrecto."
        case .server(let code, let message): return "OpenFollow respondió \(code): \(message)"
        case .unexpectedResponse: return "El PC no respondió con datos de OpenFollow. Revisá la dirección y el puerto."
        }
    }
}

private final class RedirectPolicy: NSObject, URLSessionTaskDelegate, @unchecked Sendable {
    func urlSession(
        _ session: URLSession, task: URLSessionTask,
        willPerformHTTPRedirection response: HTTPURLResponse,
        newRequest request: URLRequest, completionHandler: @escaping (URLRequest?) -> Void
    ) {
        completionHandler(nil)
    }
}

actor OpenFollowClient {
    private var baseURL: URL?
    private var session: URLSession?

    static func address(_ input: String) throws -> URL {
        let trimmed = input.trimmingCharacters(in: .whitespacesAndNewlines)
        let value = trimmed.contains("://") ? trimmed : "http://" + trimmed
        guard var parts = URLComponents(string: value),
              let host = parts.host, !host.isEmpty,
              parts.user == nil, parts.password == nil,
              parts.query == nil, parts.fragment == nil,
              parts.path.isEmpty || parts.path == "/",
              parts.scheme == "https" || parts.scheme == "http",
              parts.port.map({ (1...65535).contains($0) }) ?? true else {
            throw ConnectionError.invalidAddress
        }
        if parts.scheme == "http" {
            let components = host.split(separator: ".", omittingEmptySubsequences: false)
            let bytes = components.compactMap { UInt8($0) }
            guard components.count == 4, bytes.count == 4,
                  bytes[0] == 10 || (bytes[0] == 172 && (16...31).contains(bytes[1]))
                    || (bytes[0] == 192 && bytes[1] == 168)
                    || (bytes[0] == 100 && (64...127).contains(bytes[1])) else {
                throw ConnectionError.privateNetworkRequired
            }
        }
        if parts.port == nil && parts.scheme == "http" { parts.port = 8080 }
        parts.path = "/"
        guard let url = parts.url else { throw ConnectionError.invalidAddress }
        return url
    }

    func connect(address: String, pin: String) async throws -> JSONValue {
        disconnect()
        baseURL = try Self.address(address)
        let configuration = URLSessionConfiguration.ephemeral
        configuration.timeoutIntervalForRequest = 10
        configuration.timeoutIntervalForResource = 15
        configuration.requestCachePolicy = .reloadIgnoringLocalCacheData
        configuration.urlCache = nil
        configuration.httpShouldSetCookies = true
        session = URLSession(configuration: configuration, delegate: RedirectPolicy(), delegateQueue: nil)
        do {
            return try await json("api/info")
        } catch ConnectionError.authentication {
            guard !pin.isEmpty else { throw ConnectionError.authentication }
            var components = URLComponents()
            components.queryItems = [URLQueryItem(name: "pin", value: pin)]
            let form = (components.percentEncodedQuery ?? "").replacingOccurrences(of: "+", with: "%2B")
            _ = try await request("login", method: "POST", body: Data(form.utf8), contentType: "application/x-www-form-urlencoded", acceptRedirect: true)
            return try await json("api/info")
        }
    }

    func disconnect() {
        session?.invalidateAndCancel()
        session = nil
        baseURL = nil
    }

    func json(_ path: String, method: String = "GET", value: JSONValue? = nil) async throws -> JSONValue {
        let body = try value.map { try JSONEncoder().encode($0) }
        let data = try await request(path, method: method, body: body)
        guard let result = try? JSONDecoder().decode(JSONValue.self, from: data) else {
            throw ConnectionError.unexpectedResponse
        }
        if !result["error"].text.isEmpty { throw ConnectionError.server(400, result["error"].text) }
        return result
    }

    func preview() async throws -> Data {
        try await request("api/video/snapshot")
    }

    private func request(
        _ path: String, method: String = "GET", body: Data? = nil,
        contentType: String = "application/json", acceptRedirect: Bool = false
    ) async throws -> Data {
        guard let baseURL, let session, let url = URL(string: path, relativeTo: baseURL)?.absoluteURL else {
            throw ConnectionError.invalidAddress
        }
        var request = URLRequest(url: url)
        request.httpMethod = method
        request.httpBody = body
        request.setValue("no-store", forHTTPHeaderField: "Cache-Control")
        if body != nil { request.setValue(contentType, forHTTPHeaderField: "Content-Type") }
        let (data, response) = try await session.data(for: request)
        guard let http = response as? HTTPURLResponse else { throw ConnectionError.unexpectedResponse }
        if http.statusCode == 401 { throw ConnectionError.authentication }
        if acceptRedirect && http.statusCode == 303 { return data }
        guard (200...299).contains(http.statusCode) else {
            let detail = (try? JSONDecoder().decode(JSONValue.self, from: data))?["error"].text
            throw ConnectionError.server(http.statusCode, detail ?? "No se pudo completar la operación.")
        }
        return data
    }
}

enum PINStore {
    private static let service = "OpenFollowMobile.connection"

    static func read(address: String) -> String {
        let query: [String: Any] = [
            kSecClass as String: kSecClassGenericPassword,
            kSecAttrService as String: service,
            kSecAttrAccount as String: address,
            kSecReturnData as String: true,
            kSecMatchLimit as String: kSecMatchLimitOne
        ]
        var result: CFTypeRef?
        guard SecItemCopyMatching(query as CFDictionary, &result) == errSecSuccess,
              let data = result as? Data else { return "" }
        return String(data: data, encoding: .utf8) ?? ""
    }

    static func save(_ pin: String, address: String) throws {
        let query: [String: Any] = [
            kSecClass as String: kSecClassGenericPassword,
            kSecAttrService as String: service,
            kSecAttrAccount as String: address
        ]
        let deletion = SecItemDelete(query as CFDictionary)
        guard deletion == errSecSuccess || deletion == errSecItemNotFound else {
            throw ConnectionError.server(Int(deletion), "No se pudo guardar el PIN en el llavero.")
        }
        guard !pin.isEmpty else { return }
        var item = query
        item[kSecValueData as String] = Data(pin.utf8)
        item[kSecAttrAccessible as String] = kSecAttrAccessibleWhenUnlockedThisDeviceOnly
        let status = SecItemAdd(item as CFDictionary, nil)
        guard status == errSecSuccess else {
            throw ConnectionError.server(Int(status), "No se pudo guardar el PIN en el llavero.")
        }
    }
}
