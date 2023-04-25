# :arrow_right: Vulnerability Disclosure :arrow_left:

:wave: Vulnerability disclosure is a super important part of the vulnerability handling process and should not be skipped! This may be completely new to you, and that's okay, I'm here to assist!

First question, do we need to perform vulnerability disclosure? It depends!

1. Is the vulnerable code only in tests or example code? No disclosure required!
2. Is the vulnerable code in code shipped to your end users? Vulnerability disclosure is probably required!

For partial path traversal, consider if user-supplied input could ever flow to this logic. If user-supplied input could reach this conditional, it's  insufficient and, as such, most likely a vulnerability.

## Vulnerability Disclosure How-To

You have a few options to perform vulnerability disclosure. However, I'd like to suggest the following 2 options:

1. Request a CVE number from GitHub by creating a repository-level [GitHub Security Advisory](https://docs.github.com/en/code-security/repository-security-advisories/creating-a-repository-security-advisory).
   This has the advantage that, if you provide sufficient information, GitHub will automatically generate Dependabot alerts for your downstream consumers, resolving this vulnerability more quickly.
2. Reach out to the team at Snyk to assist with CVE issuance.
   They can be reached at the [Snyk's Disclosure Email](mailto:report@snyk.io).
   Note: Please include `OpenSSF: Omega Disclosure` in the subject of your email, so it is not missed.

## Why didn't you disclose privately (ie. coordinated disclosure)?

This PR was automatically generated, in-bulk, and sent to this project as well as many others, all at the same time.

This is technically what is called a "Full Disclosure" in vulnerability disclosure, and I agree it's less than ideal.
If GitHub offered a way to create private pull requests to submit pull requests, I'd leverage it, but that infrastructure, sadly, doesn't exist yet.

The problem is that, as an open source software security researcher, I (exactly like open source maintainers), only have so much time in a day.
I'm able to find vulnerabilities impacting hundreds, or sometimes thousands of open source projects with tools like GitHub Code Search and CodeQL.
The problem is that my knowledge of vulnerabilities doesn't scale very well.

Individualized vulnerability disclosure takes time and care.
It's a long and tedious process, and I have a significant amount of experience with it (I have over 50 CVEs to my name).
Even tracking down the reporting channel (email, Jira, etc..) can take time and isn't automatable.
Unfortunately, when facing problems of this scale, individual reporting doesn't work well either.

Additionally, if I just spam out emails or issues, I'll just overwhelm already over-taxed maintainers, I don't want to do this either.

By creating a pull request, I am aiming to provide maintainers something highly actionable to actually fix the identified vulnerability; a pull request.

There's a larger discussion on this topic that can be found here: https://github.com/JLLeitschuh/security-research/discussions/12

## Opting Out

If you'd like to opt out of future automated security vulnerability fixes like this, please consider adding a file called
`.github/GH-ROBOTS.txt` to your repository with the line:

```
User-agent: OpenSSF Alpha Omega
Disallow: *
```

This bot will respect the [ROBOTS.txt](https://moz.com/learn/seo/robotstxt) format for future contributions.

Alternatively, if this project is no longer actively maintained, consider [archiving](https://help.github.com/en/github/creating-cloning-and-archiving-repositories/about-archiving-repositories) the repository.

## CLA Requirements

_This section is only relevant if your project requires contributors to sign a Contributor License Agreement (CLA) for external contributions._

All contributed commits are already automatically signed off.

> The meaning of a signoff depends on the project, but it typically certifies that committer has the rights to submit this work under the same license and agrees to a Developer Certificate of Origin
> (see [https://developercertificate.org/](https://developercertificate.org/) for more information).
>
> \- [Git Commit SignOff documentation](https://developercertificate.org/)

## Sponsorship & Support

This work was originally sponsored by HUMAN Security Inc. and the new Dan Kaminsky Fellowship, a fellowship created to celebrate Dan's memory and legacy by funding open-source work that makes the world a better (and more secure) place.

This pull request was created by the [Open Source Security Foundation (OpenSSF)](https://openssf.org/): Project [Alpha-Omega](https://openssf.org/community/alpha-omega/).
Alpha-Omega is a project partnering with open source software project maintainers to systematically find new, as-yet-undiscovered vulnerabilities in open source code – and get them fixed – to improve global software supply chain security.

This PR was generated with [Moderne](https://www.moderne.io/), a free-for-open source SaaS offering that uses format-preserving AST transformations to fix bugs, standardize code style, apply best practices, migrate library versions, and fix common security vulnerabilities at scale.
