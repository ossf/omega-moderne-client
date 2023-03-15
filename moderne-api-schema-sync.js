const graphql_config = require('graphql-config');
const fs = require('fs');

// Used to keep the `moderne-api-schema.graphql` file in sync with the server
async function main() {
    const loaded_config = await graphql_config.loadConfig({});
    const project = loaded_config.getDefault();
    const schema = await project.getSchema('string');
    if (!schema) {
        throw new Error('No schema loaded!');
    }
    const schema_file_string =
        "# This file was generated based on \".graphqlconfig\". Do not edit manually.\n\n" +
        schema
            .replaceAll('  ', '    ')
    fs.writeFileSync(project.schema.toString(), schema_file_string);
}

(async () => {
    try {
        await main()
    } catch (err) {
        console.error('Something bad', err)
    }
})()
