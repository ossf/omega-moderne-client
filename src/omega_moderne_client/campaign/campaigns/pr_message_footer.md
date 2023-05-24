# :arrow_right: Vulnerability Disclosure :arrow_left:

:wave: Vulnerability disclosure is a super important part of the vulnerability handling process and should not be skipped! This may be completely new to you, and that's okay, I'm here to assist!

First question, do we need to perform vulnerability disclosure? It depends!

1. Is the vulnerable code only in tests or example code? No disclosure required!
2. Is the vulnerable code in code shipped to your end users? Vulnerability disclosure is probably required!

## Vulnerability Disclosure How-To

You have a few options to perform vulnerability disclosure. However, I'd like to suggest the following 2 options:

1. Request a CVE number from GitHub by creating a repository-level [GitHub Security Advisory](https://docs.github.com/en/code-security/repository-security-advisories/creating-a-repository-security-advisory).
   This has the advantage that, if you provide sufficient information, GitHub will automatically generate Dependabot alerts for your downstream consumers, resolving this vulnerability more quickly.
2. Reach out to the team at Snyk to assist with CVE issuance.
   They can be reached at the [Snyk's Disclosure Email](mailto:report@snyk.io).
   Note: Please include `OpenSSF: Omega Disclosure` in the subject of your email, so it is not missed.

## Why didn't you disclose privately (ie. coordinated disclosure)?

This pull request (PR) was automatically generated.

This is technically what is called "Full Disclosure" in vulnerability disclosure terminology, and I agree it's less than ideal. Currently, GitHub, GitLab, and BitBucket do not have support for private pull requests that can be opened by security researchers via an API, therefore, this is a stop gap process until the functionality is available.

As an open source security researcher, or even as a maintainer, there is limited time in the day. A single vulnerability could impact hundreds, or even thousands of open source projects. With tools like GitHub Code Search and CodeQL, this simplifies the identification and detection process, however, it is based on knowledge of vulnerabilities. This does not scale well.

There are several known challenges to open source security research, such as it's a long and tedious process that must be performed with time and care. Tracking individuals via email, JIRA, and bat signals also takes time, research, and isn't an automate-able process. As we study and design ways to automate at scale, individual reporting is also an issue, where security researchers do not wish to spam emails or issues, nor overwhelm already overly tax maintainers. This is not our goal.

Additionally, if we just spam out emails or issues, we’ll just overwhelm already over-taxed maintainers. We don't want to do this either.

By creating a pull request, we aim to provide maintainers a highly actionable way to fix the identified vulnerability, quickly, via a pull request.

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
