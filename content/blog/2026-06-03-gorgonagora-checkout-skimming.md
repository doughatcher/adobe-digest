---
title: "GorgonAgora: Inside the 4,800-Storefront Checkout Skimming Machine"
date: 2026-06-03
draft: false
tags:
  - skimming
  - brand-impersonation
  - checkout-security
  - sansec
category: "Analysis"
summary: "Sansec research reveals 4,880+ fake .shop storefronts impersonating real brands with a custom checkout SDK and real-time 3DS relay. The attack doesn't touch your store — it builds a parallel one. Here's what makes it work and how to find clones of your catalog."
---

Security researcher Hunter Heaivilin has been mapping a skimming operation called GorgonAgora since August 2025. The dataset he handed to Sansec confirmed 4,880 fake storefronts — and urlscan.io's CSS fingerprint matching suggests the real number is already above 6,000.

The attack pattern differs from classic magecart. GorgonAgora doesn't touch your store. The operator scraped product catalogs from real Shopify storefronts belonging to hundreds of brands — Starbucks, Nike, Ford, Sony, Disney, Lego, DJI and more — and rebuilt each one as a lookalike on a .shop domain. Every store runs Medusa.js as its commerce backend. Every checkout loads the same SDK: `payment-vanilla.iife.js`.

## How PaymentVanilla works

When a shopper reaches checkout, the SDK injects a pixel-perfect fake Stripe iframe. The real Stripe is never involved. Card data flows to a WebSocket endpoint at an AlexHost server in Moldova, encrypted with AES-256-GCM. If the victim's bank returns a 3DS challenge, the operator relays it back through the fake iframe. The transaction completes. The shopper believes they bought from a real brand.

The 3DS relay is what makes this particularly effective — victims have no immediate signal that anything went wrong.

## Two generations, one fingerprint

The operator made one structural upgrade in late March 2026, switching from a single shared Medusa database (~339 stores, one publishable API key fronting 544 brand catalogs) to individual Medusa instances per storefront (~4,500+ stores). The shared-key enumeration hole is gone. Everything else is unchanged: same CSS bundle (`d482fd41f7f1f379.css`), same JS chunk, same skimmer SDK, same C2. The network is trivially fingerprintable despite the backend refactor.

## What to do

**For brand owners:** Search urlscan.io using `filename:d482fd41f7f1f379.css` to find storefronts cloning your catalog. The operator scrapes from real Shopify stores, so trademark and DMCA takedowns typically work fast once you identify a clone. Set up ongoing brand monitoring for your domain variants — the `.shop` TLD is the current pattern, but it's a template.

**For shoppers:** If you transacted on a `.shop` domain in the IOC list, treat the card as compromised and request a replacement.

Full technical write-up including C2 IPs, SDK hashes, and the complete sample domain list: [sansec.io/research/gorgonagora-fake-storefront-skimming-network](https://sansec.io/research/gorgonagora-fake-storefront-skimming-network)
