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
            ZStack {
                // ── Background ─────────────────────────────────────────────
                backgroundLayer

                // ── Chat UI ────────────────────────────────────────────────
                VStack(spacing: 0) {
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
                        .onChange(of: viewModel.messages.count) { scrollToBottom(proxy: proxy) }
                        .onChange(of: viewModel.isLoading) { scrollToBottom(proxy: proxy) }
                        .onAppear { scrollToBottom(proxy: proxy) }
                    }

                    Divider()
                        .background(Color.white.opacity(0.3))

                    // ── Input bar ──────────────────────────────────────────
                    HStack(alignment: .bottom, spacing: 10) {
                        TextField("Ask about solar, batteries, EV chargers...", text: $viewModel.inputText, axis: .vertical)
                            .lineLimit(1...5)
                            .padding(.horizontal, 12)
                            .padding(.vertical, 8)
                            .background(.ultraThinMaterial)
                            .clipShape(RoundedRectangle(cornerRadius: 20, style: .continuous))
                            .focused($inputFocused)

                        Button {
                            let text = viewModel.inputText
                            viewModel.inputText = ""
                            inputFocused = false
                            Task { await viewModel.sendMessage(withText: text) }
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
                    .background(.ultraThinMaterial)
                }
            }
            .navigationTitle("EcoHome Assistant")
            .navigationBarTitleDisplayMode(.inline)
            .toolbarBackground(.ultraThinMaterial, for: .navigationBar)
            .toolbarColorScheme(.dark, for: .navigationBar)
            .toolbar {
                ToolbarItem(placement: .navigationBarLeading) {
                    HStack(spacing: 6) {
                        Image(systemName: "leaf.circle.fill")
                            .foregroundColor(.ecoGreen)
                            .font(.title3)
                    }
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
            // ── Session end prompt ─────────────────────────────────────────
            .alert("End of Session", isPresented: $viewModel.showSessionEndPrompt) {
                Button("Start New Chat") { viewModel.clearConversation() }
                Button("Stay", role: .cancel) {}
            } message: {
                Text("Would you like to start a new conversation?")
            }
        }
    }

    // ── Background: gradient fallback if no image asset ────────────────────
    @ViewBuilder
    private var backgroundLayer: some View {
        if let uiImage = UIImage(named: "EcoBackground") {
            GeometryReader { geo in
                Image(uiImage: uiImage)
                    .resizable()
                    .scaledToFill()
                    .frame(width: geo.size.width, height: geo.size.height)
                    .clipped()
                    .overlay(
                        Color.black.opacity(0.45)
                    )
            }
            .ignoresSafeArea()
        } else {
            // Fallback gradient when no image asset is present
            LinearGradient(
                colors: [
                    Color(red: 0.07, green: 0.22, blue: 0.14),
                    Color(red: 0.12, green: 0.38, blue: 0.22),
                    Color(red: 0.22, green: 0.55, blue: 0.34)
                ],
                startPoint: .topLeading,
                endPoint: .bottomTrailing
            )
            .ignoresSafeArea()
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
