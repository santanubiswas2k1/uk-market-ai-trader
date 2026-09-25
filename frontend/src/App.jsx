import React, { useEffect, useMemo, useState } from "react";
import {
  getHealth,
  getLiveQuote,
  getPerformance,
  getPrediction,
  searchSymbols,
} from "./api";
import { initialiseAuth, msal, signIn, signOut } from "./auth";
import { config } from "./config";

const quickSymbols = {
  uk: ["BARC.L", "LLOY.L", "SHEL.L", "AZN.L", "BP.L", "GSK.L"],
  us: ["AAPL", "MSFT", "NVDA", "AMZN", "GOOGL", "META"],
  india: ["RELIANCE.NS", "TCS.NS", "INFY.NS", "HDFCBANK.NS", "ICICIBANK.NS", "SBIN.NS"],
  uae: ["EMAAR.DU", "DEWA.DU", "FAB.AE", "ADCB.AE", "ALDAR.AE", "IHC.AE"],
  canada: ["RY.TO", "TD.TO", "SHOP.TO", "ENB.TO", "BNS.TO", "CNR.TO"],
  europe: ["SAP.DE", "ASML.AS", "MC.PA", "SIE.DE", "OR.PA", "AIR.PA"],
  hong_kong: ["0700.HK", "9988.HK", "0005.HK", "1299.HK", "3690.HK", "2318.HK"],
  japan: ["7203.T", "6758.T", "9984.T", "8306.T", "6501.T", "7974.T"],
  australia: ["BHP.AX", "CBA.AX", "CSL.AX", "NAB.AX", "WBC.AX", "ANZ.AX"],
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
      "Five-model ensemble using US equity prices, broad US index context and USD market context.",
  },
  india: {
    label: "India / NSE & BSE",
    searchLabel: "Find an India-listed company",
    placeholder: "Search by company name or ticker, e.g. Reliance",
    directLabel: "Direct NSE/BSE ticker",
    tickerPlaceholder: "RELIANCE.NS",
    description:
      "Five-model ensemble using Indian equity prices, NIFTY/Sensex context and INR FX context.",
  },
  uae: {
    label: "UAE / DFM & ADX",
    searchLabel: "Find a UAE-listed company",
    placeholder: "Search by company name or ticker, e.g. Emaar",
    directLabel: "Direct DFM/ADX ticker",
    tickerPlaceholder: "EMAAR.DU",
    description:
      "Five-model ensemble using UAE equity prices, local index context and AED FX context.",
  },
  canada: {
    label: "Canada / TSX",
    searchLabel: "Find a Canada-listed company",
    placeholder: "Search by company name or ticker, e.g. Royal Bank",
    directLabel: "Direct TSX ticker",
    tickerPlaceholder: "RY.TO",
    description:
      "Five-model ensemble using Canadian equity prices, TSX context and CAD FX context.",
  },
  europe: {
    label: "Europe / Major Exchanges",
    searchLabel: "Find a Europe-listed company",
    placeholder: "Search by company name or ticker, e.g. SAP",
    directLabel: "Direct European ticker",
    tickerPlaceholder: "SAP.DE",
    description:
      "Five-model ensemble using European equity prices, STOXX context and EUR FX context.",
  },
  hong_kong: {
    label: "Hong Kong / HKEX",
    searchLabel: "Find a Hong Kong-listed company",
    placeholder: "Search by company name or ticker, e.g. Tencent",
    directLabel: "Direct HKEX ticker",
    tickerPlaceholder: "0700.HK",
    description:
      "Five-model ensemble using HKEX equity prices, Hang Seng context and HKD FX context.",
  },
  japan: {
    label: "Japan / TSE",
    searchLabel: "Find a Japan-listed company",
    placeholder: "Search by company name or ticker, e.g. Toyota",
    directLabel: "Direct TSE ticker",
    tickerPlaceholder: "7203.T",
    description:
      "Five-model ensemble using Japanese equity prices, Nikkei context and JPY FX context.",
  },
  australia: {
    label: "Australia / ASX",
    searchLabel: "Find an Australia-listed company",
    placeholder: "Search by company name or ticker, e.g. BHP",
    directLabel: "Direct ASX ticker",
    tickerPlaceholder: "BHP.AX",
    description:
      "Five-model ensemble using Australian equity prices, ASX 200 context and AUD FX context.",
  },
};

const modelLabels = {
  logistic_regression: "Logistic Regression",
  random_forest: "Random Forest",
  xgboost: "XGBoost",
  lightgbm: "LightGBM",
  catboost: "CatBoost",
};

const returnModelLabels = {
  ridge: "Ridge",
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
  const [performance, setPerformance] = useState(null);
  const [performanceLoading, setPerformanceLoading] = useState(false);
  const [liveQuote, setLiveQuote] = useState(null);
  const [liveEnabled, setLiveEnabled] = useState(true);
  const [liveLoading, setLiveLoading] = useState(false);
  const [liveError, setLiveError] = useState("");
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
      setPerformance(null);
      return undefined;
    }

    let cancelled = false;
    setPerformanceLoading(true);

    getPerformance(market)
      .then((result) => {
        if (!cancelled) {
          setPerformance(result);
        }
      })
      .catch(() => {
        if (!cancelled) {
          setPerformance(null);
        }
      })
      .finally(() => {
        if (!cancelled) {
          setPerformanceLoading(false);
        }
      });

    return () => {
      cancelled = true;
    };
  }, [account, market]);

  useEffect(() => {
    if (!account || !liveEnabled || !symbol.trim()) {
      if (!liveEnabled) {
        setLiveQuote(null);
      }
      return undefined;
    }

    let cancelled = false;

    async function refreshLiveQuote() {
      setLiveLoading(true);
      try {
        const result = await getLiveQuote(symbol.trim().toUpperCase(), market);
        if (!cancelled) {
          setLiveQuote(result);
          setLiveError("");
        }
      } catch (error) {
        if (!cancelled) {
          setLiveError(error.message);
        }
      } finally {
        if (!cancelled) {
          setLiveLoading(false);
        }
      }
    }

    refreshLiveQuote();
    const timer = window.setInterval(
      refreshLiveQuote,
      config.marketFeedRefreshMs,
    );

    return () => {
      cancelled = true;
      window.clearInterval(timer);
    };
  }, [account, liveEnabled, market, symbol]);

  useEffect(() => {
    if (!account) {
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
        const results = await searchSymbols(query, market);
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
      const result = await getPrediction(normalized, market);
      setPrediction(result);

      try {
        const latestPerformance = await getPerformance(market);
        setPerformance(latestPerformance);
      } catch {
        // A prediction should still be shown if performance refresh is unavailable.
      }
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
      canada: "RY.TO",
      europe: "SAP.DE",
      hong_kong: "0700.HK",
      japan: "7203.T",
      australia: "BHP.AX",
    };

    setMarket(nextMarket);
    setPrediction(null);
    setPerformance(null);
    setLiveQuote(null);
    setLiveError("");
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
          <h1>Global Market AI Trader</h1>
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
              <span>Market feed: {config.marketFeedBaseUrl ? "loaded" : "missing"}</span>
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

        <section className="live-market-panel">
          <div className="live-market-heading">
            <div>
              <div className="eyebrow">MARKET DATA FEED</div>
              <h3>{symbol || "Select a symbol"}</h3>
            </div>
            <div className="live-controls">
              <span className={`feed-badge ${liveEnabled ? "feed-on" : "feed-off"}`}>
                {liveEnabled
                  ? `Auto refresh ${Math.round(config.marketFeedRefreshMs / 1000)}s`
                  : "Feed paused"}
              </span>
              <button
                type="button"
                className="ghost"
                onClick={() => setLiveEnabled((value) => !value)}
                disabled={!account}
              >
                {liveEnabled ? "Pause live feed" : "Resume live feed"}
              </button>
            </div>
          </div>

          {!account && (
            <div className="live-placeholder">Sign in to load the market feed.</div>
          )}

          {account && liveEnabled && liveLoading && !liveQuote && (
            <div className="live-placeholder">Loading latest market quote…</div>
          )}

          {account && liveError && (
            <div className="alert error">{liveError}</div>
          )}

          {account && liveQuote && (
            <>
              <div className="live-quote-grid">
                <article className="live-price-card">
                  <span className="live-label">Current quote</span>
                  <strong>{Number(liveQuote.price).toFixed(2)}</strong>
                  <span
                    className={`live-change ${
                      liveQuote.change_percent >= 0 ? "positive" : "negative"
                    }`}
                  >
                    {liveQuote.change >= 0 ? "+" : ""}
                    {Number(liveQuote.change).toFixed(2)}
                    {" · "}
                    {liveQuote.change_percent >= 0 ? "+" : ""}
                    {pct(liveQuote.change_percent)}
                  </span>
                </article>

                <article className="live-stat">
                  <span>Previous close</span>
                  <strong>{Number(liveQuote.previous_close).toFixed(2)}</strong>
                </article>
                <article className="live-stat">
                  <span>Day high</span>
                  <strong>
                    {typeof liveQuote.day_high === "number"
                      ? liveQuote.day_high.toFixed(2)
                      : "—"}
                  </strong>
                </article>
                <article className="live-stat">
                  <span>Day low</span>
                  <strong>
                    {typeof liveQuote.day_low === "number"
                      ? liveQuote.day_low.toFixed(2)
                      : "—"}
                  </strong>
                </article>
                <article className="live-stat">
                  <span>Volume</span>
                  <strong>
                    {typeof liveQuote.volume === "number"
                      ? liveQuote.volume.toLocaleString()
                      : "—"}
                  </strong>
                </article>
              </div>

              <div className="live-feed-meta">
                <span>{liveQuote.exchange || currentMarket.label}</span>
                <span>{liveQuote.currency || "Source quote units"}</span>
                <span>
                  Updated{" "}
                  {liveQuote.last_update
                    ? new Date(liveQuote.last_update).toLocaleTimeString()
                    : "—"}
                </span>
                <span>
                  {liveQuote.feed_source || "Market data provider"}
                  {" · "}
                  Real-time/delayed according to provider entitlement
                </span>
              </div>
            </>
          )}
        </section>

        <section className="performance-panel">
          <div className="ensemble-heading">
            <div>
              <div className="eyebrow">FORWARD PERFORMANCE</div>
              <h3>Stored live prediction accuracy</h3>
            </div>
            <div className="ensemble-meta">
              <span>{currentMarket.label}</span>
              <span>First forecast per ticker/day</span>
            </div>
          </div>

          {!account && (
            <div className="live-placeholder">
              Sign in to view forward prediction performance.
            </div>
          )}

          {account && performanceLoading && !performance && (
            <div className="live-placeholder">
              Checking completed forecasts…
            </div>
          )}

          {account && performance && (
            <>
              <div className="performance-grid">
                <article className="metric-card">
                  <span>Recorded</span>
                  <strong>{performance.total_predictions ?? 0}</strong>
                </article>
                <article className="metric-card">
                  <span>Evaluated</span>
                  <strong>{performance.evaluated_predictions ?? 0}</strong>
                </article>
                <article className="metric-card">
                  <span>Pending</span>
                  <strong>{performance.pending_predictions ?? 0}</strong>
                </article>
                <article className="metric-card">
                  <span>Direction accuracy</span>
                  <strong>{pct(performance.direction_accuracy)}</strong>
                </article>
                <article className="metric-card">
                  <span>Signal accuracy</span>
                  <strong>{pct(performance.signal_accuracy)}</strong>
                </article>
                <article className="metric-card">
                  <span>Brier score</span>
                  <strong>{metric(performance.brier_score)}</strong>
                </article>
                <article className="metric-card">
                  <span>Expected-close MAE</span>
                  <strong>{metric(performance.expected_close_mae, 2)}</strong>
                </article>
                <article className="metric-card">
                  <span>Close MAPE</span>
                  <strong>{pct(performance.expected_close_mape)}</strong>
                </article>
                <article className="metric-card">
                  <span>Return MAE</span>
                  <strong>{pct(performance.return_mae)}</strong>
                </article>
                <article className="metric-card">
                  <span>Range hit rate</span>
                  <strong>{pct(performance.range_hit_rate)}</strong>
                </article>
              </div>

              {performance.evaluated_predictions === 0 && (
                <p className="context-note">
                  Predictions are being recorded. Accuracy will appear after a later
                  completed trading-day close is available for comparison.
                </p>
              )}

              {(performance.recent || []).length > 0 && (
                <div className="performance-table-wrap">
                  <table className="performance-table">
                    <thead>
                      <tr>
                        <th>Symbol</th>
                        <th>Forecast date</th>
                        <th>UP probability</th>
                        <th>Expected close</th>
                        <th>Actual close</th>
                        <th>Direction</th>
                        <th>Range</th>
                      </tr>
                    </thead>
                    <tbody>
                      {(performance.recent || []).map((item) => (
                        <tr key={item.prediction_id}>
                          <td>{item.symbol}</td>
                          <td>{String(item.as_of || "").slice(0, 10)}</td>
                          <td>{pct(item.probability_up)}</td>
                          <td>{metric(item.expected_close, 2)}</td>
                          <td>{metric(item.actual_next_close, 2)}</td>
                          <td>
                            <span
                              className={
                                item.direction_correct
                                  ? "result-good"
                                  : "result-bad"
                              }
                            >
                              {item.direction_correct ? "Correct" : "Miss"}
                            </span>
                          </td>
                          <td>
                            <span
                              className={
                                item.range_hit ? "result-good" : "result-bad"
                              }
                            >
                              {item.range_hit ? "Hit" : "Miss"}
                            </span>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </>
          )}
        </section>

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
                autoComplete="off"
              />

              {(searchingSymbols || symbolMatches.length > 0) && (
                <div className="symbol-results">
                  {searchingSymbols && (
                    <div className="symbol-result muted-result">Searching {currentMarket.label} companies…</div>
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
              <button className="primary" disabled={!account || busy || !symbol.trim()}>
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
            <p>Select a company above to run the current {currentMarket.label} research model.</p>
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
                <div className="muted">
                  Base ML {pct(prediction.base_probability_up)}
                </div>
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
                <div className="muted">{prediction.quote_unit || "Source quotation units"}</div>
              </article>

              <article className="card">
                <div className="card-label">Expected next-day return</div>
                <div className="big-number">{pct(prediction.expected_return_1d)}</div>
                <div className="muted">
                  Base ML {pct(prediction.base_expected_return_1d)}
                </div>
              </article>

              <article className="card">
                <div className="card-label">Expected next close</div>
                <div className="big-number">
                  {typeof prediction.expected_close === "number"
                    ? prediction.expected_close.toFixed(2)
                    : "—"}
                </div>
                <div className="muted">{prediction.quote_unit || "Source quotation units"}</div>
              </article>

              <article className="card">
                <div className="card-label">Expected price range</div>
                <div className="range-number">
                  {typeof prediction.expected_range_low === "number"
                    ? prediction.expected_range_low.toFixed(2)
                    : "—"}
                  {" – "}
                  {typeof prediction.expected_range_high === "number"
                    ? prediction.expected_range_high.toFixed(2)
                    : "—"}
                </div>
                <div className="muted">
                  {pct(prediction.expected_range_confidence)} volatility-based interval
                </div>
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

            <section className="ensemble-panel">
              <div className="ensemble-heading">
                <div>
                  <div className="eyebrow">RETURN FORECAST</div>
                  <h3>Individual model next-day return estimates</h3>
                </div>
                <div className="ensemble-meta">
                  <span>Equal weight</span>
                  <span>Next trading day</span>
                </div>
              </div>

              <div className="model-grid">
                {Object.entries(prediction.return_model_predictions || {}).map(([name, value]) => (
                  <article className="model-card" key={name}>
                    <div className="model-name">{returnModelLabels[name] || name}</div>
                    <div className="model-probability">{pct(value)}</div>
                  </article>
                ))}
              </div>
            </section>

            <section className="decision-context-panel">
              <div className="ensemble-heading">
                <div>
                  <div className="eyebrow">DECISION CONTEXT</div>
                  <h3>News, earnings and sector context</h3>
                </div>
                <div className="ensemble-meta">
                  <span>Live sentiment fusion</span>
                  <span>
                    Weight {pct(prediction.news_sentiment_weight)}
                  </span>
                </div>
              </div>

              <div className="context-grid">
                <article className="metric-card">
                  <span>Sector</span>
                  <strong>{prediction.decision_context?.sector || "—"}</strong>
                </article>
                <article className="metric-card">
                  <span>Sector proxy</span>
                  <strong>{prediction.decision_context?.sector_proxy || "—"}</strong>
                </article>
                <article className="metric-card">
                  <span>News last 24h</span>
                  <strong>{prediction.decision_context?.news_count_24h ?? "—"}</strong>
                </article>
                <article className="metric-card">
                  <span>News sentiment</span>
                  <strong>{metric(prediction.decision_context?.news_sentiment, 2)}</strong>
                </article>
                <article className="metric-card">
                  <span>News-implied up probability</span>
                  <strong>{pct(prediction.news_probability_up)}</strong>
                </article>
                <article className="metric-card">
                  <span>Days to earnings</span>
                  <strong>{prediction.decision_context?.days_to_earnings ?? "—"}</strong>
                </article>
              </div>

              {(prediction.decision_context?.recent_headlines || []).length > 0 && (
                <div className="headline-list">
                  {(prediction.decision_context?.recent_headlines || []).map((headline) => (
                    <div className="headline-item" key={headline}>{headline}</div>
                  ))}
                </div>
              )}

              <p className="context-note">
                Current company-news sentiment now adjusts the live probability and
                expected return with a bounded weight. Earnings proximity widens the
                expected price range. The historical walk-forward metrics still cover
                the price/context ML models only until a point-in-time historical news
                archive is connected.
              </p>
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
        Global Market AI Trader • Azure Container Apps + Azure static hosting •
        Entra ID authentication
      </footer>
    </div>
  );
}
