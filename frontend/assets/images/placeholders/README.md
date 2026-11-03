# KaamDo image assets (real photos)

- `placeholders/` — real photo fallbacks: avatar, tractor, hero
- `services/` — one real JPEG per daily-service category slug
- `marketplace/` — account/home destination photos
- `listings/` — jobs / farm / equipment card photos
- `logo.png` / `favicon.png` — product mark

Regenerate (downloads photos + installs logo):

```powershell
..\venv\Scripts\python.exe scripts\generate_image_assets.py
```
