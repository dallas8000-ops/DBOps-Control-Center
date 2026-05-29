# License sale model — exclusive vs non-exclusive

Use this guide to choose how you sell **before** listing on a marketplace or sending term sheets. Then align [`DBOps_LICENSE.md`](../../DBOps_LICENSE.md) and checkout copy with the chosen model.

---

## Quick comparison

| | **Non-exclusive** (default) | **Exclusive** |
|---|---------------------------|---------------|
| **Buyers** | Many | One |
| **Typical price** | Lower per sale ($6k–$20k tiers) | Higher single sale ($25k–$60k+ negotiable) |
| **You retain IP** | Yes | Yes, unless **assignment** negotiated |
| **Buyer can resell source** | No (per license variants) | No — same restrictions unless OEM deal |
| **Your future sales** | Continue selling to others | Stop selling same codebase to others |
| **Best for** | Gumroad, agency templates, repeatable revenue | Strategic acquirer, single OEM, exit-style deal |

---

## Recommended default: **non-exclusive**

**How it works**

- Each purchaser gets a **Variant 1** (internal) or **Variant 2** (agency, up to 3 clients) license from `DBOps_LICENSE.md`.
- You keep copyright; buyer gets perpetual use of the **delivered version** subject to restrictions.
- You may sell many licenses; buyers may not redistribute source.

**Listing language (example)**

> Non-exclusive commercial source license. You receive deployable source for your organization (or up to three client projects on Agency terms). Seller may license the same product to other buyers. Redistribution and resale of source prohibited.

**Pricing:** Use [pricing-sheet.md](./pricing-sheet.md) / [ONE_PAGE_PITCH.md](./ONE_PAGE_PITCH.md) tiers.

---

## When to offer **exclusive**

**How it works**

- **One buyer** receives assurance you will not license the same product to others for a defined period or forever.
- Implement via **written exclusive license agreement** (not only the standard `DBOps_LICENSE.md` — add an **Exclusive License Addendum** signed by both parties).
- Optionally include **assignment of copyright** (buyer owns IP) — much higher price, lawyer required.

**Listing language (example)**

> Exclusive commercial license available by written agreement. Buyer receives sole right to market/deploy this codebase as licensed; seller ceases licensing to third parties for the term stated in the addendum. Price and support terms quoted separately.

**Pricing guidance (starting points — adjust with counsel)**

| Scope | Indicative range |
|--------|------------------|
| Exclusive license, seller retains copyright | $35,000 – $75,000 |
| Exclusive + 12 months updates/support | +$15,000 – $30,000 |
| Copyright assignment (full buyout) | $75,000 – $150,000+ |

---

## Mapping to `DBOps_LICENSE.md` variants

| Variant | Non-exclusive? | Notes |
|---------|----------------|--------|
| **Variant 1 — Internal Use** | ✓ Standard | Single org, no redistribution |
| **Variant 2 — Consultant / Agency** | ✓ Standard | Up to 3 end clients |
| **Variant 3 — Enterprise / OEM** | ✓ Custom quote | Unlimited clients or embedding |
| **Exclusive addendum** | Exclusive only | Supersedes seller’s right to license others |

---

## Action items before listing

1. **Pick default:** Non-exclusive for public listing; exclusive “contact for quote.”
2. **Update marketplace copy** to state non-exclusive unless buyer signs exclusive addendum.
3. **Stripe/Gumroad product** description: link `DBOps_LICENSE.md` + variant purchased.
4. **Keep a sales log** of buyer email + variant + date (prove exclusive buyer if you later offer exclusivity to someone else).
5. **Attorney review** for first exclusive or assignment deal.

---

## Exclusive addendum (outline — not legal advice)

Attach to order for exclusive deals:

1. Grant of exclusive commercial license to Named Buyer for the Software version tag `vX.Y.Z`.
2. Seller covenant not to license, sell, or distribute the Software to any third party for [perpetual / N years].
3. Exceptions: seller may maintain private repo for portfolio proof only if disclosed — or no exception.
4. Price, payment schedule, delivery method (private repo invite / encrypted archive).
5. Updates included: [90 days / none / custom].
6. Governing law (Florida per base license).
7. Signatures.

---

*Pair with [ONE_PAGE_PITCH.md](./ONE_PAGE_PITCH.md) and [REMAINING_5_PERCENT.md](./REMAINING_5_PERCENT.md).*
