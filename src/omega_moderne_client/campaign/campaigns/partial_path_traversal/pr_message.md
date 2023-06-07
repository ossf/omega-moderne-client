[SECURITY] Fix Partial Path Traversal Vulnerability

# Security Vulnerability Fix

This pull request fixes a partial-path traversal vulnerability due to an insufficient path traversal guard.

Even if you deem, as the maintainer of this project, this is not necessarily fixing a security vulnerability, it is still a valid security hardening.

## Preamble

### Impact

This issue allows a malicious actor to potentially break out of the expected directory. The impact is limited to sibling directories. For example, `userControlled.getCanonicalPath().startsWith("/user/out")` will allow an attacker to access a directory with a name like `/user/outnot`.

### Why?

To demonstrate this vulnerability, consider `"/user/outnot".startsWith("/user/out")`.
The check is bypassed although `/outnot` is not under the `/out` directory.
It's important to understand that the terminating slash may be removed when using various `String` representations of the `File` object.
For example, on Linux, `println(new File("/var"))` will print `/var`, but `println(new File("/var", "/")` will print `/var/`;
however, `println(new File("/var", "/").getCanonicalPath())` will print `/var`.

### The Fix

Comparing paths with the `java.nio.files.Path#startsWith` will adequately protect against this vulnerability.

For example: `file.getCanonicalFile().toPath().startsWith(BASE_DIRECTORY)` or `file.getCanonicalFile().toPath().startsWith(BASE_DIRECTORY_FILE.getCanonicalFile().toPath())`

### Other Examples

 - [CVE-2022-31159](https://github.com/aws/aws-sdk-java/security/advisories/GHSA-c28r-hw5m-5gv3) - aws/aws-sdk-java
 - [CVE-2022-23457](https://securitylab.github.com/advisories/GHSL-2022-008_The_OWASP_Enterprise_Security_API/) - ESAPI/esapi-java-legacy
