---
title: "Adobe Keeps Patching the Same Cracks: Inside July's Critical Commerce and AEM Bulletins"
date: 2026-07-15T10:00:00-05:00
draft: false
author: doug-hatcher
tags: [adobe-commerce, magento, aem, cve, cvss, apsb26-73, apsb26-74, incorrect-authorization, stored-xss, file-upload, xxe, patch-management, security-posture, incident-response, adobe-commerce-cloud-service, saas]
category: "Pattern Analysis"
summary: "July 14 wasn't one bulletin — it was a week. APSB26-73 shipped seven Adobe Commerce CVEs (two critical RCEs); the parallel AEM bulletin APSB26-74 added two more criticals, one of them an XXE — the exact class as CosmicSting; and Amasty patched 25 extensions the week before. A month ago we argued the 2026 Commerce pattern was structural, not bad luck. The full July picture doesn't just confirm it — it shows the same cracks running clean across Adobe's whole DX stack, and back four years."
related:
  - title: "Two Patch Cycles, Same Cracks: What Commerce's 2026 CVE Pattern Is Telling You"
    url: https://experiencedigest.org/blog/2026-06-23-two-patch-cycles-same-cracks/
    date: "June 23, 2026"
  - title: "Security update available for Adobe Commerce — APSB26-73"
    url: https://helpx.adobe.com/security/products/magento/apsb26-73.html
    date: "July 14, 2026"
  - title: "Security update available for Adobe Experience Manager — APSB26-74"
    url: https://helpx.adobe.com/security/products/experience-manager/apsb26-74.html
    date: "July 14, 2026"
  - title: "Amasty patches 25 Magento extensions, 1 critical (Sansec)"
    url: https://sansec.io/research/amasty-mass-disclosure
    date: "July 2, 2026"
---

On July 14, 2026, Adobe published two security bulletins on the same day: one for **Adobe Commerce** — the enterprise platform behind Magento storefronts — and one for **Adobe Experience Manager (AEM)**, its content-management sibling. Between them they fix four *critical* vulnerabilities, most of which let an attacker run their own code on your server. If you run either platform, the short version is: **patch now.**

For Commerce, that means applying the July 2026 security patch for your release line — the `…-2026-jul` builds, from `2.4.9-2026-jul` down to `2.4.4-p18-2026-jul`. One catch worth knowing up front: these ship as *isolated* security patches, so you have to already be on the latest `-p` release for your line (2.4.8-p5, 2.4.7-p10, and so on) before they'll apply.

If that's all you came for, you're done. But this week is worth a closer look than a checklist, because here's the uncomfortable part: it's the same small handful of flaws Adobe has been patching, under fresh CVE numbers, for four years running. This isn't a new problem getting fixed. It's an old one showing up again — and once you can see the pattern, the bulletins read very differently.

Start with the Commerce bulletin, [APSB26-73](https://helpx.adobe.com/security/products/magento/apsb26-73.html), rated Priority 2. On the surface it's a routine out-of-band update. Look at the composition and it stops looking routine: **every finding in the core batch is rated Critical. Zero "Important," zero "Moderate."** That distribution is unusual. Most Commerce bulletins are a long tail of Importants with one or two Criticals riding along. This one is all headline.

## What's in it

Seven Commerce CVEs, across three familiar classes:

| CVE | Class | CVSS |
|-----|-------|------|
| CVE-2026-48358 | Improper output encoding → RCE | **10.0 (NIST) / 9.1 (Adobe)** |
| CVE-2026-48356 | Unrestricted file upload → RCE | **9.6** |
| CVE-2026-47984 | Incorrect authorization → read **and** write, no user interaction | 8.2 |
| CVE-2026-47995 | Stored XSS | 8.1 |
| CVE-2026-47996 | Incorrect authorization → unauthorized read | 7.6 |
| CVE-2026-47992 | SQL injection | 7.2 |
| CVE-2026-47999 | Stored XSS | 4.8 |

Two of those deserve a second look before we move on. CVE-2026-48358, the output-encoding RCE, carries the split score we'll unpack shortly. And CVE-2026-47984 is quietly one of the worst in the batch despite its 8.2: it's an authorization bypass that yields **both read and write with no user interaction** — the cleanest on-ramp in the whole bulletin.

Affected versions run up through 2.4.9 and back across the patch lines to 2.4.4-p18, plus the matching Adobe Commerce B2B builds. Nobody on a supported line is out of scope.

## Where those numbers come from

A ninety-second primer, because the rest of this piece leans on it — and because the two numbers next to CVE-2026-48358 up in that table are only confusing until you know how they're made.

A **CVE** — Common Vulnerabilities and Exposures — is not a severity, a patch, or a bug report. It's a catalog number. The CVE Program, run by MITRE and funded by CISA, exists so that when Sansec, Adobe, and your WAF vendor are all talking about the same flaw, they use the same name instead of three marketing nicknames. `CVE-2026-48358` means "the 48,358th vulnerability catalogued in 2026," nothing more.

The IDs are handed out by **CNAs** — CVE Numbering Authorities, organizations MITRE authorizes to assign numbers inside their own products. **Adobe is its own CNA.** So the lifecycle of one of these entries looks like this:

1. Someone finds it — an internal team, a bug-bounty researcher, or a shop like Sansec watching real-world attacks.
2. It's reported to Adobe under coordinated disclosure — quietly, before the public knows.
3. Adobe, as CNA, reserves a CVE ID and builds the fix.
4. On a bulletin cadence (the APSB numbers), Adobe publishes the advisory with the CVE, the affected versions, and **its own CVSS score.**
5. Days later, **NIST's National Vulnerability Database (NVD)** ingests the CVE and re-scores it *independently*, adding machine-readable version data.

That last step is why the table shows two numbers. **CVSS** — the Common Vulnerability Scoring System — runs 0 to 10 and is built from base metrics: how the bug is reached (network vs. local), how hard it is to pull off, whether the attacker needs privileges or a victim's click, and how much confidentiality/integrity/availability is lost. Critical is 9.0–10.0, High is 7.0–8.9, and down from there. But CVSS is a *judgment applied to a fixed rubric* — and the CNA and NVD apply it separately. When they read the "privileges required" metric differently, you get exactly the split we're about to walk through. Neither number is wrong. They're answering slightly different questions, and knowing that is the difference between reading a bulletin and being managed by one.

One more piece the score doesn't carry: **CVSS tells you how bad a bug is in the abstract, not how urgent it is for you.** Two other signals do that job, and we'll use them later — Adobe's own **Priority rating** (1/2/3, its read on exploitation likelihood; APSB26-73 is Priority 2) and CISA's **Known Exploited Vulnerabilities** catalog, the definitive "this is being used in real attacks right now" list.

## We said this was structural. Here's the third data point.

A month ago, in [Two Patch Cycles, Same Cracks](https://experiencedigest.org/blog/2026-06-23-two-patch-cycles-same-cracks/), we laid two 2026 bulletins side by side — APSB26-05 in March and APSB26-49 in May — and pointed at the same two classes showing up in both: **incorrect authorization and stored XSS, bulletin after bulletin.** Different entry points, different CVSS, same categories. The line was: *that's structural, not bad luck.*

APSB26-73 is the third cycle, and it doesn't break the pattern — it thickens it. Both authorization classes are back. Stored XSS is back. The batch adds a dangerous-file-upload path and an output-encoding RCE, both of which are the same failure mode wearing different clothes: **the platform trusting input it shouldn't at a boundary it controls.** Three bulletins, one diagnosis.

But calling it a "2026 pattern" undersells it. The honest framing is longer.

## The history this bulletin is standing on

These aren't new cracks. They're the same load-bearing walls Commerce has been patching for years, and each generation of them has a body count.

- **CVE-2022-24086** — the mail-template injection RCE. Unauthenticated, wormable, and mass-exploited: the Ondatry group alone hit 4,000+ stores. This is the one that taught the ecosystem that a Magento RCE isn't an abstraction — it's payment-skimmer infrastructure within days of disclosure.
- **CVE-2024-34102, "CosmicSting"** — an XXE that leaked the encryption key, which attackers turned into forged admin API access and, from there, CMS-block skimmers. Sansec counted **4,275 confirmed store compromises** across seven groups. CVSS 9.8. The lesson: in Commerce, the *primitive* (XXE, a key leak) is rarely the whole attack — it's the first hop in a chain that ends at checkout data.
- **CVE-2025-54236, "SessionReaper"** — unauthenticated RCE through session handling, disclosed September 2025, actively exploited within weeks. Adobe rated it 9.1. NIST scored the class higher. Sound familiar?

Line those up — template injection (2022), XXE and key theft (2024), session deserialization (2025), and now output encoding and file upload (2026) — and the entry points keep changing while the *category* never does: **Commerce fails at the input-trust boundary, and the payoff is always the same, because the payoff is always payment data.** GorgonAgora, the 4,800-storefront skimming operation [we covered in June](https://experiencedigest.org/blog/2026-06-03-gorgonagora-checkout-skimming/), is what these CVEs become downstream. The bulletin is the upstream. APSB26-73 is not a new problem. It's the 2026 rev of a four-year-old one.

## The scoring gap is part of the history too

Look at CVE-2026-48358 again: **NIST scores it 10.0, Adobe scores it 9.1.** The entire two-point spread hinges on one metric — Adobe assumes `PR:H` (you need an authenticated admin session to exploit it); NIST assumes `PR:N` (you don't). Same vulnerability, two threat models.

This is not a one-off. SessionReaper had the same NIST-vs-Adobe tension. So did findings in the last two bulletins. Adobe's `PR:H` assumption rests on admin being hard to reach — but **this very bulletin ships an auth-bypass and a stored XSS alongside the RCE.** The prerequisites for the "high-privilege" bug are satisfied by the low-privilege bugs in the same batch. When you score the RCE in isolation, you get 9.1. When you score it as an operator holding the whole patch note, you assume the chain exists and you plan for 10.0.

That's the real reason to stop reading these bulletins as CVSS leaderboards. **A Commerce bulletin isn't a list of independent bugs — it's an attack graph, and Adobe hands you the whole graph at once.** Auth bypass to reach admin context; stored XSS or the file upload to get code in; the encoding bug to execute it. The batch is more dangerous than any single row because the rows compose.

## This wasn't one bulletin — it was a week

Here's the part that turns a Commerce story into an ecosystem story: **APSB26-73 didn't ship alone.** The same day, Adobe published [APSB26-74](https://helpx.adobe.com/security/products/experience-manager/apsb26-74.html) for Experience Manager — 13 more CVEs, and two of them critical (CVSS 9.6):

- **CVE-2026-48259** — a server-side request forgery that chains to arbitrary code execution.
- **CVE-2026-48359** — an **XML External Entity (XXE)** flaw, also leading to code execution.

Stop on that second one. An XXE, in an Adobe product, leading to code execution, is not a new movie — it's *CosmicSting*, the 2024 catastrophe from the history section above, playing in the theater next door. Different product (AEM, not Commerce), different CVE, same class that compromised 4,275 stores two years ago. When the exact vulnerability family that caused the last mass-compromise event resurfaces as a fresh critical in the sibling product, "isolated incident" stops being a defensible reading. (Credit where due: Assetnote's researchers found the AEM criticals — external eyes on the same input-trust boundaries Adobe keeps patching internally.)

And it wasn't only Adobe. Twelve days earlier, on July 2, [Sansec reported](https://sansec.io/research/amasty-mass-disclosure) that **Amasty shipped an emergency release for 25 of its Magento extensions.** The critical one lives in **Advanced Product Reviews** (`amasty/advanced-review`, fixed in 1.17.1; its GraphQL companion `amasty/advanced-review-graphql` in 1.0.6): an *unauthenticated* attacker can upload a web shell and take full control of the store. No login. That makes it operationally *worse* than APSB26-73's own file-upload RCE, which at least needs a victim to click something. And it isn't Amasty's first this summer — [CVE-2026-53787](https://sansec.io/research/amasty-order-attributes-file-upload), an unauthenticated file-upload RCE in Amasty Order Attributes rated CVSS 9.3, landed back in June. Same vendor, same class, twice in two months.

Amasty modules run on thousands of stores. That's the third leg of the same window: first-party Commerce (APSB26-73), first-party AEM (APSB26-74), and the third-party extension layer (Amasty) — all disclosing the same families of input-handling and code-execution bugs inside two weeks.

This is the completeness that matters for posture. If your mental model of "am I exposed?" is a single Adobe Commerce bulletin, you're watching one of three doors. The extension layer is the one most shops never scan against Adobe's calendar at all — and it's the door Sansec's telemetry says attackers walk through most often, because a vulnerable module inherits the full trust of the store it's installed in.

## What a 9 or a 10 actually demands

A CVSS score is not a priority. It's an *input* to a priority. The mistake that gets stores skimmed is treating "9.8 Critical" as a feeling instead of a trigger for a specific, pre-decided response. Proper posture means the number lands in a runbook, not a Slack channel where it gets a 👍 and a "we'll get it next sprint."

Here's the discipline, roughly tiered:

**Critical (9.0–10.0), especially network-reachable, low-complexity, or unauthenticated.** This is an *emergency change*, not a maintenance-window item. The clock is hours-to-days. The moment a Critical Commerce RCE has a public proof-of-concept or lands on CISA's KEV list, that clock drops to hours — attackers weaponize known Magento bugs in days, sometimes the same day, because the payoff is a payment skimmer. If you cannot deploy the patch inside that window, you deploy a *compensating control* inside it instead (below). "We're scheduled for the next release" is not a response to a 10.

**High (7.0–8.9).** Expedited, but not fire-alarm — days to about two weeks, on a tracked ticket with an owner and a deadline, not the open-ended backlog. Most of APSB26-73's non-RCE findings live here, and they matter precisely because they're the on-ramps that make the Criticals reachable.

**Medium / Low.** Fold into the next scheduled patch cycle. Don't ignore them — an auth-bypass rated 6.5 is still a rung on someone's ladder — but they don't preempt planned work.

Now the part people skip: **what you do in the gap between "a Critical dropped" and "the patch is validated and live."** For a platform where a bad deploy can take checkout offline, you rarely get to patch blind in an hour. So you buy time with blocking precautions:

- **Virtual-patch at the edge.** A WAF rule (Fastly on Commerce Cloud, Cloudflare, Akamai, or on-prem) that blocks the exploit signature buys you days to test the real patch properly. Sansec and the WAF vendors typically publish rules for high-profile Magento CVEs within a day of disclosure.
- **Segment the admin panel.** IP-allowlist or VPN-gate `/admin`. This is the single highest-leverage control for Commerce, because so many "high privilege required" bugs — including CVE-2026-48358's Adobe scoring — assume admin is reachable. Make it unreachable and you've downgraded the CVE on your own infrastructure.
- **Disable or lock down the affected surface.** If the vulnerable feature is optional, turn it off. If it's a file-upload path, rate-limit it and tighten its type/permission checks at the proxy.
- **The blunt lever: take the surface offline.** Reserved for the genuine worst case — an unauthenticated, actively-exploited Critical with no patch and no workable virtual patch. It's rare, and it's exactly what "a 10 with a public exploit and no fix" is *for*. Knowing in advance that you're willing to pull it is what keeps the decision from taking six hours of meetings while you're being drained.

Calibrate to *both* the score and the exploitation status. APSB26-73 is all-Critical but Priority 2 — Adobe's read is elevated risk, no known exploits yet. That combination says **patch on an expedited cycle and segment your admin as belt-and-suspenders — not pull checkout offline tonight.** If it moves to CISA KEV next week, that calculus changes in an afternoon, and a shop with a posture already has the WAF rule and the admin allowlist in place to absorb the wait. A shop without one spends that afternoon deciding whether to take the store down.

## The practical calls

1. **Patch this cycle, and patch the whole line.** Apply the `…-2026-jul` security patch for your release — and note it only lands if you're already on the latest `-p` (2.4.8-p5, 2.4.7-p10, etc.), so budget for that step first. The two RCEs (48358, 48356) are the priority, but you don't get to cherry-pick — the auth and XSS bugs are what make the RCEs reachable.
2. **Score the batch, not the bug.** Treat CVE-2026-48358 as a 10.0 in your risk register regardless of Adobe's `PR:H`. The auth-bypass shipped in the same bulletin is your attacker's on-ramp to the privilege Adobe assumes they don't have.
3. **If you're on an older line, watch the back-port window.** Shops pinned to 2.4.6/2.4.7 for extension-compatibility reasons are exposed for exactly as long as it takes to validate the patch against their module stack. That validation lag *is* the exposure window — budget for it, don't discover it.
4. **Patch AEM in the same change window, not a separate one.** If you run Experience Manager alongside Commerce, APSB26-74's two 9.6 criticals — the SSRF and the XXE — belong on the same emergency ticket. Treating "the Commerce bulletin" and "the AEM bulletin" as separate workstreams is how the second one slips a cycle.
5. **Scan your extensions against this week too.** Adobe's calendar doesn't cover Amasty, or any of your other third-party modules. Confirm `amasty/advanced-review` is ≥ 1.17.1 (and `amasty/advanced-review-graphql` ≥ 1.0.6), check the June Order Attributes fix (CVE-2026-53787) while you're in there, and make "audit installed extensions for known CVEs" a standing item — not something you do only when a first-party bulletin reminds you. The extension unauth-RCE is a lower-friction attack than anything in APSB26-73.
6. **Assume skimming is the endgame.** Every prior generation of this pattern ended at checkout. Post-patch, audit CMS blocks, admin users, and integration tokens for anything that predates your update — the fix closes the door, it doesn't evict whoever's already inside.

The reason this week earns editorial attention isn't the severity, though two all-critical bulletins on the same day is worth a raised eyebrow. It's that it's the cleanest data point yet on a line that runs back to 2022 — and this time the same cracks show up across Commerce, AEM, and the extension layer all at once. The bulletins keep telling you the same thing. The only question is whether your patch process is built to hear it.

## Or stop running the treadmill

Everything above assumes you're the one holding the patch pipeline — the runbook, the WAF rules, the emergency-change muscle, the standing extension audit. You can get very good at all of it. But being the one who runs it is itself a choice, and it's worth saying plainly that Adobe now sells the other one.

**Adobe Commerce as a Cloud Service** — the SaaS product, not the older PaaS "Commerce on Cloud" — moves the treadmill onto Adobe's side of the line. Security updates like APSB26-73 are applied continuously by Adobe. There's no "get current to the latest `-p`, then apply the isolated July patch, then regression-test against your module stack" sequence, because there's no self-managed core sitting in your `vendor/` for you to patch. The edge, the WAF, the infrastructure hardening — managed, on the other side of the boundary.

And here's the part that speaks straight to the third leg of this week's story. On the Cloud Service, extensions run **out-of-process** through App Builder — not as in-process PHP dropped into `vendor/`. The Amasty-shaped risk — a third-party module inheriting the full trust of your storefront and turning an unauthenticated file upload into a web shell — largely stops being your problem, because the extension no longer executes inside your store's trust boundary. The architecture removes the *class*, not just this month's instance of it. That's a different kind of fix than a patch: a patch closes a door, and this moves the door out of the building.

It isn't free of trade-offs. SaaS means less low-level control, more opinionated constraints, and a migration that's real work — especially if you've built deep in-process customizations. That's a legitimate cost to weigh, and for some shops it's the deciding one. But if you read this whole piece nodding along at the runbook and the emergency-change window and the standing extension audit — and quietly ran the math on what that operational load costs you every single bulletin cycle — the honest question isn't whether the Cloud Service is worth it. It's whether the treadmill is.
