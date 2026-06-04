import Foundation
import SwiftUI

@MainActor
class ChatViewModel: ObservableObject {

    @Published var messages: [ChatMessage] = []
    @Published var inputText: String = ""
    @Published var isLoading: Bool = false
    @Published var errorMessage: String? = nil
    @Published var showBookingSheet: Bool = false

    private let api = APIService()
    private(set) var sessionId: String? = nil

    init() {
        // Welcome message
        messages.append(ChatMessage(
            role: .assistant,
            text: "Hi! I'm the EcoHome AI Assistant. I can help you with solar panels, home batteries, EV chargers, smart thermostats, grants, and booking a free consultation. What would you like to know?"
        ))
    }

    func sendMessage() async {
        let text = inputText.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !text.isEmpty, !isLoading else { return }

        // Add user message
        let userMessage = ChatMessage(role: .user, text: text)
        messages.append(userMessage)
        inputText = ""
        isLoading = true
        errorMessage = nil

        do {
            let response = try await api.sendMessage(message: text, sessionId: sessionId)
            sessionId = response.sessionId

            let assistantMessage = ChatMessage(
                role: .assistant,
                text: response.reply,
                sources: response.sources,
                latencyMs: response.latencyMs
            )
            messages.append(assistantMessage)

            // Trigger booking sheet if structured command detected
            if response.structuredCommand == "BOOK_CONSULTATION" {
                DispatchQueue.main.asyncAfter(deadline: .now() + 0.5) {
                    self.showBookingSheet = true
                }
            }
        } catch {
            errorMessage = error.localizedDescription
            messages.append(ChatMessage(
                role: .system,
                text: "Sorry, I couldn't get a response. Please check your connection and try again."
            ))
        }

        isLoading = false
    }

    func submitFeedback(for message: ChatMessage, rating: Int) async {
        guard let sessionId else { return }
        await api.submitFeedback(
            sessionId: sessionId,
            messageId: message.id.uuidString,
            rating: rating
        )
    }

    func submitBooking(_ booking: BookingRequest) async throws -> BookingResponse {
        return try await api.submitBooking(booking)
    }

    func clearConversation() {
        messages = []
        sessionId = nil
        messages.append(ChatMessage(
            role: .assistant,
            text: "Hi! I'm the EcoHome AI Assistant. How can I help you today?"
        ))
    }
}

