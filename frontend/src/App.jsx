import React, { useEffect, useMemo, useState } from "react";
import { getHealth, getPrediction, searchSymbols } from "./api";
import { initialiseAuth, msal, signIn, signOut } from "./auth";
import { config } from "./config";

const quickSymbols = {
  uk: ["BARC.L", "LLOY.L", "SHEL.L", "AZN.L", "BP.L", "GSK.L"],
  us: ["AAPL", "MSFT", "NVDA", "AMZN", "GOOGL", "META"],
  india: ["RELIANCE.NS", "TCS.NS", "INFY.NS", "HDFCBANK.NS", "ICICIBANK.NS", "SBIN.NS"],
  uae: ["EMAAR.DU", "DEWA.DU", "FAB.AE", "ADCB.AE", "ALDAR.AE", "IHC.AE"],
};

const marketConfig = {
  uk: {
    label: "UK / LSE",
    searchLabel: "Find a London-listed company",
    placeholder: "Search by company name or ticker, e.g. Barclays",
    directLabel: "Direct LSE ticker",
    tickerPlaceholder: "BARC.L",
    description:
      "Five-model ensemble using LSE price/volume, FTSE 100 context and GBP/USD.",
  },
  us: {
    label: "US / NYSE & NASDAQ",
    searchLabel: "Find a US-listed company",
    placeholder: "Search by company name or ticker, e.g. Apple",
    directLabel: "Direct US ticker",
    tickerPlaceholder: "AAPL",
    description:
      "US market support is being added with S&P 500, NASDAQ and volatility context.",
  },
  india: {
    label: "India / NSE & BSE",
    searchLabel: "Find an India-listed company",
    placeholder: "Search by company name or ticker, e.g. Reliance",
    directLabel: "Direct NSE/BSE ticker",
    tickerPlaceholder: "RELIANCE.NS",
    description:
      "India market support is planned with NIFTY 50, Sensex and INR market context.",
  },
  uae: {
    label: "UAE / DFM & ADX",
    searchLabel: "Find a UAE-listed company",
    placeholder: "Search by company name or ticker, e.g. Emaar",
    directLabel: "Direct DFM/ADX ticker",
    tickerPlaceholder: "EMAAR.DU",
    description:
      "UAE market support is planned with DFM, ADX and AED market context.",
  },
};

const modelLabels = {
  logistic_regression: "Logistic Regression",
  random_forest: "Random Forest",
  xgboost: "XGBoost",
  lightgbm: "LightGBM",
  catboost: "CatBoost",
};

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
  const [market, setMarket] = useState("uk");
  const [symbol, setSymbol] = useState("BARC.L");
  const [companyQuery, setCompanyQuery] = useState("");
  const [symbolMatches, setSymbolMatches] = useState([]);
  const [selectedCompany, setSelectedCompany] = useState(null);
  const [searchingSymbols, setSearchingSymbols] = useState(false);
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

  useEffect(() => {
    if (!account) {
      setSymbolMatches([]);
      return undefined;
    }

    if (market !== "uk") {
      setSymbolMatches([]);
      return undefined;
    }

    const query = companyQuery.trim();
    if (query.length < 2) {
      setSymbolMatches([]);
      return undefined;
    }

    const timer = window.setTimeout(async () => {
      setSearchingSymbols(true);
      try {
        const results = await searchSymbols(query);
        setSymbolMatches(results);
      } catch (error) {
        setMessage(error.message);
        setSymbolMatches([]);
      } finally {
        setSearchingSymbols(false);
      }
    }, 350);

    return () => window.clearTimeout(timer);
  }, [companyQuery, account, market]);

  function chooseCompany(match) {
    setSelectedCompany(match);
    setSymbol(match.symbol);
    setCompanyQuery(match.name);
    setSymbolMatches([]);
    setMessage("");
  }

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

  function changeMarket(nextMarket) {
    const defaults = {
      uk: "BARC.L",
      us: "AAPL",
      india: "RELIANCE.NS",
      uae: "EMAAR.DU",
    };

    setMarket(nextMarket);
    setPrediction(null);
    setMessage("");
    setCompanyQuery("");
    setSelectedCompany(null);
    setSymbolMatches([]);
    setSymbol(defaults[nextMarket] || "");
  }

  const currentMarket = marketConfig[market];
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

        <section className="market-selector-panel">
          <div>
            <div className="eyebrow">MARKET</div>
            <h3>Select market</h3>
          </div>
          <div className="market-dropdown-wrap">
            <label htmlFor="market-select">Market</label>
            <select
              id="market-select"
              className="market-select"
              value={market}
              onChange={(event) => changeMarket(event.target.value)}
            >
              {Object.entries(marketConfig).map(([key, item]) => (
                <option key={key} value={key}>
                  {item.label}
                </option>
              ))}
            </select>
          </div>
        </section>

        <section className="hero">
          <div>
            <div className="eyebrow">NEXT TRADING DAY RESEARCH</div>
            <h2>Equity direction signals with market context</h2>
            <p>
              Five-model ensemble using Logistic Regression, Random Forest, XGBoost,
              LightGBM and CatBoost. {currentMarket.description}
            </p>
          </div>
          <div className="research-note">
            Research and paper trading only. Predictions are probabilistic and are
            not financial advice.
          </div>
        </section>

        {market !== "uk" && (
          <div className="alert">
            <strong>{currentMarket.label} selected.</strong> The market is available in the
            selector and watchlist, but company lookup and prediction are not enabled for this
            market in the backend yet.
          </div>
        )}

        <section className="search-panel">
          <form
            onSubmit={(event) => {
              event.preventDefault();
              runPrediction();
            }}
          >
            <label htmlFor="company-search">{currentMarket.searchLabel}</label>
            <div className="company-search-wrap">
              <input
                id="company-search"
                value={companyQuery}
                onChange={(event) => {
                  setCompanyQuery(event.target.value);
                  setSelectedCompany(null);
                }}
                placeholder={currentMarket.placeholder}
                disabled={market !== "uk"}
                autoComplete="off"
              />

              {(searchingSymbols || symbolMatches.length > 0) && (
                <div className="symbol-results">
                  {searchingSymbols && (
                    <div className="symbol-result muted-result">Searching LSE companies…</div>
                  )}
                  {!searchingSymbols && symbolMatches.map((match) => (
                    <button
                      type="button"
                      className="symbol-result"
                      key={match.symbol}
                      onClick={() => chooseCompany(match)}
                    >
                      <span>
                        <strong>{match.name}</strong>
                        <small>{match.exchange}</small>
                      </span>
                      <b>{match.symbol}</b>
                    </button>
                  ))}
                </div>
              )}
            </div>

            <div className="selected-company-row">
              <div>
                <span className="selected-label">Selected</span>
                <strong>{selectedCompany?.name || currentMarket.directLabel}</strong>
                <span className="selected-symbol">{symbol}</span>
              </div>
              <input
                aria-label="Market ticker"
                value={symbol}
                onChange={(event) => {
                  setSymbol(event.target.value.toUpperCase());
                  setSelectedCompany(null);
                }}
                placeholder={currentMarket.tickerPlaceholder}
              />
              <button className="primary" disabled={!account || busy || !symbol.trim() || market !== "uk"}>
                {busy ? "Analysing…" : "Run prediction"}
              </button>
            </div>
          </form>

          <div className="quick-symbols">
            {quickSymbols[market].map((item) => (
              <button
                key={item}
                className="ticker"
                onClick={() => {
                  setSymbol(item);
                  setSelectedCompany(null);
                  setCompanyQuery("");
                  runPrediction(item);
                }}
                disabled={!account || busy || market !== "uk"}
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
            <p>{market === "uk" ? "Select a UK company above to run the current research model." : `${currentMarket.label} prediction support will be enabled in a later backend update.`}</p>
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

            <section className="ensemble-panel">
              <div className="ensemble-heading">
                <div>
                  <div className="eyebrow">ENSEMBLE BREAKDOWN</div>
                  <h3>Individual model probabilities</h3>
                </div>
                <div className="ensemble-meta">
                  <span>{prediction.ensemble_method || "equal_weight"}</span>
                  <span>{prediction.model_source || "trained"}</span>
                </div>
              </div>

              <div className="model-grid">
                {Object.entries(prediction.model_probabilities || {}).map(([name, value]) => {
                  const metrics = prediction.model_metrics?.[name];
                  return (
                    <article className="model-card" key={name}>
                      <div className="model-name">{modelLabels[name] || name}</div>
                      <div className="model-probability">{pct(value)}</div>
                      <div className="progress">
                        <span style={{ width: pct(value) }} />
                      </div>
                      <div className="model-stats">
                        <span>Weight {pct(prediction.model_weights?.[name])}</span>
                        <span>WF acc {pct(metrics?.accuracy)}</span>
                        <span>Brier {metric(metrics?.brier)}</span>
                      </div>
                    </article>
                  );
                })}
              </div>
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
