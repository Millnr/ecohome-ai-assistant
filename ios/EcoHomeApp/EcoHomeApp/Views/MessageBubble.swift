import SwiftUI

struct MessageBubble: View {
    let message: ChatMessage
    let onThumbsUp: () -> Void
    let onThumbsDown: () -> Void

    @State private var feedbackGiven: Int? = nil

    private var isUser: Bool { message.role == .user }
    private var isSystem: Bool { message.role == .system }

    var body: some View {
        HStack(alignment: .bottom, spacing: 8) {
            if isUser { Spacer(minLength: 48) }

            VStack(alignment: isUser ? .trailing : .leading, spacing: 4) {

                // ── Bubble ─────────────────────────────────────────────────
                Text(message.text)
                    .padding(.horizontal, 14)
                    .padding(.vertical, 10)
                    .background(bubbleBackground)
                    .foregroundColor(isUser ? .white : .black.opacity(0.85))
                    .clipShape(RoundedRectangle(cornerRadius: 18, style: .continuous))
                    .font(.body)
                    .shadow(color: .black.opacity(0.15), radius: 4, x: 0, y: 2)

                // ── Sources + feedback (assistant only) ────────────────────
                if !isUser && !isSystem {
                    HStack(spacing: 12) {
                        if !message.sources.isEmpty {
                            HStack(spacing: 4) {
                                Image(systemName: "doc.text")
                                    .font(.caption2)
                                Text(message.sources.joined(separator: ", "))
                                    .font(.caption2)
                            }
                            .foregroundColor(.secondary)
                        }

                        Spacer()

                        // Thumbs up/down
                        HStack(spacing: 8) {
                            Button {
                                feedbackGiven = 1
                                onThumbsUp()
                            } label: {
                                Image(systemName: feedbackGiven == 1 ? "hand.thumbsup.fill" : "hand.thumbsup")
                                    .font(.caption)
                                    .foregroundColor(feedbackGiven == 1 ? .ecoGreen : .secondary)
                            }
                            Button {
                                feedbackGiven = -1
                                onThumbsDown()
                            } label: {
                                Image(systemName: feedbackGiven == -1 ? "hand.thumbsdown.fill" : "hand.thumbsdown")
                                    .font(.caption)
                                    .foregroundColor(feedbackGiven == -1 ? .red : .secondary)
                            }
                        }
                    }
                    .padding(.horizontal, 4)
                }
            }

            if !isUser { Spacer(minLength: 48) }
        }
        .padding(.horizontal, 12)
        .padding(.vertical, 2)
    }

    @ViewBuilder
    private var bubbleBackground: some View {
        if isUser {
            Color.ecoGreen
        } else if isSystem {
            Color.orange.opacity(0.75)
        } else {
            // Assistant bubble: clearly white frosted
            Color.white.opacity(0.82)
        }
    }
}

extension Color {
    static let ecoGreen = Color(red: 0.18, green: 0.56, blue: 0.34)
}
