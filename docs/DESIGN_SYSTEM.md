# Design system

The visual direction for WearWise. M1 turns this into tokens and components, with a `/styleguide` page that is checked against this file before anything else is built on top.

## Direction

**A photo studio backdrop, not a shop window.** The clothes are the only colourful thing on the screen. Everything else is the pale grey paper a stylist lays garments on: quiet, even, slightly cool. The usability comes from shopping apps (photo grids, filter chips, sort, sticky filters); the look does not. No sale banners, no brand colours shouting, no carousels.

It should feel light and calm, and equally at home showing a sherwani, a hoodie, or a saree. Nothing in the chrome should read as menswear or womenswear.

## Colour

| Token | Hex | Use |
|---|---|---|
| `paper` | `#F4F5F3` | Page background |
| `surface` | `#FFFFFF` | Cards, sheets, inputs |
| `tile` | `#E8EAE7` | Behind every garment photo |
| `line` | `#D9DCD8` | Dividers and card edges (decorative; never the only cue) |
| `line-strong` | `#858A91` | Borders of inputs and selects: 3.5:1 on `surface`, 3.2:1 on `paper` |
| `ink` | `#1B1D20` | Text, primary buttons |
| `ink-soft` | `#5A5F66` | Secondary text |
| `indigo` | `#2C3A82` | Links, selected states, focus ring, active tab |
| `buy` | `#1F7A4D` | Buy verdict, success |
| `consider` | `#8A5A00` | Consider verdict, warnings |
| `skip` | `#B3261E` | Skip verdict, errors, destructive actions |

Measured contrast: `ink` on `paper` 15.4:1, `ink-soft` on `paper` 5.9:1, `indigo` on `surface` 10.3:1, verdict colours on `surface` all above 5:1. All pass WCAG AA for body text.

Rules:
- One accent. Indigo marks what is selected or clickable. It is the colour of indigo dye and denim, and it is not any retailer's brand colour.
- Primary buttons are `ink` with white text. Indigo is not a button fill.
- Verdict colours appear only on verdicts and system messages, always with an icon or word, never colour alone.
- No gradients. No coloured section backgrounds.
- Depth comes from `tile` against `surface` against `paper`, not from shadows. One soft shadow is allowed, on floating layers only (dialogs, menus, the add button).

Light theme only for v1. Keep every colour as a CSS variable so a dark theme stays possible.

## Type

| Role | Typeface | Notes |
|---|---|---|
| Display | Bricolage Grotesque | Page titles, outfit names, big numbers. Weight 600, tight tracking, sentence case. |
| Text and UI | Instrument Sans | Everything else. Weights 400 and 500. |

Both are on Google Fonts. Load them with `next/font` so they are self-hosted.

Scale (px): 12, 14, 16, 20, 28, 40. Body is 16 on desktop and phone. Line height 1.5 for text, 1.15 for display. Prices and counts use tabular numerals.

Rules:
- Sentence case everywhere, including buttons and labels. No all-caps labels.
- No decorative labels above headings. A heading is enough.
- Line length under 75 characters for any paragraph.

## Shape and space

- Spacing scale: 4, 8, 12, 16, 24, 32, 48, 64.
- Radius: 12 px on photo tiles and cards, 8 px on inputs and buttons, full on chips. Three values, used by role.
- Photo tiles are 3:4 portrait, image fitted inside with padding so garments never touch the edge.
- Hit targets at least 44 px.
- Grid: 2 columns on phones, 3 at 640 px, 4 at 1024 px, 5 or 6 at 1440 px.

## The signature: the outfit board

One element carries the personality. An outfit is shown as a **flat-lay board**: its items arranged on one `tile` the way they would be laid out on a bed.

```
+-------------------------------+
|   [ top ]        [ layer ]    |
|                               |
|   [ bottom ]     [ watch ]    |
|                  [ belt  ]    |
|   [ shoes ]      [ bag   ]    |
+-------------------------------+
  ■ ■ ■ □   Smart casual, for college
  Navy and beige are an easy pair; you haven't worn the loafers in 12 days.
```

- Positions are fixed by slot, so every outfit reads the same way at a glance.
- Under the board, a **swatch strip**: small squares of the outfit's actual colours.
- Then the occasion and the reason, in plain text.
- When a new suggestion appears, the pieces settle into place in a quick stagger (about 40 ms apart). This is the only non-triggered animation in the app, and it is skipped when the user prefers reduced motion.

Everything around the board stays plain so the board stands out.

## Components for M1

Button (primary, secondary, quiet, destructive; with loading state), text input, select, checkbox, radio, switch, chip (filter and removable), tabs, card, photo tile, dialog, bottom sheet (phone), toast, tooltip, skeleton, empty state, error state, pagination or "load more", avatar menu.

Each component needs: default, hover, focus-visible, active, disabled, loading (where relevant), and error (where relevant) states, all visible on `/styleguide`.

## Navigation

- **Desktop:** left sidebar with Home, Wardrobe, Outfits, My Week, Shopping, Insights, Stylist; Settings in the avatar menu.
- **Phone:** bottom tab bar with Home, Wardrobe, Outfits, My Week, and More; a floating add button above it.
- Show a destination only once its page exists. M1 ships with Home and Settings only.

## Patterns borrowed from shopping apps

- Sticky filter bar with chips; filters open in a left rail on desktop and a bottom sheet on phones.
- Active filters shown as removable chips with a "Clear all".
- Sort menu at the top right of any grid.
- Result count next to the page title.
- Search with instant results.
- Colour filters as swatches, not words.
- Photo first, text second, on every card.

## Writing

- Plain verbs. Buttons say what happens: "Add item", "Save outfit", "Mark as worn".
- The same action keeps the same name everywhere. "Save outfit" produces "Outfit saved".
- Empty states tell the user what to do next: "Your wardrobe is empty. Add your first item. A photo and a colour are enough."
- Errors say what went wrong and what to do: "That file is 14 MB. Photos can be up to 8 MB."
- No exclamation marks, no apologies, no jokes in errors.
- Never comment on the user's body, budget, or how much they own.

## Accessibility floor

- Every interactive element reachable and usable by keyboard, with a visible indigo focus ring.
- Every image has alt text built from the item's name, colour, and category.
- Form fields have visible labels; errors are tied to their fields.
- Colour is never the only signal.
- `prefers-reduced-motion` respected.
- Tested at 200% zoom and 375 px width.
