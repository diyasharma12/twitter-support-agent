# How to fill in to_label.csv

Fill the `intent` column with one of these names (or its number):

- `0` **rebooking_change** — Wants to change, rebook or cancel a flight, or is asking why a change was handled the way it was. Includes missed connections.
- `1` **delay_cancellation** — Reporting or asking about a delayed, cancelled or diverted flight, including the knock-on effects of one.
- `2` **baggage** — Lost, delayed, damaged, or charged-for baggage.
- `3` **website_app_issue** — The website, app, kiosk or check-in system is broken or behaving wrongly.
- `4` **inflight_experience** — Something about the onboard experience: seat, crew, wifi/entertainment, food, cleanliness.
- `5` **loyalty_refund_compensation** — SkyMiles/Medallion status, refunds, vouchers, or a request for compensation.
- `6` **praise** — Positive feedback with no issue to resolve.
- `7` **other** — Real message that fits none of the above, including pure venting with no actionable request. Use sparingly — if this exceeds ~10% the taxonomy is wrong.

Fill `decision` with `auto` or `escalate` (or just `a` / `e`).

Escalate when answering needs their booking or account details, when money or compensation is at stake, when they are stranded right now, or when the tone is angry enough that a canned reply makes it worse. Everything else is auto.

Use `note` whenever you hesitated. Those notes become the failure analysis.

## Tie-break rules

- Label by what the customer is ASKING FOR, not by what happened to them. 'Delayed, missed my connection, can you rebook me' -> rebooking_change. 'Delayed 7 hours, where is the plane you promised' -> delay_cancellation.
- If the message asks for money or miles back, it is loyalty_refund_compensation, even when a bag or a delay caused it.
- A message that mentions a bag ONLY as context for a delay is delay_cancellation; baggage means the bag itself is the problem.
- Praise plus a small complaint -> the complaint wins; praise is for messages with nothing to resolve.
- Sarcasm with no request ('great job as always') -> other, not praise.

When done, save as CSV (same filename) and run:

```
.venv/bin/python scripts/import_labelling_sheet.py
```