import Foundation

struct BookingRequest: Codable {
    var name: String = ""
    var postcode: String = ""
    var propertyType: String = "house"
    var tenure: String = "own"
    var productInterest: String = "solar"
    var contactMethod: String = "email"
    var preferredTime: String = "flexible"
    var notes: String = ""

    enum CodingKeys: String, CodingKey {
        case name
        case postcode
        case propertyType = "property_type"
        case tenure
        case productInterest = "product_interest"
        case contactMethod = "contact_method"
        case preferredTime = "preferred_time"
        case notes
    }
}

struct BookingResponse: Codable {
    let bookingId: String
    let status: String
    let message: String

    enum CodingKeys: String, CodingKey {
        case bookingId = "booking_id"
        case status
        case message
    }
}
