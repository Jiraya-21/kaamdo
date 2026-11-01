# Karnataka locations

KaamDo listings use official Karnataka names. This file does not invent villages or coordinates.

## Hierarchy

1. **State** — Karnataka (fixed).
2. **District** — 31 official districts, including Bengaluru Urban, Bengaluru Rural, and Bengaluru South.
3. **Taluk** — official taluks for the chosen district.
4. **Locality** — typed by the user. KaamDo does not ship a village list.

Matching still needs a real GPS fix from the phone. A district or taluk name is a label, not a map pin.

## Official sources (retrieved 27 October 2026)

| Source | Used for |
| --- | --- |
| [Karnataka district portal](https://karnataka.s3waas.gov.in/) | 31 district names, including Bengaluru South. |
| [Bengaluru South NIC](https://bengalurusouth.nic.in/en/) | Rename from Ramanagara on 23 May 2025; taluks Ramanagara, Channapatna, Kanakapura, Magadi, Harohalli. |
| [List of taluks of Karnataka](https://en.wikipedia.org/wiki/List_of_taluks_of_Karnataka) | Taluk names by district. Wikipedia OCR typos were not copied. Villages and coordinates were not copied. |

The district portal HTML mixed the Mandya label with Raichur. Mandya is an established official district and is included.

Ramanagara is stored as an alias of **Bengaluru South**. It is not a 32nd district.

## What the app does

- Catalog API: `GET /api/v1/locations/catalog/`
- Districts: `GET /api/v1/locations/districts/`
- Taluks: `GET /api/v1/locations/taluks/?district=Bengaluru%20South`
- Forms and filters use official dropdowns.
- Cards show locality, taluk, and district. They do not show raw latitude or longitude.
- Seed command (isolated database only):

```powershell
cd backend
..\venv\Scripts\python.exe manage.py seed_karnataka_locations
```

Do not run this against `backend/db.sqlite3` unless you intend to write that file. This pass did not.

## Maps

Default `KAAMDO_MAP_PROVIDER=none`. There is no Nominatim autocomplete. KaamDo does not invent district centroids as precise pins. If you later set `osm`, the page may show OpenStreetMap attribution after a real GPS fix.

## Code

Source of truth: `backend/locations/catalog.py`.
