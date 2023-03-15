# Contributing

This project use `tox` to run tests and linting.

Currently, IntelliJ and PyCharm only support `tox` version 3.x.
This will be fixed in the next release of IntelliJ and PyCharm, until then, you will need to install `tox` version 3.x manually.
See: https://youtrack.jetbrains.com/issue/PY-57956

To run all tests and linting, run:

```bash
tox
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

