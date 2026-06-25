# Wiki Schema — mifiya (reference example)

> ⚠ STATUS: v0.1 example reflecting the legacy 5-folder Layer-2 structure.
> Pending v0.3 rewrite to match the 19-folder schema agreed 2026-06-25.
> Use `templates/SCHEMA.md` (v0.2) as the authoritative template; treat this file
> as background reading only until updated.
>
> This is an example of a fully filled-in SCHEMA.md for the Mifiya consulting team.
> Use as a template when adapting the default SCHEMA.md to a specific team.

## Domain

Mifiya consulting engagement — AI consulting for a Taiwanese F&B/lifestyle brand.
The vault covers Mifiya's brand assets, internal SOPs, product lines, AI consultant
deliverables, and the methodology used during the engagement.

## Conventions

- File names: lowercase, hyphens (e.g., `mifiya-brand-voice.md`)
- All standard frontmatter required
- `[[wikilinks]]` minimum 2 per page
- Meeting transcripts: `raw/transcripts/YYYY-MM-DD-<topic>.md`
- Weekly consultant reports: `syntheses/weekly-report-YYYY-WW.md`
- Deliverables tagged with the engagement phase code (e.g., `phase-1`, `phase-2`)

## Frontmatter

Standard. `sources` always points to one or more `raw/` files.

## Tag taxonomy

### Brand & Product
- `brand` — Mifiya brand identity, voice, visual
- `product` — specific Mifiya product lines
- `pricing` — pricing structures, packages
- `positioning` — market positioning, target audience

### Engagement
- `phase-1`, `phase-2`, `phase-3` — engagement phases
- `deliverable` — formal output delivered to client
- `meeting` — meeting notes / decisions
- `interview` — customer / stakeholder interview
- `consultant-note` — Ansai's internal working notes

### People & Orgs
- `person` — individual stakeholders (Mifiya team, customers, partners)
- `team` — Mifiya internal teams or our consultant team
- `partner` — Mifiya's vendors, partners, clients
- `competitor` — competitive brands

### Knowledge & Methods
- `framework` — methodologies applied (AIDA, JTBD, etc.)
- `tool` — tools used (LanceDB, Notion, Discord, OpenClaw)
- `template` — reusable templates
- `case-study` — past cases referenced
- `lesson-learned` — retrospective insights

### Meta
- `comparison` — side-by-side analysis pages
- `timeline` — chronological event pages
- `open-question` — unresolved issues
- `decision` — recorded decisions with rationale
- `contradiction` — flagged conflicting info

## Page thresholds

Same as default, but with these additions:
- **Create a page** for every Mifiya product line, even if mentioned only once
- **Create a page** for every recorded decision (Mifiya engagement requires a decision log)
- **Don't create pages** for one-off meeting attendees who never appear again

## Team-specific overrides

- Every deliverable must link to [[engagement-overview]]
- Brand voice references must link to [[mifiya-brand-voice]]
- All weekly reports must link forward to the next week and back to the previous one
- Customer interview notes must list the interviewer and date in frontmatter
- All sources from Mifiya internal Notion go in `raw/articles/notion-<page-id>.md`
