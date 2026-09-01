# TWDS Alpha release checklist

This checklist applies to the protected Alpha branch candidate. It does not establish what is deployed to Alpha.

## Public “What's New” gate — blocking

Before approving an Alpha public-website release, an administrator must open **Admin → Communications** and verify all three cards: **Recently Updated**, **What We're Working On**, and **Commercial Launch**.

- [ ] Each card has a non-empty public title, plain-language summary, and release label.
- [ ] Each card shows **Public-information content reviewed** and **Approved to show publicly**.
- [ ] Each card's status is `approved`, and its last-updated date matches the intended content review.
- [ ] The public homepage is checked at desktop and mobile widths; every card shows its release label and last-updated date.
- [ ] No card exposes branch names, commit SHAs, internal validation notes, unapproved dates, customer information, or other non-public operational detail.
- [ ] `GET /api/suite/whats-new` reports `public_ready: true` for all three card keys.

Any empty, draft, unreviewed, or unpublished card is a release blocker. The safe public fallback (“No approved update” / “Last updated: Not published”) is intentional behavior, not approval to release unnoticed.
