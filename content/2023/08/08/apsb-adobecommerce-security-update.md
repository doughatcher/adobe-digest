---
layout: "post"
title: "APSB23-42 - Adobe-Commerce Security Update"
microblog: false
guid: "http://adobedigest.micro.blog/2023/08/08/apsb-adobecommerce-security-update.html"
date: "2023-08-08T00:00:00-05:00"
type: "post"
url: "/2023/08/08/apsb-adobecommerce-security-update.html"
---
## Bulletin Information

- **Bulletin ID:** APSB23-42
- **Published:** August 08, 2023
- **Priority:** 3
- **Severity:** Critical
- **CVE Count:** 3

## Affected Versions

- **Adobe Commerce:** 2.4.6-p1 and earlier2.4.5-p3 and earlier2.4.4-p4 and earlier2.4.3-ext-3 and earlier*2.4.2-ext-3 and earlier*2.4.1-ext-3 and earlier*2.4.0-ext-3 and earlier*2.3.7-p4-ext-3 and earlier*
- **Magento Open Source:** 2.4.6-p1 and earlier2.4.5-p3 and earlier2.4.4-p4 and earlier

## Vulnerability Details

**Total Vulnerabilities:** 3

**Severity Breakdown:**
- **Important:** 2
- **Critical:** 1

**Key Vulnerabilities:**

### 1. CVE-2023-38207
- **Category:** XML Injection (aka Blind XPath Injection) (CWE-91)
- **Impact:** Arbitrary file system read
- **Severity:** Important
- **CVSS Score:** 5.3
- **Authentication Required:** No

### 2. CVE-2023-38208
- **Category:** Improper Neutralization of Special Elements used in an OS Command ('OS Command Injection') (CWE-78)
- **Impact:** Arbitrary code execution
- **Severity:** Critical
- **CVSS Score:** 9.1
- **Authentication Required:** Yes

### 3. CVE-2023-38209
- **Category:** Improper Access Control (CWE-284)
- **Impact:** Privilege escalation
- **Severity:** Important
- **CVSS Score:** 6.5
- **Authentication Required:** Yes

## CVE Identifiers

CVE-2023-38207, CVE-2023-38208, CVE-2023-38209

---

[**Read Full Bulletin on Adobe Security Portal →**](https://helpx.adobe.com/security/products/magento/apsb23-42.html)
