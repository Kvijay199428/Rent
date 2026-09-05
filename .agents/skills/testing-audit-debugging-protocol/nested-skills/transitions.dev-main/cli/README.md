# transitions-pro

Install [transitions.dev](https://transitions.dev) CSS/React transitions into your project from the terminal. Free transitions work with no account; Pro transitions unlock after a passwordless browser sign-in.

```bash
npx transitions-pro list                 # list free + Pro transitions
npx transitions-pro add card-resize       # add a free transition (instant)

npx transitions-pro add --pro             # add every Pro recipe (signs you in if needed)
npx transitions-pro skill                 # install the Pro transitions as an agent skill
npx transitions-pro logout               # sign out
```

`add --pro` and `skill` both sign you in automatically (browser device-flow) the first
time. Recipes are written to `./transitions/` (override with `--dir <path>`); the skill
installs to `~/.claude/skills/transitions-pro/` (override with `--dir <path>`).

## How Pro auth works

`login` uses a device-authorization flow: the CLI prints a short code and opens your browser, you confirm while signed in to your Transitions Pro account, and the CLI receives a scoped token. No password or API key is ever entered in the terminal. Your Pro entitlement is re-checked on every download, so access ends immediately if your plan lapses — recipes you already pulled keep working.

This package contains **no premium source** — Pro recipes are fetched from the authenticated `api.transitions.dev` service.

MIT for the CLI; installed transitions are covered by the [Transitions.dev license](https://transitions.dev/terms.html).
