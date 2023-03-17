[SECURITY] Fix Zip Slip Vulnerability

# Security Vulnerability Fix

This pull request fixes a Zip Slip vulnerability either due to an insufficient, or missing guard when unzipping zip files.

Even if you deem, as the maintainer of this project, this is not necessarily fixing a security vulnerability, it is still, most likely, a valid security hardening.

## Preamble

### Impact

This issue allows a malicious zip file to potentially break out of the expected destination directory, writing contents into arbitrary locations on the file system.
Overwriting certain files/directories could allow an attacker to achieve remote code execution on a target system by exploiting this vulnerability.

### Why?

The best description of Zip-Slip can be found in the white paper published by Snyk: [Zip Slip Vulnerability](https://snyk.io/research/zip-slip-vulnerability)

#### But I had a guard in place, why wasn't it sufficient?

If the changes you see are a change to the guard, not the addition of a new guard, this is probably because this code contains a Zip-Slip vulnerability due to a partial path traversal vulnerability.

To demonstrate this vulnerability, consider `"/usr/outnot".startsWith("/usr/out")`.
The check is bypassed although `/outnot` is not under the `/out` directory.
It's important to understand that the terminating slash may be removed when using various `String` representations of the `File` object.
For example, on Linux, `println(new File("/var"))` will print `/var`, but `println(new File("/var", "/")` will print `/var/`;
however, `println(new File("/var", "/").getCanonicalPath())` will print `/var`.

### The Fix

Implementing a guard comparing paths with the method `java.nio.files.Path#startsWith` will adequately protect against this vulnerability.

For example: `file.getCanonicalFile().toPath().startsWith(BASE_DIRECTORY)` or `file.getCanonicalFile().toPath().startsWith(BASE_DIRECTORY_FILE.getCanonicalFile().toPath())`

### Other Examples

 - [CVE-2018-1002201](https://snyk.io/vuln/SNYK-JAVA-ORGZEROTURNAROUND-31681) - zeroturnaround/zt-zip
 - [CVE-2018-1002202](https://snyk.io/vuln/SNYK-JAVA-NETLINGALAZIP4J-31679) - srikanth-lingala/zip4j
 - [CVE-2018-8009](https://nvd.nist.gov/vuln/detail/CVE-2018-8009) - apache/hadoop
