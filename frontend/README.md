# Job Role Matcher - Frontend

Next.js 14 frontend dashboard for the Job Role Matcher system.

## Setup

1. Install dependencies using pnpm:
```bash
pnpm install
```

2. Create environment file:
```bash
cp .env.example .env.local
# Edit .env.local with your admin token
```

## Running

Development mode:
```bash
pnpm dev
```

Build for production:
```bash
pnpm build
```

Run production build:
```bash
pnpm start
```

The dashboard will be available at http://localhost:3000

## Project Structure

```
frontend/
├── app/
│   ├── page.tsx           # Dashboard (job list)
│   ├── jobs/
│   │   └── [id]/
│   │       └── page.tsx   # Job detail view
│   ├── api/               # Next.js API routes (proxy to backend)
│   ├── layout.tsx         # Root layout
│   └── globals.css        # Global styles
├── components/            # Reusable components
├── lib/
│   ├── api.ts            # API client functions
│   └── types.ts          # TypeScript types
└── public/               # Static assets
```

## Environment Variables

Create `.env.local` with:

```
NEXT_PUBLIC_API_URL=http://localhost:8000
API_URL=http://localhost:8000
ADMIN_TOKEN=your-secret-token-here
```

- `NEXT_PUBLIC_API_URL`: Backend API URL (client-side)
- `API_URL`: Backend API URL (server-side)
- `ADMIN_TOKEN`: Admin token for protected endpoints (server-side only)

## Development

Type checking:
```bash
pnpm tsc --noEmit
```

Linting:
```bash
pnpm lint
```

Format code:
```bash
pnpm format
```

## Features

- Job listing table with filtering
- Job detail view with fit analysis
- Score breakdown visualization
- Review status tracking
- Refresh trigger for scraping
