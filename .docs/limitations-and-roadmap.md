# Limitations and Roadmap

## Current limitations

### Extraction depends on page structure

Browser extraction currently relies on the rendered page DOM. That means extraction can fail or degrade when a provider changes its layout, class names, message containers, or script policies.

### Browser tools are page-injected

The current browser helper is injected into supported tabs. If a site blocks injected scripts or changes its loading flow, the tool may not appear or may stop working.

### Provider-specific behavior varies

Chat providers do not expose the same structure, so extraction quality can differ between ChatGPT, Claude, Gemini, and DeepSeek.

### Validation depends on network access

API key validation relies on provider availability and the local network. A valid key may still fail if the service is unavailable or rate-limited.

## Planned direction

### More authentic browsing support

The long-term direction is to support API-backed browser workflows where possible, so browser actions can be validated with real provider access instead of relying only on page scraping.

### Stronger extraction pipeline

The extraction pipeline can be improved with more resilient parsing, better message grouping, and safer fallbacks when the DOM changes.

### Better provider alignment

Browser roles and API roles should remain separate, but both should map cleanly into the dashboard so the operator can see which workflow each profile belongs to.

### More import/export options

Future documentation can cover bulk import/export for chats, browser tabs, and API profiles using versioned JSON formats.

## Design principle

The project should stay local-first by default, with clear opt-in support for API-backed workflows and explicit validation before saving sensitive configuration.
