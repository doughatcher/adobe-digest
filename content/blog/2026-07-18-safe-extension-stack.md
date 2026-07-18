---
title: "You Can't Shop Your Way to a Safe Extension Stack"
date: 2026-07-18T08:00:00-05:00
draft: false
author: doug-hatcher
tags: [adobe-commerce, magento, extensions, third-party, supply-chain, vendor-risk, sansec, magevulndb, vulnerability-scanning, ci-cd, patch-management, security-posture]
category: "Supply Chain"
summary: "Sansec's public vulnerability database for Magento extensions is topped by the biggest, most established vendors — not because they're careless, but because scale and honest disclosure are what put a module on the list. It cuts both ways, and the lesson isn't which vendors to avoid. You can't vendor-select your way to safety: judge each module on its merits, scan what you actually run, and — the cheapest control of all — question whether you needed half of it in the first place."
related:
  - title: "Adobe Keeps Patching the Same Cracks: Inside July's Critical Commerce and AEM Bulletins"
    url: https://experiencedigest.org/blog/2026-07-15-apsb26-73-pattern-held/
    date: "July 15, 2026"
  - title: "Bad extensions now main source of Magento hacks & a solution (Sansec)"
    url: https://sansec.io/research/magento-module-blacklist
    date: "Sansec Research"
  - title: "Magento Vulnerability Database (magevulndb)"
    url: https://github.com/sansecio/magevulndb
    date: "GitHub"
---

Sansec keeps a public database of Magento and Adobe Commerce extensions with known security issues — [magevulndb](https://github.com/sansecio/magevulndb), 205 entries and counting. If you read the list looking for the vendors to avoid, you'll draw the wrong lesson. The names near the top are some of the largest, most established, most widely installed extension makers in the ecosystem. That isn't a coincidence, and it isn't an indictment. It's most of the point.

Being on this list is mostly a function of three things: how many modules you ship, how many stores run them, and whether you disclose and patch when something turns up. Big vendors score high on all three. Larger catalogs mean more surface area, more installs mean more researchers and attackers looking, and the reputable vendors actually publish advisories and cut fixes — which is what you want from a supplier, and also what lands a CVE in a public database with the vendor's name on it.

It cuts both ways, and it's worth being honest about. A vendor like Amasty earns its footprint: the modules are cheap, they're capable, and they'll often do something out of the box a competitor can't. Run six or seven of them together and you can stand up a genuinely nice setup for very little money. But six or seven well-scrutinized modules are also six or seven pieces of catalogued, actively-probed surface, concentrated under one vendor whose flaws tend to get found and published. The convenience and the exposure are the same decision seen from two sides.

That doesn't make the competition safer. The obscure alternative that never lands on any list is just as likely to ship code that's as bad or worse — you just won't hear about it, because nobody's looking. Security through obscurity was never security. So the move isn't to trade a scrutinized vendor for an unscrutinized one. It's to stop treating "who made it" as the safety question and judge each module on its own merits: do you run it, is it current, does it need to be there at all.

This is why you can't vendor-select your way to safety. "We only use big, reputable extensions" is a comforting policy and a weak control, because the big reputable extensions are the ones with the most catalogued vulnerabilities — not because they're worse, but because they're bigger and more open about what they find. The exposure that gets a store skimmed is rarely "we picked a bad vendor." It's "we're three releases behind on a good one, and nobody was watching."

## The layer Adobe's bulletins don't cover

This is the surface last week's Adobe advisories say nothing about. APSB26-73 patched the Commerce core. APSB26-74 patched Experience Manager. Neither touches the third-party PHP running inside your store with the store's full privileges, and that is the surface Sansec's incident telemetry keeps naming as the one attackers actually use. Since 2018, when Magecart crews shifted off core exploits and onto extension zero-days, a vulnerable module has been a more reliable way into a store than the platform itself.

The [Amasty Advanced Product Reviews RCE we covered last week](https://experiencedigest.org/blog/2026-07-15-apsb26-73-pattern-held/) is the pattern working the way it should: a large vendor finds a serious flaw, discloses it, and ships fixes across its catalog. That's why it's documented at all. The finding that should worry you is the one from the vendor who never posts an advisory — the module quietly rotting in your `vendor/` directory that no database will ever flag for you.

Until now this digest could tell you to "scan your extensions" without pointing at what to scan against. magevulndb is what to scan against.

## The scanner is the point

The database isn't only meant to be read. It ships as a plugin for n98-magerun, the standard Magento command-line tool, and the plugin compares every registered module on an install against the list. Set it up once:

```
# one-time, for Magento 2
mkdir -p ~/.n98-magerun2/modules
cd ~/.n98-magerun2/modules
git clone https://github.com/gwillem/magevulndb.git
```

Then run it from any store root:

```
n98-magerun2.phar dev:module:security -q
```

It reloads the latest data on every run, so there's nothing to keep current yourself. It also returns a usable exit code: `0` when the store is clean, `1` when it finds a known-vulnerable module, and `2` when it couldn't load the data. That `1` is the one that matters, because it means the scan belongs in CI. A single required step in your pipeline turns "we should audit our extensions sometime" into a gate that blocks a deploy carrying a known-vulnerable module, with no human in the loop.

If your shop is composer-managed and you'd rather not add a runtime tool, [Roave's SecurityAdvisories](https://github.com/Roave/SecurityAdvisories) does a comparable job at install time by refusing to resolve package versions with known advisories. It's the tighter fit for teams already living in composer. magevulndb's advantage is that it also covers Magento 1 and installs that composer never managed at all.

## What a clean scan does and doesn't mean

A clean scan means no *known* issue, not no issue. The list is community-maintained, it registers only the newest advisory per module, and it matches on the module's registered code name. This is a floor, not a ceiling.

What that floor catches is the failure mode that dominates Sansec's data: a store running a module version with a public, catalogued, already-patched vulnerability that nobody got around to updating. It's unglamorous, it requires no zero-day, and it is one of the most common ways a Magento store ends up with a skimmer. Closing it isn't sophisticated work. It's mostly a matter of ever having checked.

We've folded the mechanics into the [CVE Response Runbook](https://experiencedigest.org/runbook/) as a standing control, next to the patch-cadence discipline the rest of that document covers. The database has been public for years and updates itself on every scan. Wiring it into one pipeline is close to free, and it belongs in every Magento build.

## The extension you don't install

Everything to here is about managing surface. There's a cheaper move than managing it: not acquiring it in the first place.

Walk a Magento marketplace with a purchasing mindset and it turns into the old supermarket-sweep game show — cart barreling down the aisle, grab everything that looks useful before the buzzer. Improved sorting. A fancier mega-menu. Six ways to badge a product. Each one is a real feature, and each one is also third-party code running inside your store with the store's full privileges: another dependency to patch, another version to track, another row that might one day land on a list like this one.

The question that actually shrinks your risk isn't "which sorting extension is safest." It's "why do we need improved sorting at all." You are trying to sell products online. A surprising share of any marketplace is answering problems a well-built storefront doesn't have. Every module you don't install is one you never have to scan, patch, monitor, or explain to an incident responder at two in the morning. Restraint is a security control, and it's the only one that costs nothing to run.

Scan what you keep. But keep less.
