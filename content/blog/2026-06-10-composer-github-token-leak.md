---
title: "Before the Next Wave: What Magento Shops Must Do After the Composer Token Leak"
date: 2026-06-10
draft: false
tags:
  - composer
  - github-actions
  - supply-chain
  - magento
  - mage-os
category: security
summary: "GitHub is rolling out its token format change again. If your CI still pins Composer or hasn't tightened workflow permissions, you're not ready for it."
---

On May 12, 2026, the PHP ecosystem had a near-miss that deserves more attention than it received. The [post-mortem from the graycoreio maintainer](https://github.com/graycoreio/github-actions-magento2/discussions/261) — who runs the canonical GitHub Actions suite for Magento and Mage-OS — is worth reading in full. Here is the operational summary for Commerce shops.

## What happened

GitHub began rolling out a new format for App installation tokens. The new format includes characters (`-`) that Composer's existing token validator rejected. When Composer threw the validation exception, it included the literal token value in the error message. Symfony Console rendered that message to stderr before the Actions runner could mask it — bypassing the secret masker's substring match.

For roughly 14 hours (2026-05-12 ~22:00 UTC to 2026-05-13 ~14:30 UTC), any workflow that ran `composer install` after `shivammathur/setup-php` on a `push`, `pull_request_target`, or `schedule` trigger had its `GITHUB_TOKEN` printed in plaintext to a world-readable Actions log.

The typical `GITHUB_TOKEN` on a push workflow carries `contents: write` by default. That is enough to push commits and tags to the repo it came from.

## Why Magento shops specifically should care

The graycoreio maintainer caught this while working on Magento 2.4.9 release support. His report named the repos where failures were visible during the window: `composer/composer` itself, `laravel/framework`, `sylius`, `woocommerce`, and others.

For Magento deployments, the supply chain path is direct: Magento and Mage-OS are Composer projects. Packagist polls GitHub for new tags and publishes them automatically. A successful exfil-and-push against any sufficiently popular Composer package resolves as remote code execution on every store that runs `composer install` before the rollback.

The maintainer has a working proof of concept: a stolen token can push to main in under a second with a polling setup. The window is narrow, but it is real.

## This is not over

Composer shipped patched releases (2.9.8 / 2.2.28 / 1.10.28) and GitHub paused the rollout. GitHub will resume the format change. The fix has to be in place before the next wave.

## What to do

**Bump Composer in CI.** If your workflows pin Composer — `tools: composer:v2.8.1` in setup-php, or a hardcoded version anywhere — unpin it or bump to 2.9.8 / 2.2.28 / 1.10.28. Unpatched Composer is the entire attack surface here.

**Add an explicit `permissions:` block.** Workflows without one inherit the legacy permissive default (`contents: write`). Add `permissions: contents: read` at the top of every workflow that does not need write access. Most CI jobs do not.

**Protect your tags.** The practical attack vector is pushing a tag to trigger a Packagist release. Enable GitHub tag protection rules on your repos. Branch protection alone does not cover tags — that distinction matters here.

**Sweep your logs for the window.** Look at failed runs between 2026-05-12 22:00 UTC and 2026-05-13 14:30 UTC. If you see a `ghs_…` string in any rendered output, your token was exposed. Then run:

```bash
git log --since='2026-05-12T22:00Z' --until='2026-05-13T14:30Z' --all
git tag --sort=creatordate
```

Check both for anything you do not recognize.

**Review failure-upload steps.** If you have `actions/upload-artifact` on `if: failure()` steps, those extend the live-token window while the upload runs — for large test fixtures this can be minutes, not seconds. Consider whether those steps need the token in scope, or whether the artifact upload can be moved outside the token's lifetime.

## The broader lesson

The person who caught this describes himself as a small fish. He caught it because he was actively working on Magento 2.4.9 support, noticed intermittent CI failures that did not match any change he had made, and dug in. His immediate actions — disabling actions org-wide, reaching out to Laravel and Mage-OS Discord, filing the Composer advisory — almost certainly kept this from being exploited.

The ecosystem's defense was accidental: Composer fails loudly, tokens are repo-scoped and short-lived, the rollout was gradual. None of that is engineered defense-in-depth. The checklist above is the engineered version. With the next rollout wave coming, there is no reason to wait.

---

*Sources: [graycoreio/github-actions-magento2 #261](https://github.com/graycoreio/github-actions-magento2/discussions/261) · [CVE-2026-45793 / GHSA-f9f8-rm49-7jv2](https://github.com/composer/composer/security/advisories/GHSA-f9f8-rm49-7jv2) · [Composer 2.9.8 release notes](https://blog.packagist.com/composer-2-9-8-and-2-2-28-fix-github-actions-token-disclosure-in-error-messages/)*
