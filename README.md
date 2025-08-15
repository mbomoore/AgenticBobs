# AgenticBobs

## Development

Run tests with uv:

```bash
uv run python -m pytest -q
```

### Local component sanity check

If the bpmn.io component has trouble loading, use the built-in minimal component under the "Sanity Check" tab in the app. It uses no external JS and simply echoes a timestamp and counter when you click its button. This helps confirm the Streamlit custom component pipeline is working locally.

