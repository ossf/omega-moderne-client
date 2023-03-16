# Omega Moderne Client

This is a client for the Moderne SaaS API (https://moderne.io).
It is how the [OpenSSF Alpha Omega](https://openssf.org/community/alpha-omega/) project generates
automated pull requests to fix vulnerabilities, at-scale, across the entire open source ecosystem.

## Usage

This client can either be used as a standalone script, or as a library.

### Secrets

The client requires a few secrets to be set in the environment:

#### Moderne API Token
Can either be read from:
 - `~/.moderne/token.txt` file
 - `MODERNE_API_TOKEN` environment variable

This is required for all moderne API calls.

#### GitHub API Token
Can either be read from:
 - `~/.config/hub` file
 - `GITHUB_TOKEN_FOR_MODERNE` environment variable

This is required only when attempting to create pull requests.

#### GPG Key
The following environment variables are required to sign generated commits:
 - `GPG_KEY_PUBLIC_KEY`
 - `GPG_KEY_PRIVATE_KEY`
 - `GPG_KEY_PASSPHRASE`

This is required only when attempting to create pull requests.

### CLI Usage

To install the CLI dependencies use the following command:

```bash
pip install .[cli]
```

For live development, you can use the following command to install the CLI in editable mode:
```bash
pip install -e .[cli]
```
To see more information about developing the CLI, see the [CONTRIBUTING](CONTRIBUTING.md) guide.

To use it as a script, you can run it like this:

```bash
omega-moderne-client --help
```

### Library Usage
TODO
