# CertiChain React Frontend

## Backend target (swayam)

This frontend is configured to call the swayam backend by using:

- `VITE_SWAYAM_API_BASE_URL`

Default fallback in code:

- `http://localhost:8000`

Create a `.env` file in this folder and set:

```env
VITE_SWAYAM_API_BASE_URL=http://localhost:8000
```

Use `8000` if swayam backend is running on its default port, or `8001` (or any other port) if you run it on a custom port.

## Run

```bash
npm install
npm run dev
```
