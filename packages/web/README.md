# DealScannr Web

React 19 + Vite + Tailwind. Dev server port **5100**.

## Setup

```bash
cd packages/web
npm install
```

## Environment

- `VITE_API_URL` — backend origin (default `http://localhost:5200`).

## Commands

- `npm run dev` — Vite dev server (`localhost:5100`).
- `npm run preview` — production preview.

Typecheck (no dev server):

```bash
npx tsc --noEmit
```

## E2E (Playwright)

From `e2e/web`: `npm install && npx playwright install && npx playwright test` with the dev app running unless you rely only on route mocks.
