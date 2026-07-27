# Agent Usage

Agents should call high-level business commands instead of browser selectors.

Preferred pattern:

```bash
bili search "AI programming" --limit 5 --json
bili video info 1 --json
bili comments 1 --count 10 --json
```

When a command returns `CAPTCHA_REQUIRED`, ask the user to run `bili login` or retry from a browser-backed session.
