# Frontend

This folder contains the React and Vite client for CertiChain. It provides the browser experience for universities, students, and verifiers.

## What It Includes

- landing and navigation flows
- university issue and revoke pages
- student vault and QR-based sharing views
- verifier and employer verification pages
- shared API client for the FastAPI backend

## Tech Stack

- React
- Vite
- React Router
- Axios
- Tailwind-based styling and custom UI components

## Environment

The frontend expects the backend base URL through `VITE_SWAYAM_API_BASE_URL`.

Copy the example file:

```powershell
cd CertiChain/frontend
Copy-Item .env.example .env.local
```

Example value:

```env
VITE_SWAYAM_API_BASE_URL=http://localhost:8000
```

## Install And Run

```powershell
cd CertiChain/frontend
npm install
npm run dev
```

Useful commands:

```powershell
npm run build
npm run preview
npm run lint
```

## Important Files

- `CertiChain/frontend/src/App.jsx`: route registration
- `CertiChain/frontend/src/api/client.js`: backend API wrapper
- `CertiChain/frontend/src/pages`: app screens
- `CertiChain/frontend/.env.example`: frontend environment template

## Notes

- `dist` and `node_modules` are generated and should not be committed.
- The default development backend URL is `http://localhost:8000`.
- If the student or verifier views look empty, check the backend first for IPFS or blockchain connectivity issues.
