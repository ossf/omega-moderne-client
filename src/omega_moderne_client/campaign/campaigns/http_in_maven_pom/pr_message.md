[SECURITY] Use HTTPS to resolve dependencies in Maven Build

[![mitm_build](https://user-images.githubusercontent.com/1323708/59226671-90645200-8ba1-11e9-8ab3-39292bef99e9.jpeg)](https://infosecwriteups.com/want-to-take-over-the-java-ecosystem-all-you-need-is-a-mitm-1fc329d898fb)

---

This is a security fix for a high severity vulnerability in your [Apache Maven](https://maven.apache.org/) `pom.xml` file(s).

The build files indicate that this project is resolving dependencies over HTTP instead of HTTPS.
This leaves your build vulnerable to allowing a [Man in the Middle](https://en.wikipedia.org/wiki/Man-in-the-middle_attack) (MITM) attackers to execute arbitrary code on your or your computer or CI/CD system.

This vulnerability has a CVSS v3.0 Base Score of [8.1/10](https://nvd.nist.gov/vuln-metrics/cvss/v3-calculator?vector=AV:N/AC:H/PR:N/UI:N/S:U/C:H/I:H/A:H).

[POC code](https://max.computer/blog/how-to-take-over-the-computer-of-any-java-or-clojure-or-scala-developer/) has existed since 2014 to maliciously compromise a JAR file in-flight.
MITM attacks against HTTP are [increasingly common](https://security.stackexchange.com/a/12050), for example [Comcast is known to have done it to their own users](https://thenextweb.com/news/comcast-continues-to-inject-its-own-code-into-websites-you-visit).

## Resources

- [Want to take over the Java ecosystem? All you need is a MITM!](https://infosecwriteups.com/want-to-take-over-the-java-ecosystem-all-you-need-is-a-mitm-1fc329d898fb)
- [Update: Want to take over the Java ecosystem? All you need is a MITM!](https://medium.com/bugbountywriteup/update-want-to-take-over-the-java-ecosystem-all-you-need-is-a-mitm-d069d253fe23?source=friends_link&sk=8c8e52a7d57b98d0b7e541665688b454)
- [CVE-2021-26291](https://nvd.nist.gov/vuln/detail/CVE-2021-26291)
