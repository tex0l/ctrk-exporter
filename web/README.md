# CTRK-Exporter Web Edition

Browser-based telemetry analyzer for Yamaha Y-Trac motorcycle telemetry files (.CTRK). Built with Astro and Vue.js, featuring interactive GPS track visualization and multi-channel telemetry graphs.

## Features

- 100% client-side processing (no server required)
- Drag-and-drop .CTRK file upload
- Interactive GPS track visualization (Leaflet.js)
- Multi-channel telemetry graphs (Chart.js)
- Lap-by-lap analysis with data table
- 21 telemetry channels at 10 Hz
- Web Worker parsing for non-blocking UI
- Dark theme optimized for telemetry analysis

## Stack

| Component | Technology |
|-----------|-----------|
| Framework | Astro (static site) |
| UI Components | Vue.js 3 |
| Map | Leaflet.js |
| Charts | Chart.js |
| Parser | TypeScript (shared with CLI) |
| Build | Vite |

## Development

### Prerequisites

- Node.js 20+
- npm or pnpm

### Install Dependencies

```bash
npm install
```

### Run Development Server

```bash
npm run dev
```

The app will be available at `http://localhost:4321`.

### Type Checking

```bash
npm run typecheck
```

### Testing

```bash
npm test              # Run tests once
npm run test:watch    # Watch mode
```

## Production Build

### Build Locally

```bash
npm run build
```

This creates a static site in `dist/` directory containing:

- Optimized HTML, CSS, JS
- Hashed asset filenames for cache busting
- Compressed bundles (gzip/brotli)
- Total size: ~170 KB gzipped

Build output:
```
dist/
├── _astro/              # JS/CSS bundles (cache: 1 year)
│   ├── chart.*.js       # Chart.js (71 KB gzipped)
│   ├── leaflet-src.*.js # Leaflet (43 KB gzipped)
│   ├── parser-worker.*.js  # CTRK parser in Web Worker
│   └── *.css            # Component styles
├── analyze/
│   └── index.html       # Analysis page
├── index.html           # Landing page
├── favicon.svg
└── robots.txt
```

### Preview Production Build

```bash
npm run preview
```

This serves the `dist/` directory locally at `http://localhost:4321`.

## Deployment

The web app is a **fully static site** with no server-side code. It can be deployed to any static hosting service.

### Deploy to Netlify

#### Option 1: CLI Deployment

1. Install Netlify CLI:
   ```bash
   npm install -g netlify-cli
   ```

2. Login to Netlify:
   ```bash
   netlify login
   ```

3. Deploy:
   ```bash
   # Build first
   npm run build

   # Deploy to production
   netlify deploy --prod
   ```

#### Option 2: Git Integration

1. Push code to GitHub/GitLab/Bitbucket
2. Go to [Netlify](https://netlify.com)
3. Click "New site from Git"
4. Select your repository
5. Configure build settings:
   - **Base directory**: `web/`
   - **Build command**: `npm run build`
   - **Publish directory**: `web/dist/`
6. Deploy

The `netlify.toml` file is already configured with:
- Build command and output directory
- Security headers (CSP, X-Frame-Options, etc.)
- Cache headers (1 year for assets, 1 hour for HTML)
- Compression settings

### Deploy to Vercel

#### Option 1: CLI Deployment

1. Install Vercel CLI:
   ```bash
   npm install -g vercel
   ```

2. Deploy:
   ```bash
   # Build first
   npm run build

   # Deploy to production
   vercel --prod
   ```

#### Option 2: Git Integration

1. Push code to GitHub/GitLab/Bitbucket
2. Go to [Vercel](https://vercel.com)
3. Click "Import Project"
4. Select your repository
5. Configure project:
   - **Framework Preset**: Astro
   - **Root Directory**: `web/`
   - **Build Command**: `npm run build`
   - **Output Directory**: `dist/`
6. Deploy

The `vercel.json` file is already configured with:
- Build command and output directory
- Security headers
- Cache headers

### Deploy to Other Platforms

The site can be deployed to any static hosting service:

| Platform | Documentation |
|----------|--------------|
| GitHub Pages | [Deploy Astro to GitHub Pages](https://docs.astro.build/en/guides/deploy/github/) |
| Cloudflare Pages | [Deploy Astro to Cloudflare Pages](https://docs.astro.build/en/guides/deploy/cloudflare/) |
| AWS S3 + CloudFront | [Static Website Hosting](https://docs.aws.amazon.com/AmazonS3/latest/userguide/WebsiteHosting.html) |
| Firebase Hosting | [Deploy Astro to Firebase](https://firebase.google.com/docs/hosting) |

**Build requirements:**
- Build command: `npm run build`
- Output directory: `dist/`
- Node.js version: 20+

## Configuration

### Environment Variables

**None required.** The app is 100% client-side and requires no environment variables or API keys.

### Base Path

If deploying to a subdirectory (e.g., `example.com/ctrk/`), update `astro.config.mjs`:

```js
export default defineConfig({
  base: '/ctrk',
  // ...
});
```

### Custom Domain

After deploying, you can configure a custom domain in your hosting provider's dashboard:

- **Netlify**: Site settings > Domain management
- **Vercel**: Project settings > Domains

## Project Structure

```
web/
├── src/
│   ├── components/       # Vue components
│   │   ├── AppHeader.vue
│   │   ├── FileUpload.vue
│   │   ├── AnalyzePage.vue  # Main analysis UI
│   │   └── Toast.vue
│   ├── composables/      # Vue composables (shared state)
│   │   └── useTelemetryData.ts
│   ├── layouts/
│   │   └── BaseLayout.astro
│   ├── pages/            # Astro pages
│   │   ├── index.astro   # Landing page
│   │   └── analyze.astro # Analysis page
│   └── workers/
│       └── parser-worker.ts  # Web Worker for CTRK parsing
├── public/               # Static assets (copied to dist/)
│   ├── favicon.svg
│   └── robots.txt
├── astro.config.mjs      # Astro configuration
├── netlify.toml          # Netlify deployment config
├── vercel.json           # Vercel deployment config
├── package.json
└── tsconfig.json
```

## Browser Compatibility

Requires a modern browser with:
- Web Workers
- File API
- ES2020+ features
- Canvas API (for charts)

Tested on:
- Chrome 90+
- Firefox 88+
- Safari 14+
- Edge 90+

## Security

The app implements security best practices:

- **Content Security Policy (CSP)**: Restricts resource loading
- **X-Frame-Options**: Prevents clickjacking
- **X-Content-Type-Options**: Prevents MIME sniffing
- **Referrer-Policy**: Controls referrer information
- **Permissions-Policy**: Disables unused browser features

All processing happens client-side. No data is sent to any server.

## Performance

| Metric | Value |
|--------|-------|
| Initial load | ~170 KB gzipped |
| Time to Interactive | < 2s (fast 3G) |
| Lighthouse Score | 95+ |
| Parser performance | ~100ms for 30-minute session |

Optimizations:
- Vite code splitting
- Lazy loading of heavy components (map, charts)
- Web Worker parsing (non-blocking UI)
- 1-year cache for hashed assets
- Tree-shaking (Chart.js, Leaflet)

## License

See parent project for license information.

## Related Projects

- `parser/` - TypeScript parser (npm package)
- `src/ctrk_parser.py` - Python reference parser
- `ctrk-exporter` - Python CLI tool

## Support

For issues and feature requests, see the main project repository.
