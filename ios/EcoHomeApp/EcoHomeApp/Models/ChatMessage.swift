import Foundation

enum MessageRole {
    case user
    case assistant
    case system
}

struct ChatMessage: Identifiable, Equatable {
    let id: UUID
    let role: MessageRole
    let text: String
    let sources: [String]
    let latencyMs: Int?
    let timestamp: Date

    init(
        id: UUID = UUID(),
        role: MessageRole,
        text: String,
        sources: [String] = [],
        latencyMs: Int? = nil,
        timestamp: Date = Date()
    ) {
        self.id = id
        self.role = role
        self.text = text
        self.sources = sources
        self.latencyMs = latencyMs
        self.timestamp = timestamp
    }
}
