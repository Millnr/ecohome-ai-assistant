//
//  ContentView.swift
//  EcoHomeApp
//
//  Created by sdina on 05/05/2026.
//

import SwiftUI

struct ContentView: View {
    @StateObject private var viewModel = ChatViewModel()
    @FocusState private var inputFocused: Bool

    var body: some View {
        NavigationStack {
            VStack(spacing: 0) {

                // ── Message list ───────────────────────────────────────────
                ScrollViewReader { proxy in
                    ScrollView {
                        LazyVStack(spacing: 0) {
                            ForEach(viewModel.messages) { message in
                                MessageBubble(
                                    message: message,
                                    onThumbsUp: {
                                        Task { await viewModel.submitFeedback(for: message, rating: 1) }
                                    },
                                    onThumbsDown: {
                                        Task { await viewModel.submitFeedback(for: message, rating: -1) }
                                    }
                                )
                                .id(message.id)
                            }

                            if viewModel.isLoading {
                                TypingIndicator()
                                    .id("typing")
                            }
                        }
                        .padding(.top, 8)
                        .padding(.bottom, 8)
                    }
                    .onChange(of: viewModel.messages.count) { _ in
                        scrollToBottom(proxy: proxy)
                    }
                    .onChange(of: viewModel.isLoading) { _ in
                        scrollToBottom(proxy: proxy)
                    }
                    .onAppear {
                        scrollToBottom(proxy: proxy)
                    }
                }

                Divider()

                // ── Input bar ──────────────────────────────────────────────
                HStack(alignment: .bottom, spacing: 10) {
                    TextField("Ask about solar, batteries, EV chargers...", text: $viewModel.inputText, axis: .vertical)
                        .lineLimit(1...5)
                        .padding(.horizontal, 12)
                        .padding(.vertical, 8)
                        .background(Color(.secondarySystemBackground))
                        .clipShape(RoundedRectangle(cornerRadius: 20, style: .continuous))
                        .focused($inputFocused)

                    Button {
                        Task { await viewModel.sendMessage() }
                    } label: {
                        Image(systemName: "arrow.up.circle.fill")
                            .font(.system(size: 32))
                            .foregroundColor(
                                viewModel.inputText.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty || viewModel.isLoading
                                    ? .secondary : .ecoGreen
                            )
                    }
                    .disabled(
                        viewModel.inputText.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty || viewModel.isLoading
                    )
                }
                .padding(.horizontal, 12)
                .padding(.vertical, 8)
                .background(Color(.systemBackground))
            }
            .navigationTitle("EcoHome Assistant")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .navigationBarLeading) {
                    Image(systemName: "leaf.circle.fill")
                        .foregroundColor(.ecoGreen)
                        .font(.title3)
                }
                ToolbarItem(placement: .navigationBarTrailing) {
                    Button {
                        viewModel.clearConversation()
                    } label: {
                        Image(systemName: "square.and.pencil")
                            .foregroundColor(.ecoGreen)
                    }
                }
            }
            .sheet(isPresented: $viewModel.showBookingSheet) {
                BookingView(viewModel: viewModel)
            }
        }
    }

    private func scrollToBottom(proxy: ScrollViewProxy) {
        withAnimation(.easeOut(duration: 0.2)) {
            if viewModel.isLoading {
                proxy.scrollTo("typing", anchor: .bottom)
            } else if let last = viewModel.messages.last {
                proxy.scrollTo(last.id, anchor: .bottom)
            }
        }
    }
}

#Preview {
    ContentView()
}
