# Booking a Consultation

## Overview
EcoHome offers free, no-obligation consultations for homeowners and renters interested in solar panels, home batteries, EV chargers, or smart thermostats. A consultation helps determine what system is right for your home and what grants or incentives you may be eligible for.

---

## How to Book

When a user is ready to book, the assistant should trigger the structured command:

```
[BOOK_CONSULTATION]
```

This command initiates the booking form flow in the EcoHome app.

---

## Information Required for Booking

The following details are collected during the booking flow:

| Field | Notes |
|---|---|
| Full name | |
| Postcode | Used to assess local installer availability and grant eligibility |
| Property type | House / Flat / Bungalow / Other |
| Own or rent | Some grants differ for renters |
| Product interest | Solar / Battery / EV Charger / Smart Thermostat / Multiple |
| Preferred contact method | Phone / Email |
| Preferred time slot | Morning / Afternoon / Flexible |
| Additional notes | Optional — e.g. "south-facing roof", "already have solar" |

---

## What Happens After Booking

1. EcoHome confirms the booking by email within 2 hours (during business hours)
2. An advisor calls or emails at the agreed time
3. The consultation covers:
   - Your property and energy usage
   - Recommended system(s) for your situation
   - Indicative pricing and savings estimate
   - Grant and incentive eligibility
   - Next steps if you wish to proceed

**No obligation to purchase.** The consultation is entirely free.

---

## Important Guardrails

> **The assistant must NOT recommend a specific installer by name.**
> When a user asks for installer recommendations, direct them to:
> - MCS Certified Installer Finder: https://mcscertified.com/find-an-installer/
> - Energy Saving Trust Installer Finder: https://energysavingtrust.org.uk/advice/find-an-installer/
>
> EcoHome advisors can discuss finding an MCS-certified installer, but the AI assistant should never endorse a named third-party installer.

---

## Edge Cases

**User wants to book for a rental property:**
Acknowledge that some grant rules differ for renters (e.g. OZEV EV grant is available to renters; some grants require landlord consent). Capture this in the "own or rent" field and notes. An advisor will discuss specifics.

**User is unsure which product they need:**
Encourage them to select "Multiple" or "Not sure" in the product interest field. The advisor will help identify the best starting point.

**User asks to book outside business hours:**
The booking form is available 24/7. An advisor will respond on the next business day. Business hours: Monday–Friday 8am–6pm, Saturday 9am–1pm.

**User asks about availability in their area:**
EcoHome operates across England, Scotland, and Wales. Coverage in remote rural areas may be limited — capture the postcode and the advisor will confirm at consultation.

---

## What to Expect at a Consultation

- Duration: approximately 30–45 minutes
- Format: phone call or video call (in-person surveys are a separate follow-up step)
- Preparation tips for the customer:
  - Know your approximate monthly electricity bill
  - Have a rough idea of your roof orientation (which way it faces) if interested in solar
  - Know whether you own or rent your property
  - Have your postcode ready

---

## Frequently Asked Questions

**Is the consultation really free?**
Yes. There is no charge and no obligation. EcoHome makes money when customers choose to install — we have no incentive to give you bad advice.

**Will I be pressured to buy?**
No. Our advisors are trained to give honest recommendations. If solar isn't right for your property or budget, they will tell you.

**Can I book for a friend or family member?**
Yes. Enter the property owner's or occupier's details in the form and note in the additional comments that you are booking on their behalf.

**How soon can I get an appointment?**
Most consultations are booked within 3–5 working days. For urgent enquiries, call our team directly.

## Sources
- MCS Find an Installer: https://mcscertified.com/find-an-installer/
- Energy Saving Trust — Find an Installer: https://energysavingtrust.org.uk/advice/find-an-installer/
- GOV.UK — Get Help to Upgrade Your Home: https://www.gov.uk/improve-energy-efficiency
