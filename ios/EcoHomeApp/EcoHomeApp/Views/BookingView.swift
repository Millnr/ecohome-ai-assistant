import SwiftUI

struct BookingView: View {
    @Environment(\.dismiss) private var dismiss
    @ObservedObject var viewModel: ChatViewModel

    @State private var booking = BookingRequest()
    @State private var isSubmitting = false
    @State private var confirmationMessage: String? = nil
    @State private var showError = false
    @State private var errorText = ""

    var body: some View {
        NavigationStack {
            Form {
                // ── Confirmation banner ────────────────────────────────────
                if let confirmation = confirmationMessage {
                    Section {
                        VStack(alignment: .leading, spacing: 8) {
                            Label("Booking Confirmed", systemImage: "checkmark.seal.fill")
                                .font(.headline)
                                .foregroundColor(.ecoGreen)
                            Text(confirmation)
                                .font(.body)
                        }
                        .padding(.vertical, 4)
                    }
                }

                // ── Personal details ───────────────────────────────────────
                Section("Your Details") {
                    TextField("Full name", text: $booking.name)
                        .textContentType(.name)
                    TextField("Postcode", text: $booking.postcode)
                        .textContentType(.postalCode)
                        .autocapitalization(.allCharacters)
                }

                // ── Property ───────────────────────────────────────────────
                Section("Property") {
                    Picker("Property type", selection: $booking.propertyType) {
                        Text("House").tag("house")
                        Text("Flat").tag("flat")
                        Text("Bungalow").tag("bungalow")
                        Text("Other").tag("other")
                    }
                    Picker("Ownership", selection: $booking.tenure) {
                        Text("I own it").tag("own")
                        Text("I rent it").tag("rent")
                    }
                }

                // ── Interest ───────────────────────────────────────────────
                Section("I'm interested in") {
                    Picker("Product", selection: $booking.productInterest) {
                        Text("Solar panels").tag("solar")
                        Text("Home battery").tag("battery")
                        Text("EV charger").tag("ev-charger")
                        Text("Smart thermostat").tag("thermostat")
                        Text("Multiple / not sure").tag("multiple")
                    }
                }

                // ── Contact preferences ────────────────────────────────────
                Section("Contact Preferences") {
                    Picker("Contact me by", selection: $booking.contactMethod) {
                        Text("Email").tag("email")
                        Text("Phone").tag("phone")
                    }
                    Picker("Best time", selection: $booking.preferredTime) {
                        Text("Morning").tag("morning")
                        Text("Afternoon").tag("afternoon")
                        Text("Flexible").tag("flexible")
                    }
                }

                // ── Notes ──────────────────────────────────────────────────
                Section("Additional Notes (optional)") {
                    TextField("e.g. south-facing roof, already have solar...", text: $booking.notes, axis: .vertical)
                        .lineLimit(3...6)
                }

                // ── Submit ─────────────────────────────────────────────────
                Section {
                    Button {
                        Task { await submit() }
                    } label: {
                        HStack {
                            Spacer()
                            if isSubmitting {
                                ProgressView()
                            } else {
                                Text("Request Free Consultation")
                                    .bold()
                            }
                            Spacer()
                        }
                    }
                    .disabled(isSubmitting || booking.name.isEmpty || booking.postcode.isEmpty || confirmationMessage != nil)
                    .foregroundColor(confirmationMessage != nil ? .secondary : .ecoGreen)
                }

                // ── Disclaimer ─────────────────────────────────────────────
                Section {
                    Text("EcoHome will contact you within 2 business hours during Monday–Friday 8am–6pm, Saturday 9am–1pm. No obligation.")
                        .font(.caption)
                        .foregroundColor(.secondary)
                }
            }
            .navigationTitle("Book a Consultation")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button("Close") { dismiss() }
                }
            }
            .alert("Something went wrong", isPresented: $showError) {
                Button("OK", role: .cancel) {}
            } message: {
                Text(errorText)
            }
        }
    }

    private func submit() async {
        isSubmitting = true
        do {
            let response = try await viewModel.submitBooking(booking)
            confirmationMessage = response.message
            // Auto-dismiss after showing confirmation
            DispatchQueue.main.asyncAfter(deadline: .now() + 3.0) {
                dismiss()
            }
        } catch {
            errorText = error.localizedDescription
            showError = true
        }
        isSubmitting = false
    }
}
