[SECURITY] Fix Temporary File Information Disclosure Vulnerability

# Security Vulnerability Fix

This pull request fixes a Temporary File Information Disclosure Vulnerability, which may exist in this project.

Even if you deem, as the maintainer of this project, this is not necessarily fixing a security vulnerability, it is still, most likely, a valid security hardening.

## Preamble

The system temporary directory is shared between all users on most unix-like systems (not MacOS, or Windows). Thus, code interacting with the system temporary directory must be careful about file interactions in this directory, and must ensure that the correct file posix permissions are set.

This PR was generated because a call to `File.createTempFile(..)` was detected in this repository in a way that makes this project vulnerable to local information disclosure.
With the default umask configuration, `File.createTempFile(..)` creates a file with the permissions `-rw-r--r--`. This means that any other user on the system can read the contents of this file.

### Impact

Information in this file is visible to other local users, allowing a malicious actor co-resident on the same machine to view potentially sensitive files.

#### Other Examples

 - [CVE-2020-15250](https://github.com/advisories/GHSA-269g-pwp5-87pp) - junit-team/junit
 - [CVE-2021-21364](https://github.com/advisories/GHSA-hpv8-9rq5-hq7w) - swagger-api/swagger-codegen
 - [CVE-2022-24823](https://github.com/advisories/GHSA-5mcr-gq6c-3hq2) - netty/netty
 - [CVE-2022-24823](https://github.com/advisories/GHSA-269q-hmxg-m83q) - netty/netty

# The Fix

The fix has been to convert the logic above to use the following API that was introduced in Java 1.7.

```java
File tmpDir = Files.createTempFile("temp dir").toFile();
```

The API both creates the file securely, ie. with a random, non-conflicting name, with file permissions that only allow the currently executing user to read or write the contents of this file.
By default, `Files.createTempFile("temp dir")` will create a file with the permissions `-rw-------`, which only allows the user that created the file to view/write the file contents.
