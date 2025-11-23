mod instagram-scraper 'services/instagram-scraper'

# AsyncAPI: Bundle all asyncapi files from services directory
asyncapi-bundle:
    bun run asyncapi:bundle

# AsyncAPI: Generate code from bundled asyncapi spec
asyncapi-generate:
    bun run asyncapi:generate

# AsyncAPI: Bundle and generate in one command
asyncapi-build:
    bun run asyncapi:build