# Canary Tokens

This is a proof-of-concept tool to generate and destroy canary tokens.

It requires two environment variables:
* `CANARY_DOMAIN`, the subdomain for `canary.tools`;
* `CANARY_API_TOKEN` for authenticating to the API, see https://docs.canary.tools/guide/getting-started.html#api-details for instructions.

See the wiki for more details.

This code uses the `canarytools` package to make API calls, but in some cases that's not possible. Specifically, it is not possible to create `FASTREDIRECT`, `SLOWREDIRECT` and `SQL` tokens via the console.
This code also implements a `CanaryAPI` class to polyfill the missing interactions and transparently chooses the appropriate class to use.

If this code is run directly, it will create and destroy every token kind in succession, in the order presented in `CanaryTokenKinds`, excluding the S3 token kind.
