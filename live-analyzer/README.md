# Personal Investment Portfolio Dashboard

A private, secure, and self-hosted personal investment portfolio dashboard designed to track total net worth across Stocks, Mutual Funds, Fixed Deposits (FDs), and Gold.

---

## Features

1. **Zerodha Kite Integration (Read-Only)**
   * Daily manual OAuth reconnect flow (for security, 2FA automation is avoided).
   * Fetches equity holdings and mutual fund (Coin) holdings securely.
2. **Price & NAV Enrichment**
   * Real-time stock prices fetched from NSE via `jugaad-data` / `yfinance` fallback.
   * Daily Mutual Fund Net Asset Values (NAV) fetched directly from AMFI (supporting ISIN and Scheme Code mapping).
3. **Manual Asset CRUD (FD & Gold)**
   * **Fixed Deposits**: Compounding interest accrual calculations (compounding monthly, quarterly, or yearly) automatically updated over time.
   * **Gold**: Live gold spot price calculations in INR per gram using USD Gold Futures and USD/INR exchange rates via `yfinance`.
4. **Portfolio Analytics**
   * Holding-specific and category-level CAGR/XIRR (using bisection and Newton-Raphson solvers).
   * Asset allocation breakdowns and unrealized P&L.
5. **Historical Performance**
   * Daily background scheduler (APScheduler) taking portfolio value snapshots for net-worth growth trend charts.
6. **Defense in Depth**
   * Application binds only to Tailscale or localhost interfaces.
   * Fernet symmetric encryption of Kite access tokens at rest.
   * PyJWT/Bcrypt app-password gateway.

---

## Setup Instructions

### 1. Zero-Cost Credentials

#### A. Zerodha Kite Connect
1. Visit the [Kite Developer Console](https://kite.trade/).
2. Create an account and register a **Personal (free) developer app**.
3. Set your Redirect URL to: `http://localhost:8000/api/auth/callback` (or your Tailscale URL when deploying).
4. Note down your **API Key** and **API Secret**.

#### B. Generate Encryption Key & Password Hash
Run the following helper command in your terminal to generate a secure Fernet key and a hashed password for your dashboard:

```bash
# Generate Fernet Encryption Key
python3 -c "from cryptography.fernet import Fernet; print('ENCRYPTION_KEY=' + Fernet.generate_key().decode())"

# Generate Bcrypt Password Hash (change 'yourpassword' to your desired password)
python3 -c "import bcrypt; print('APP_PASSWORD_HASH=' + bcrypt.hashpw(b'yourpassword', bcrypt.gensalt()).decode())"
```

---

### 2. Environment Configuration

Create a `.env` file at the project root by copying the template:

```bash
cp .env.example .env
```

Edit `.env` and fill in the values:
```env
KITE_API_KEY=your_zerodha_api_key
KITE_API_SECRET=your_zerodha_api_secret
ENCRYPTION_KEY=the_fernet_key_you_generated
APP_PASSWORD_HASH=the_bcrypt_hash_you_generated

BIND_IP=127.0.0.1  # Set to your Tailscale IP when deploying (e.g. 100.x.y.z)
PORT=8000
DATABASE_URL=sqlite:///./portfolio.db
FRONTEND_URL=http://localhost:5173
```

---

### 3. Quick Start (Development)

Run the master start script from the root folder:

```bash
./start.sh
```

This will automatically:
1. Create a Python virtual environment (`venv`) and install backend dependencies.
2. Initialize the local SQLite database (`portfolio.db`).
3. Start the FastAPI backend server (`http://127.0.0.1:8000`).
4. Launch the React Vite development server (`http://localhost:5173`).

Open **[http://localhost:5173](http://localhost:5173)** in your browser!

---

## Production & Tailscale Deployment

This application has no public DNS, no reverse proxy, and no open public inbound ports. It is designed to run locally or on a private network via **Tailscale**.

1. Ensure **Tailscale** is installed and active on the host machine and your devices.
2. Get your host machine's Tailscale IP:
   ```bash
   tailscale ip -4
   ```
3. Update your `.env` file:
   * Change `BIND_IP` to your Tailscale IP (e.g., `100.x.y.z`).
   * Change `FRONTEND_URL` to `http://100.x.y.z:5173` (where `100.x.y.z` is your Tailscale IP).
4. Run `./start.sh` or configure them as systemd background services. You can now securely access the dashboard from any of your Tailscale-connected devices (phone, laptop, tablet).
