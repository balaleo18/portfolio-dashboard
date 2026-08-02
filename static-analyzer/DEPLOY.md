# Hosting & Deployment Guide: `static-analyzer`

The **`static-analyzer`** is a pure client-side React single-page application. Because it contains no database or backend servers and parses your Zerodha holdings spreadsheet entirely in-memory in your browser, it can be hosted for **100% free** on static hosting platforms.

This guide outlines how to host it securely.

---

## Option 1: Cloudflare Pages (Recommended)

Cloudflare Pages is the best hosting choice because it offers unlimited free bandwidth and integrates natively with **Cloudflare Access (Zero Trust)** to password-protect your site for free.

### Method A: Deploy via GitHub Integration (Continuous Deployment)
This is the easiest path. Every time you push changes to your private GitHub repository, Cloudflare will automatically build and deploy them.

1.  Log in to your **Cloudflare Dashboard** (or create a free account at [dash.cloudflare.com](https://dash.cloudflare.com)).
2.  In the left sidebar, navigate to **Workers & Pages** -> **Create application** -> **Pages** tab -> **Connect to Git**.
3.  Authenticate with your GitHub account, search for, and select your private repository: `balaleo18/portfolio-dashboard`.
4.  Configure the build settings:
    *   **Project Name**: `portfolio-analyzer` (or your preferred name)
    *   **Production Branch**: `main`
    *   **Framework Preset**: `Vite` (or select `None` and fill in the details below)
    *   **Build Command**: `npm run build`
    *   **Build Output Directory**: `static-analyzer/dist`
    *   **Root Directory**: `/static-analyzer` *(Important: Point this to the static-analyzer subdirectory)*
5.  Click **Save and Deploy**. Cloudflare will build the React bundle and provide a live `.pages.dev` URL!

---

### Method B: Deploy via Wrangler CLI (Direct Upload)
If you prefer deploying directly from your local terminal without linking GitHub:

1.  Inside the `static-analyzer/` folder, install the Cloudflare Wrangler CLI helper:
    ```bash
    npm install --save-dev wrangler
    ```
2.  Login to your Cloudflare account from the terminal:
    ```bash
    npx wrangler login
    ```
3.  Deploy the pre-compiled `dist` folder:
    ```bash
    npx wrangler pages deploy dist --project-name=portfolio-analyzer
    ```
    *(Wrangler will guide you through creating a new Pages project on your Cloudflare account if it doesn't already exist).*

---

### Security: Lock Down Your Dashboard with Cloudflare Access
Even though the static analyzer contains **no personal financial data** (the dashboard template is blank until you drag and drop your spreadsheet), you can secure access to the URL so that only you can open the page.

1.  In the Cloudflare sidebar, click **Zero Trust**.
2.  Navigate to **Access** -> **Applications** -> **Add an application**.
3.  Select **Self-hosted**.
4.  Configure the application details:
    *   **Application Name**: `Portfolio Dashboard`
    *   **Application Domain**: Enter your Pages URL (e.g., `portfolio-analyzer.pages.dev`).
5.  Under **Policies**, define who can log in:
    *   **Policy Name**: `Owner Access`
    *   **Action**: `Allow`
    *   **Configure Rules**: Set selector to `Emails` and enter your email address (e.g., your login email).
6.  Click **Next** and save the policy.
7.  Now, visiting your Pages URL will present a secure Cloudflare login page. Cloudflare will send a 6-digit one-time passcode (OTP) to your email to authorize access.

---

## Option 2: Netlify (Alternative Free Host)

Netlify is another excellent free static host.

1.  Create a free account at [netlify.com](https://www.netlify.com).
2.  Click **Add new site** -> **Import from Git**.
3.  Connect your GitHub account and choose `balaleo18/portfolio-dashboard`.
4.  Configure the build settings:
    *   **Base Directory**: `static-analyzer`
    *   **Build Command**: `npm run build`
    *   **Publish Directory**: `static-analyzer/dist`
5.  Click **Deploy site**.

---

## Option 3: Local Serving (Caddy)

If you want to keep the static analyzer purely local alongside the live analyzer:

1.  You can add a block to your [Caddyfile](file:///Users/bala/Documents/Production/live-analyzer/Caddyfile) on another port (e.g., `:3001`):
    ```caddy
    :3001 {
        root * /Users/bala/Documents/Production/static-analyzer/dist
        file_server
        try_files {path} /index.html
    }
    ```
2.  Restart the Caddy server. It will be served on `http://localhost:3001`!
