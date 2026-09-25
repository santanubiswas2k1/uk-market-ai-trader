import { useEffect, useMemo, useState } from "react";
import { getHealth, getPrediction } from "./api";
import { initialiseAuth, msal, signIn, signOut } from "./auth";
import { config } from "./config";

const quickSymbols = ["BARC.L", "LLOY.L", "SHEL.L", "AZN.L", "BP.L", "GSK.L"];

function pct(value) {
  return typeof value === "number" ? `${(value * 100).toFixed(1)}%` : "—";
}

function metric(value, digits = 3) {
  return typeof value === "number" ? value.toFixed(digits) : "—";
}

function SignalBadge({ signal }) {
  const css = signal ? signal.toLowerCase() : "neutral";
  return <span className={`signal signal-${css}`}>{signal || "—"}</span>;
}

export default function App() {
  const [account, setAccount] = useState(null);
  const [health, setHealth] = useState("checking");
  const [symbol, setSymbol] = useState("BARC.L");
  const [prediction, setPrediction] = useState(null);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");

  const configured = useMemo(
    () =>
      Boolean(
        config.apiBaseUrl &&
          config.entraClientId &&
          config.tenantId &&
          config.apiScope,
      ),
    [],
  );

  useEffect(() => {
    initialiseAuth()
      .then(setAccount)
      .catch((error) => setMessage(error.message));

    if (config.apiBaseUrl) {
      getHealth()
        .then(() => setHealth("online"))
        .catch(() => setHealth("offline"));
    }
  }, []);

  async function runPrediction(nextSymbol = symbol) {
    setBusy(true);
    setMessage("");
    setPrediction(null);

    try {
      const normalized = nextSymbol.trim().toUpperCase();
      setSymbol(normalized);
      const result = await getPrediction(normalized);
      setPrediction(result);
    } catch (error) {
      setMessage(error.message);
    } finally {
      setBusy(false);
    }
  }

  const displayName = account?.name || account?.username || "Signed-in user";

  return (
    <div className="shell">
      <header className="topbar">
        <div>
          <div className="eyebrow">AZURE SERVERLESS • PAPER TRADING</div>
          <h1>UK Market AI Trader</h1>
        </div>
        <div className="account">
          <span className={`status-dot status-${health}`} />
          <span>{health === "online" ? "API online" : health}</span>
          {account ? (
            <>
              <span className="account-name">{displayName}</span>
              <button className="ghost" onClick={signOut}>Sign out</button>
            </>
          ) : (
            <button className="primary" onClick={signIn} disabled={!configured}>
              Sign in with Microsoft
            </button>
          )}
        </div>
      </header>

      <main>
        <section className="auth-panel">
          <div>
            <div className="eyebrow">MICROSOFT ENTRA ID</div>
            <h3>{account ? `Signed in as ${displayName}` : "Sign in to access predictions"}</h3>
            <p>
              {account
                ? "Authentication is active. You can now run protected market predictions."
                : "Use your Microsoft account to authenticate before running predictions."}
            </p>
          </div>
          <div className="auth-actions">
            {account ? (
              <button className="ghost" onClick={signOut}>Sign out</button>
            ) : (
              <button className="primary auth-button" onClick={signIn} disabled={!configured}>
                Sign in with Microsoft
              </button>
            )}
          </div>
        </section>

        {!configured && (
          <div className="alert error">
            <strong>Frontend authentication configuration is incomplete.</strong>
            <div className="config-diagnostics">
              <span>API URL: {config.apiBaseUrl ? "loaded" : "missing"}</span>
              <span>Client ID: {config.entraClientId ? "loaded" : "missing"}</span>
              <span>Tenant ID: {config.tenantId ? "loaded" : "missing"}</span>
              <span>API scope: {config.apiScope ? "loaded" : "missing"}</span>
            </div>
          </div>
        )}

        <section className="hero">
          <div>
            <div className="eyebrow">NEXT TRADING DAY RESEARCH</div>
            <h2>UK equity direction signals with market context</h2>
            <p>
              XGBoost model using LSE price/volume, FTSE 100 context and GBP/USD.
              Evaluation uses expanding-window walk-forward testing.
            </p>
          </div>
          <div className="research-note">
            Research and paper trading only. Predictions are probabilistic and are
            not financial advice.
          </div>
        </section>

        <section className="search-panel">
          <form
            onSubmit={(event) => {
              event.preventDefault();
              runPrediction();
            }}
          >
            <label htmlFor="symbol">London Stock Exchange symbol</label>
            <div className="search-row">
              <input
                id="symbol"
                value={symbol}
                onChange={(event) => setSymbol(event.target.value)}
                placeholder="e.g. BARC.L"
              />
              <button className="primary" disabled={!account || busy}>
                {busy ? "Analysing…" : "Run prediction"}
              </button>
            </div>
          </form>

          <div className="quick-symbols">
            {quickSymbols.map((item) => (
              <button
                key={item}
                className="ticker"
                onClick={() => runPrediction(item)}
                disabled={!account || busy}
              >
                {item}
              </button>
            ))}
          </div>
        </section>

        {message && <div className="alert error">{message}</div>}

        {!account && (
          <section className="empty-state">
            <h3>Authentication required</h3>
            <p>
              Use the Microsoft sign-in button above. Your access token stays in
              the browser session and is sent only to the protected API.
            </p>
          </section>
        )}

        {account && !prediction && !busy && (
          <section className="empty-state">
            <h3>Ready to analyse</h3>
            <p>Select an LSE ticker above to run the current research model.</p>
          </section>
        )}

        {prediction && (
          <>
            <section className="summary-grid">
              <article className="card primary-card">
                <div className="card-label">Signal</div>
                <SignalBadge signal={prediction.signal} />
                <div className="symbol">{prediction.symbol}</div>
                <div className="as-of">As of {prediction.as_of}</div>
              </article>

              <article className="card">
                <div className="card-label">Probability up</div>
                <div className="big-number">{pct(prediction.probability_up)}</div>
                <div className="progress">
                  <span style={{ width: pct(prediction.probability_up) }} />
                </div>
              </article>

              <article className="card">
                <div className="card-label">Probability down</div>
                <div className="big-number">{pct(prediction.probability_down)}</div>
                <div className="progress down">
                  <span style={{ width: pct(prediction.probability_down) }} />
                </div>
              </article>

              <article className="card">
                <div className="card-label">Latest quote</div>
                <div className="big-number">
                  {typeof prediction.close_price === "number"
                    ? prediction.close_price.toFixed(2)
                    : "—"}
                </div>
                <div className="muted">Source quotation units</div>
              </article>
            </section>

            <section className="metrics">
              <article className="metric-card">
                <span>Walk-forward accuracy</span>
                <strong>{pct(prediction.walk_forward_accuracy)}</strong>
              </article>
              <article className="metric-card">
                <span>Brier score</span>
                <strong>{metric(prediction.walk_forward_brier)}</strong>
              </article>
              <article className="metric-card">
                <span>Walk-forward folds</span>
                <strong>{prediction.walk_forward_folds ?? "—"}</strong>
              </article>
              <article className="metric-card">
                <span>Features</span>
                <strong>{prediction.feature_count ?? "—"}</strong>
              </article>
              <article className="metric-card">
                <span>Labelled rows</span>
                <strong>{prediction.labelled_rows ?? "—"}</strong>
              </article>
            </section>
          </>
        )}
      </main>

      <footer>
        UK Market AI Trader • Azure Container Apps + Azure static hosting •
        Entra ID authentication
      </footer>
    </div>
  );
}
