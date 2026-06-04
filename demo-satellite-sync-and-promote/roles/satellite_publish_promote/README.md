# satellite_publish_promote role

**Publishes** a Content View after repository sync (new version in **Library**). Promotion into lifecycle environments is handled by [`satellite_promote_lifecycle`](../satellite_promote_lifecycle/README.md).

## Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `satellite_content_view` | `""` (required) | Content View name to publish |

## Notes

- Publishing is **not idempotent** — each run creates a new Content View version when content changed.

## Tags

`publish`
