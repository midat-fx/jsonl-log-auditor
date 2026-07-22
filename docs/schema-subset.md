# Schema subset

`logaudit validate --schema <file>` checks records against a small, documented
subset of JSON Schema 2020-12. It is intentionally dependency-free and is *not*
a complete implementation.

## Supported keywords

| Keyword | Applies to | Meaning |
|---|---|---|
| `required` | object | listed properties must be present |
| `properties` | object | per-property sub-schemas |
| `type` | any | `string`, `integer`, `number`, `boolean`, `object`, `array`, `null` |
| `enum` | any | value must be one of the listed values |
| `pattern` | string | value must match this regex (`re.search`) |
| `minimum` / `maximum` | number | inclusive numeric bounds |
| `minLength` / `maxLength` | string | inclusive length bounds |
| `format` | string | `date-time`, `ipv4`, `email` |

Notes:
- `integer` rejects booleans; `number` accepts int or float but not bool.
- Unlisted properties are allowed (no `additionalProperties` enforcement).
- Nested object/array schemas beyond `properties` are not validated.

## Example

```json
{
  "required": ["ts", "level", "service", "code"],
  "properties": {
    "ts": {"type": "string", "format": "date-time"},
    "level": {"type": "string", "enum": ["DEBUG", "INFO", "WARN", "ERROR"]},
    "service": {"type": "string", "minLength": 1},
    "code": {"type": "integer", "minimum": 100, "maximum": 599},
    "latency_ms": {"type": "number", "minimum": 0}
  }
}
```

`validate` prints one line per violation as `file:record: message` and exits 1
if the number of bad records exceeds `--max-bad` (default 0).
