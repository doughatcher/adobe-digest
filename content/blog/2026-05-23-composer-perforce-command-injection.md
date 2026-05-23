---
title: "The Perforce Driver You Never Knew You Had: Composer CVE-2026-40261 and CVE-2026-40176"
date: 2026-05-23T10:00:00-05:00
draft: false
tags: [composer, php, supply-chain, cve, magento, adobe-commerce, dependency-management]
category: "Attack Analysis"
summary: "Two command injection vulnerabilities in Composer's Perforce driver are exploitable even if you've never touched Perforce. For Magento shops running dev dependencies from source, CVE-2026-40261 is a supply-chain exposure hiding behind a feature most teams don't know is active."
---

Update Composer to 2.9.6 or 2.2.27 LTS now. If that sentence is enough, you're done. If you want to understand why this one is worth a closer look, keep reading.

## The Perforce Driver Is Loaded Whether You Use It or Not

[CVE-2026-40261](https://github.com/composer/composer/security/advisories/GHSA-gqw4-4w2p-838q) and [CVE-2026-40176](https://github.com/composer/composer/security/advisories/GHSA-wg36-wvj6-r67p) are both in Composer's Perforce VCS driver - the code that handles repositories declared as perforce type in a composer.json. Neither requires Perforce to be installed. Both allow arbitrary command execution in the context of whatever runs composer install or composer update.

That's the part the advisory buries in the third paragraph. Most Magento shops have never configured a Perforce repository and have no intention of doing so. That doesn't matter. The vulnerable code path loads regardless, and an attacker-controlled composer.json or package metadata can reach it.

## Two Different Attack Surfaces

CVE-2026-40176 requires the attacker to control the composer.json you're actually running - the root manifest. The injected values are Perforce connection parameters (port, user, client) that get interpolated into shell commands without escaping. This is the local-project risk: if you're running Composer commands on a project from an untrusted source, this fires.

CVE-2026-40261 is the wider problem. It affects the syncCodeBase() method, which handles a source reference parameter that can come from *package metadata* - not just the root composer.json. That means any Composer repository, including a compromised or malicious third-party repository, can serve package metadata that exploits this. You don't have to touch the root manifest. You just have to install or update a dependency from source.

The trigger condition: installing dev-prefixed versions (anything before 1.0.0, or packages with dev- prefix) defaults to --prefer-source in Composer. Commerce agencies running Magento module development pipelines almost certainly have some dev-constraint packages in their dependency tree.

## What This Means for a Magento and Commerce Pipeline

Enterprise commerce platforms run layered dependency graphs. The core is typically Magento/Adobe Commerce, which comes from the Magento Composer repository. Third-party modules come from a mix of Packagist, private repositories, and occasionally vendor-managed repos. Development workflows - module builds, staging deploys, CI pipelines - regularly operate with dev- constraints to pull HEAD on in-development extensions.

In that environment, CVE-2026-40261 is not hypothetical. Any point in the supply chain where package metadata can be influenced - a compromised private repo, a package repository serving malicious metadata, a CI secret that got rotated too late - becomes a command injection entry point into your build environment. The build environment has access to credentials, cloud provider tokens, and staging infrastructure that production doesn't expose directly.

The patch notes say there's no evidence of exploitation prior to publication. That's the standard disclosure language and it's worth taking at face value. It also doesn't change the update calculus.

## Packagist and Private Packagist Already Moved

Packagist.org disabled Perforce source metadata on April 10, 2026 as a precaution. Private Packagist did the same. If your dependencies come exclusively from these sources and you're not running --prefer-source against anything that reaches Perforce metadata, your exposure was already mitigated at the registry layer.

If you run Private Packagist Self-Hosted, the new release is dropping now - and you should scan your installation using the verification command the release announcement documents before relying on the registry-level mitigation.

## The Practical Calls

1. Run composer.phar self-update on every machine and CI runner that executes Composer commands. This includes local dev environments - dev machines are a vector, not just pipelines.
2. If you can't update immediately, --prefer-dist in your installs eliminates the CVE-2026-40261 exposure by avoiding the source-fetch path. It's a workaround, not a fix.
3. For CVE-2026-40176: review any composer.json files you run Composer commands against and aren't fully trust-anchored. If your dev workflow clones external projects and runs composer install on them without inspection, that's a habit worth fixing regardless of this CVE.
4. Audit your private Composer repositories for Perforce-type source declarations. These should not exist in commerce dependency graphs. If they do, understand why.

This is a straightforward dependency update with a clear fix. The reason it's worth editorial attention is the "doesn't affect Perforce users" misread - the relevant audience here is every team running a PHP/Composer-based build pipeline, which in the commerce world is essentially everyone.
