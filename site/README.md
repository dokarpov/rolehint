# RoleHint public site

Live: https://dokarpov.github.io/rolehint/site/

The static GitHub Pages site holds the product presentation, a native guided product view with three selectable roles, the decision desk (`assess.html`, `check.html`), onboarding, pricing, subscription, install and privacy pages, and the example workspace (`workspace.html`).

## User journey

Start at the [public site](https://dokarpov.github.io/rolehint/site/) and use **Start free** to open `workspace.html`. First-time visitors upload or paste a CV, or go straight to example jobs. Onboarding runs choose/paste CV → review editable text → confirm hiring rules → a guided first job review. Search preferences are saved locally, Preferences has a control to delete the local CV, and saved or passed decisions persist in localStorage across visits.

[Pricing](https://dokarpov.github.io/rolehint/site/pricing.html) and [Subscription](https://dokarpov.github.io/rolehint/site/subscription.html) describe the free start: no payment details, no automatic renewal.

## Install

A web manifest and service worker enable PWA use. In Safari on iOS choose **Share → Add to Home Screen**; in Android or desktop browsers choose **Install**. `install.html` explains each path. The manifest `start_url` opens `workspace.html`. Offline access never queues form submissions.

## Forms

Forms post to `https://formsubmit.co/dokarpov@gmail.com` with CAPTCHA, a honeypot field and a thank-you redirect; `early-access.js` reports submission progress without intercepting the POST.

## Brand and UI

Purple icon: `favicon.svg`. Typography and material tokens: `design-lock.css` and `silver-restore.css`. Rules: `../docs/DESIGN_SYSTEM.md`. `release-v1.css` and `release-v1.js` provide the guided product view.

## Privacy

`privacy.html` covers data flows, legal bases, processors and transfers, retention, rights, local storage, security incidents and AI processing. The service-worker cache version `rolehint-public-v3` keeps privacy content current.

## QA

`qa-release.mjs` (workflow `../.github/workflows/release-qa.yml`) checks 320/375/390/768/1024/1440 px widths, the guided view, CTA, form wiring and privacy layout in headless Chromium. `qa-workspace.mjs` (workflow `../.github/workflows/prototype-ux.yml`) covers the onboarding scenarios.
