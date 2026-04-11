# Design System Strategy: The Immutable Document

## 1. Overview & Creative North Star: "The Digital Curator"
This design system is built on the philosophy of **"The Digital Curator."** In a world of fleeting digital data, this system treats blockchain-verified credentials with the same reverence as a physical gallery or a high-end editorial publication. We move away from the "SaaS dashboard" aesthetic of heavy shadows and card-based layouts. Instead, we embrace **Swiss Minimalist Brutalism**: a high-contrast, typographically-led experience where the "Paper" is the foundation, and the "Ink" is the truth.

The experience is defined by **intentional asymmetry**. We do not fill the screen with boxes; we anchor elements to a rigid grid but leave vast areas of whitespace (breathing room) to signal prestige and clarity. Every pixel must feel intentional, as if typeset by a master printer.

---

## 2. Colors & Surface Philosophy
The palette is rooted in tactile materials: Ink, Paper, Seal, and Mist. 

### Core Palette
- **Ink (#0F0F0F):** High-density black for definitive text, icons, and primary interactions.
- **Paper (#FAFAF8):** An off-white, warm-neutral background that reduces eye strain and feels more "archival" than pure white.
- **Seal (#C17A3A):** Our primary accent. Used for verified states and "Actionable Gold"—representing the historical wax seal of authenticity.
- **Mist (#E8E6E1):** Our architectural color. Used for subtle structure.

### The "No-Line" Rule & Surface Hierarchy
While the prompt allows for Mist borders, we prioritize **Tonal Layering** to define hierarchy.
- **Prohibited:** Do not use 1px solid borders to section off large areas of the layout. 
- **The Surface Shift:** Use `surface-container-low` (#F6F3F2) to set off secondary content areas against the main `surface` (#FCF9F8/Paper).
- **The "Ghost Border" Fallback:** If a container requires definition (e.g., an input field), use a 1px border of **Mist (#E8E6E1)** at 50% opacity. Never use high-contrast black borders for structural containers.

---

## 3. Typography: The Editorial Engine
Typography is the primary visual signal of authority. We pair a high-contrast serif with a technical sans and a precision mono.

### Display (Instrument Serif)
*Traditional, authoritative, academic.*
- **Display-LG:** 64px / 1.1 Line Height / -0.02em Tracking
- **Display-MD:** 40px / 1.1 Line Height / -0.01em Tracking
- **Display-SM:** 28px / 1.2 Line Height

### UI Text (Geist / Inter)
*Functional, clean, modern.*
- **Body-MD:** 15px / 1.5 Line Height (The workhorse for all content).
- **Label-SM:** 11px / Uppercase / 0.08em Tracking (Used for metadata, small captions, and categories).

### Data (Geist Mono)
*Technical, precise, immutable.*
- **Mono-MD:** 13px (Hashes, Transaction IDs, Blockchain data).
- **Mono-SM:** 12px (Timestamped logs).

---

## 4. Elevation & Depth: Atmospheric Weight
We reject the "floating card" trend. This system is grounded.

- **The Layering Principle:** Depth is achieved by stacking. A `surface-container-lowest` (#FFFFFF) element sits atop a `surface` (#FCF9F8) background to create a "lift" without a shadow.
- **Ambient Shadows:** Only use shadows for temporary floating elements (Modals, Popovers). 
  - **Token:** `0 1px 3px rgba(15, 15, 15, 0.06)`. This is a "whisper shadow" that mimics the thickness of heavy paper rather than a digital glow.
- **Glassmorphism:** For navigation bars or sticky headers, use a backdrop-blur (12px) with a semi-transparent **Paper (#FAFAF8BB)** fill. This maintains the "Editorial" feel while allowing content to flow underneath.

---

## 5. Components

### Buttons & Interaction
- **Primary Action:** Solid **Ink (#0F0F0F)** with **Paper (#FAFAF8)** text. 6px radius. No gradient. 
- **Secondary Action:** 1px **Mist (#E8E6E1)** border, **Ink** text.
- **States:** On hover, the primary button shifts to **Seal (#C17A3A)**. This is the only time Seal is used for a large surface area.

### Status Badges (The "Seal" Logic)
Status must be communicated through text and stroke only. **No background fills.**
- **Verified:** `#2A7A5A` | 1px solid currentColor | 11px Geist Mono.
- **Revoked:** `#B03A2A` | 1px solid currentColor | 11px Geist Mono.
- **Pending:** `#8A6A20` | 1px solid currentColor | 11px Geist Mono.

### Data Inputs
- **Style:** 1px Mist border, 6px radius. On focus, the border becomes **Seal (#C17A3A)**.
- **Labels:** Always use **Label-SM** (11px Uppercase) positioned precisely 8px above the input.

### Lists & Tables
- **Rule:** Forbid horizontal divider lines between every row.
- **Solution:** Use vertical whitespace (16px–24px) to separate list items. If separation is visually required, use a subtle background shift to `surface-container-low` on hover.

---

## 6. Do’s and Don’ts

### Do
- **Embrace Asymmetry:** Align the main header to the left, but place secondary data points in the far right margin.
- **Use Mono for Integrity:** Use Geist Mono for any string of characters that represents a blockchain truth (hashes, keys).
- **Respect the Paper:** Keep the background clean. Avoid filling every corner of the screen.

### Don't
- **No Gradients:** We use flat, solid colors to represent the permanence of the ledger.
- **No Heavy Shadows:** If it looks like it’s "floating" more than 1mm off the page, the shadow is too heavy.
- **No Card-in-Card:** Avoid nesting cards. Use typography and whitespace to create sections instead of adding more boxes.
- **No Icons as decoration:** Icons must serve a functional purpose (e.g., an arrow indicating a link). Do not use icons just to "fill space."