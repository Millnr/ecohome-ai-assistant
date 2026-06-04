import Foundation

struct ChatRequest: Codable {
    let message: String
    let sessionId: String?

    enum CodingKeys: String, CodingKey {
        case message
        case sessionId = "session_id"
    }
}

struct ChatResponse: Codable {
    let reply: String
    let sessionId: String
    let structuredCommand: String?
    let sources: [String]
    let latencyMs: Int

    enum CodingKeys: String, CodingKey {
        case reply
        case sessionId = "session_id"
        case structuredCommand = "structured_command"
        case sources
        case latencyMs = "latency_ms"
    }
}

struct FeedbackRequest: Codable {
    let sessionId: String
    let messageId: String
    let rating: Int
    let comment: String?

    enum CodingKeys: String, CodingKey {
        case sessionId = "session_id"
        case messageId = "message_id"
        case rating
        case comment
    }
}

enum APIError: LocalizedError {
    case invalidURL
    case networkError(Error)
    case decodingError(Error)
    case serverError(Int)
    case unknown

    var errorDescription: String? {
        switch self {
        case .invalidURL:         return "Invalid server URL"
        case .networkError(let e): return "Network error: \(e.localizedDescription)"
        case .decodingError:      return "Unexpected response from server"
        case .serverError(let c): return "Server error (\(c))"
        case .unknown:            return "An unknown error occurred"
        }
    }
}

class APIService: ObservableObject {

    // ── Change this to your machine's LAN IP when testing on a real device ──
    static let baseURL = "http://localhost:8000"

    private let session = URLSession.shared
    private let decoder: JSONDecoder = {
        let d = JSONDecoder()
        return d
    }()
    private let encoder: JSONEncoder = {
        let e = JSONEncoder()
        return e
    }()

    func sendMessage(message: String, sessionId: String?) async throws -> ChatResponse {
        guard let url = URL(string: "\(Self.baseURL)/chat") else { throw APIError.invalidURL }

        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        request.timeoutInterval = 60

        let body = ChatRequest(message: message, sessionId: sessionId)
        request.httpBody = try encoder.encode(body)

        let (data, response) = try await session.data(for: request)

        if let http = response as? HTTPURLResponse, http.statusCode != 200 {
            throw APIError.serverError(http.statusCode)
        }

        do {
            return try decoder.decode(ChatResponse.self, from: data)
        } catch {
            throw APIError.decodingError(error)
        }
    }

    func submitFeedback(sessionId: String, messageId: String, rating: Int) async {
        guard let url = URL(string: "\(Self.baseURL)/feedback") else { return }
        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        let body = FeedbackRequest(sessionId: sessionId, messageId: messageId, rating: rating, comment: nil)
        request.httpBody = try? encoder.encode(body)
        _ = try? await session.data(for: request)
    }

    func submitBooking(_ booking: BookingRequest) async throws -> BookingResponse {
        guard let url = URL(string: "\(Self.baseURL)/booking") else { throw APIError.invalidURL }
        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        request.httpBody = try encoder.encode(booking)

        let (data, response) = try await session.data(for: request)
        if let http = response as? HTTPURLResponse, http.statusCode != 200 {
            throw APIError.serverError(http.statusCode)
        }
        return try decoder.decode(BookingResponse.self, from: data)
    }
}
