# Contributing

This project use `tox` to run tests and linting.

To run all tests and linting, run:

```bash
tox
```

## Live Development

It's best practice to use pip's [development mode](https://setuptools.pypa.io/en/latest/userguide/development_mode.html)
during development.

```bash
pip install --editable .
```

## Suggested Development Environment

Either IntelliJ or PyCharm can be used to develop this project.

Suggested Plugins:
 - https://jimkyndemeyer.github.io/js-graphql-intellij-plugin/

## Updating the `moderne-api-schema.graphql` file

1. Add a `.env` file to the root of the project with the following content.
    ```text
    MODERNE_API_TOKEN=<your token>
    ```
2. Within IntelliJ or PyCharm, open the `.graphqlconfig` file.
3. Click the green arrow next to the `url` field.

