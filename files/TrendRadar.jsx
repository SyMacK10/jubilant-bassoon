import { useState } from "react";

const MOCK_DATA = {
  signals: [
    {
      tech: "Java 8",
      score: 87,
      triggers: ["eol_proximity", "demand_spike"],
      eol_days: 62,
      so_delta: 41,
      cve_count: 2,
      gh_mentions: 34,
      severity: "critical",
    },
    {
      tech: "CentOS 7",
      score: 79,
      triggers: ["eol_proximity", "migration_signal"],
      eol_days: 88,
      so_delta: 28,
      cve_count: 1,
      gh_mentions: 61,
      severity: "critical",
    },
    {
      tech: "Spring Framework 5",
      score: 65,
      triggers: ["demand_spike", "migration_signal"],
      eol_days: 142,
      so_delta: 55,
      cve_count: 0,
      gh_mentions: 22,
      severity: "high",
    },
    {
      tech: "Python 3.8",
      score: 58,
      triggers: ["eol_proximity"],
      eol_days: 201,
      so_delta: 12,
      cve_count: 3,
      gh_mentions: 9,
      severity: "high",
    },
    {
      tech: "Elasticsearch 7",
      score: 44,
      triggers: ["demand_spike"],
      eol_days: 310,
      so_delta: 33,
      cve_count: 0,
      gh_mentions: 18,
      severity: "medium",
    },
    {
      tech: "PostgreSQL 12",
      score: 39,
      triggers: ["eol_proximity"],
      eol_days: 280,
      so_delta: 8,
      cve_count: 1,
      gh_mentions: 6,
      severity: "medium",
    },
    {
      tech: "Kafka 2.x",
      score: 31,
      triggers: ["migration_signal"],
      eol_days: 410,
      so_delta: 6,
      cve_count: 0,
      gh_mentions: 29,
      severity: "low",
    },
    {
      tech: "Node.js 18",
      score: 22,
      triggers: ["demand_spike"],
      eol_days: 480,
      so_delta: 19,
      cve_count: 0,
      gh_mentions: 7,
      severity: "low",
    },
  ],
  digest: `Java 8 is the clearest priority this week. With EOL 62 days out and Stack Overflow volume up 41% week-over-week, enterprise teams are actively searching for answers. The buyer profile here is an IT leader who knows migration is overdue but hasn't been forced to act yet. The forcing function is arriving. Outreach framing: extended support as bridge coverage, not a permanent solution.

CentOS 7 follows closely. GitHub migration discussions spiked, which indicates active internal projects — not just awareness, but actual teams in motion. This is a warm audience. The angle is replacement path clarity: what does a supported, production-stable alternative look like without a full infrastructure rewrite?

Spring Framework 5 shows the fastest-growing question volume this week at +55%, driven by the Spring 6 migration complexity. Enterprises running legacy Spring stacks are hitting compatibility walls. Content opportunity: a straight-line migration guide that doesn't require a full Java version upgrade.

Watch Python 3.8 — three CVEs this week is unusual. It's not a volume signal yet, but CVE accumulation on EOL-adjacent versions historically precedes rapid demand spikes. Worth queuing content now before the wave.`,
  sources: [
    { name: "Stack Overflow", count: 142, status: "live" },
    { name: "GitHub Issues", count: 89, status: "live" },
    { name: "endoflife.date", count: 31, status: "live" },
    { name: "NVD / CVE", count: 7, status: "live" },
    { name: "Reddit", count: 0, status: "pending" },
  ],
  last_run: "Mon Apr 7 2025 — 07:04 AM",
};

const TRIGGER_LABELS = {
  eol_proximity: { label: "EOL", color: "#ff4444" },
  demand_spike: { label: "SPIKE", color: "#f5a623" },
  migration_signal: { label: "MIGR", color: "#4a9eff" },
  cve: { label: "CVE", color: "#c471ed" },
};

const SEVERITY_COLORS = {
  critical: "#ff4444",
  high: "#f5a623",
  medium: "#4a9eff",
  low: "#6b7a8d",
};

const scoreBarWidth = (score) => `${Math.min(score, 100)}%`;

export default function TrendRadar() {
  const [selected, setSelected] = useState(null);
  const [activeTab, setActiveTab] = useState("signals");

  const selectedSignal = selected !== null ? MOCK_DATA.signals[selected] : null;

  return (
    <div style={{
      fontFamily: "'IBM Plex Mono', 'Courier New', monospace",
      background: "#0a0c0f",
      color: "#c8d0dc",
      minHeight: "100vh",
      padding: "0",
      fontSize: "13px",
    }}>
      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500;600&family=IBM+Plex+Sans:wght@400;500;600;700&display=swap');
        * { box-sizing: border-box; margin: 0; padding: 0; }
        ::-webkit-scrollbar { width: 4px; }
        ::-webkit-scrollbar-track { background: #0d1117; }
        ::-webkit-scrollbar-thumb { background: #2a3040; border-radius: 2px; }
        .signal-row:hover { background: rgba(74,158,255,0.06) !important; cursor: pointer; }
        .tab-btn { border: none; cursor: pointer; transition: all 0.15s ease; }
        .tab-btn:hover { color: #4a9eff !important; }
        .source-pill { transition: all 0.2s ease; }
        @keyframes pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.4; } }
        .live-dot { animation: pulse 2s ease-in-out infinite; }
        @keyframes fadeIn { from { opacity: 0; transform: translateY(4px); } to { opacity: 1; transform: translateY(0); } }
        .fade-in { animation: fadeIn 0.25s ease forwards; }
        .score-bar { transition: width 0.6s cubic-bezier(0.4,0,0.2,1); }
      `}</style>

      {/* Header */}
      <div style={{
        background: "#0d1117",
        borderBottom: "1px solid #1c2230",
        padding: "16px 28px",
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between",
      }}>
        <div style={{ display: "flex", alignItems: "baseline", gap: "12px" }}>
          <span style={{
            fontFamily: "'IBM Plex Sans', sans-serif",
            fontSize: "15px",
            fontWeight: 700,
            color: "#e8edf4",
            letterSpacing: "0.02em",
          }}>TREND RADAR</span>
          <span style={{ color: "#3a4556", fontSize: "11px" }}>// OpenLogic Market Intelligence</span>
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: "20px" }}>
          <span style={{ color: "#3a4556", fontSize: "11px" }}>Last run: {MOCK_DATA.last_run}</span>
          <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
            <div className="live-dot" style={{
              width: "6px", height: "6px", borderRadius: "50%", background: "#2ecc71"
            }} />
            <span style={{ color: "#2ecc71", fontSize: "11px", letterSpacing: "0.06em" }}>LIVE</span>
          </div>
        </div>
      </div>

      {/* Source Status Bar */}
      <div style={{
        background: "#0d1117",
        borderBottom: "1px solid #1c2230",
        padding: "10px 28px",
        display: "flex",
        gap: "8px",
        alignItems: "center",
      }}>
        <span style={{ color: "#3a4556", fontSize: "11px", marginRight: "4px" }}>SOURCES</span>
        {MOCK_DATA.sources.map(src => (
          <div key={src.name} className="source-pill" style={{
            display: "flex",
            alignItems: "center",
            gap: "5px",
            padding: "3px 10px",
            borderRadius: "2px",
            background: src.status === "live" ? "rgba(46,204,113,0.08)" : "rgba(255,255,255,0.03)",
            border: `1px solid ${src.status === "live" ? "rgba(46,204,113,0.2)" : "#1c2230"}`,
            fontSize: "11px",
            color: src.status === "live" ? "#a8e6c3" : "#3a4556",
          }}>
            <div style={{
              width: "5px", height: "5px", borderRadius: "50%",
              background: src.status === "live" ? "#2ecc71" : "#3a4556"
            }} />
            {src.name}
            {src.count > 0 && (
              <span style={{ color: "#4a9eff", marginLeft: "2px" }}>{src.count}</span>
            )}
          </div>
        ))}
      </div>

      {/* Main Grid */}
      <div style={{
        display: "grid",
        gridTemplateColumns: "1fr 360px",
        gridTemplateRows: "auto 1fr",
        gap: "0",
        height: "calc(100vh - 95px)",
      }}>

        {/* Left Panel */}
        <div style={{ borderRight: "1px solid #1c2230", display: "flex", flexDirection: "column" }}>

          {/* Tabs */}
          <div style={{
            display: "flex",
            borderBottom: "1px solid #1c2230",
            padding: "0 28px",
          }}>
            {["signals", "digest"].map(tab => (
              <button
                key={tab}
                className="tab-btn"
                onClick={() => setActiveTab(tab)}
                style={{
                  background: "none",
                  padding: "12px 0",
                  marginRight: "24px",
                  fontSize: "11px",
                  letterSpacing: "0.08em",
                  fontFamily: "'IBM Plex Mono', monospace",
                  fontWeight: 500,
                  color: activeTab === tab ? "#4a9eff" : "#4a5568",
                  borderBottom: `2px solid ${activeTab === tab ? "#4a9eff" : "transparent"}`,
                  textTransform: "uppercase",
                }}
              >
                {tab}
              </button>
            ))}
          </div>

          {/* Signals Table */}
          {activeTab === "signals" && (
            <div style={{ overflowY: "auto", flex: 1 }}>
              {/* Column Headers */}
              <div style={{
                display: "grid",
                gridTemplateColumns: "200px 80px 1fr 100px 80px 80px",
                padding: "10px 28px",
                borderBottom: "1px solid #1c2230",
                color: "#3a4556",
                fontSize: "10px",
                letterSpacing: "0.1em",
                textTransform: "uppercase",
              }}>
                <span>Technology</span>
                <span>Score</span>
                <span>Signal Bar</span>
                <span>Triggers</span>
                <span style={{ textAlign: "right" }}>EOL Days</span>
                <span style={{ textAlign: "right" }}>CVEs</span>
              </div>

              {MOCK_DATA.signals.map((sig, i) => (
                <div
                  key={sig.tech}
                  className="signal-row"
                  onClick={() => setSelected(selected === i ? null : i)}
                  style={{
                    display: "grid",
                    gridTemplateColumns: "200px 80px 1fr 100px 80px 80px",
                    padding: "13px 28px",
                    borderBottom: "1px solid #111720",
                    background: selected === i ? "rgba(74,158,255,0.08)" : "transparent",
                    alignItems: "center",
                    transition: "background 0.1s ease",
                  }}
                >
                  {/* Tech Name */}
                  <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
                    <div style={{
                      width: "3px", height: "28px", borderRadius: "2px",
                      background: SEVERITY_COLORS[sig.severity],
                      flexShrink: 0,
                    }} />
                    <span style={{
                      color: selected === i ? "#e8edf4" : "#b0bac9",
                      fontFamily: "'IBM Plex Sans', sans-serif",
                      fontWeight: selected === i ? 600 : 400,
                      fontSize: "13px",
                    }}>{sig.tech}</span>
                  </div>

                  {/* Score */}
                  <div style={{
                    fontWeight: 600,
                    fontSize: "15px",
                    color: SEVERITY_COLORS[sig.severity],
                    fontFamily: "'IBM Plex Sans', sans-serif",
                  }}>
                    {sig.score}
                  </div>

                  {/* Score Bar */}
                  <div style={{ paddingRight: "20px" }}>
                    <div style={{
                      height: "4px", background: "#1c2230", borderRadius: "2px", overflow: "hidden"
                    }}>
                      <div className="score-bar" style={{
                        height: "100%",
                        width: scoreBarWidth(sig.score),
                        background: `linear-gradient(90deg, ${SEVERITY_COLORS[sig.severity]}88, ${SEVERITY_COLORS[sig.severity]})`,
                        borderRadius: "2px",
                      }} />
                    </div>
                  </div>

                  {/* Triggers */}
                  <div style={{ display: "flex", gap: "4px", flexWrap: "wrap" }}>
                    {sig.triggers.map(t => (
                      <span key={t} style={{
                        fontSize: "9px",
                        fontWeight: 600,
                        letterSpacing: "0.06em",
                        padding: "2px 5px",
                        borderRadius: "2px",
                        color: TRIGGER_LABELS[t]?.color,
                        background: `${TRIGGER_LABELS[t]?.color}18`,
                        border: `1px solid ${TRIGGER_LABELS[t]?.color}33`,
                      }}>
                        {TRIGGER_LABELS[t]?.label}
                      </span>
                    ))}
                  </div>

                  {/* EOL Days */}
                  <div style={{
                    textAlign: "right",
                    color: sig.eol_days < 100 ? "#ff4444" : sig.eol_days < 200 ? "#f5a623" : "#4a5568",
                    fontWeight: sig.eol_days < 100 ? 600 : 400,
                  }}>
                    {sig.eol_days}d
                  </div>

                  {/* CVEs */}
                  <div style={{
                    textAlign: "right",
                    color: sig.cve_count > 0 ? "#c471ed" : "#3a4556",
                    fontWeight: sig.cve_count > 0 ? 600 : 400,
                  }}>
                    {sig.cve_count > 0 ? sig.cve_count : "—"}
                  </div>
                </div>
              ))}
            </div>
          )}

          {/* Digest Tab */}
          {activeTab === "digest" && (
            <div className="fade-in" style={{ padding: "28px", overflowY: "auto", flex: 1 }}>
              <div style={{
                display: "flex", alignItems: "center", gap: "10px", marginBottom: "20px"
              }}>
                <span style={{
                  fontSize: "10px", letterSpacing: "0.1em", textTransform: "uppercase",
                  color: "#4a9eff", fontWeight: 600,
                }}>
                  AI DIGEST
                </span>
                <span style={{ color: "#3a4556", fontSize: "11px" }}>— generated by Claude</span>
              </div>
              <div style={{
                fontFamily: "'IBM Plex Sans', sans-serif",
                color: "#a8b4c4",
                lineHeight: "1.75",
                fontSize: "13.5px",
                whiteSpace: "pre-line",
              }}>
                {MOCK_DATA.digest}
              </div>
            </div>
          )}
        </div>

        {/* Right Panel — Detail */}
        <div style={{ background: "#0d1117", overflowY: "auto" }}>
          {selectedSignal ? (
            <div className="fade-in" style={{ padding: "24px" }}>
              <div style={{ marginBottom: "20px" }}>
                <div style={{ display: "flex", alignItems: "center", gap: "10px", marginBottom: "6px" }}>
                  <div style={{
                    width: "4px", height: "20px", borderRadius: "2px",
                    background: SEVERITY_COLORS[selectedSignal.severity],
                  }} />
                  <span style={{
                    fontFamily: "'IBM Plex Sans', sans-serif",
                    fontSize: "16px",
                    fontWeight: 700,
                    color: "#e8edf4",
                  }}>{selectedSignal.tech}</span>
                </div>
                <div style={{ color: "#4a5568", fontSize: "11px", paddingLeft: "14px" }}>
                  Composite Signal Score: <span style={{
                    color: SEVERITY_COLORS[selectedSignal.severity],
                    fontWeight: 600, fontSize: "13px"
                  }}>{selectedSignal.score}</span>
                </div>
              </div>

              {/* Metrics Grid */}
              <div style={{
                display: "grid", gridTemplateColumns: "1fr 1fr",
                gap: "8px", marginBottom: "20px"
              }}>
                {[
                  { label: "EOL Days Out", value: `${selectedSignal.eol_days}d`, color: selectedSignal.eol_days < 100 ? "#ff4444" : "#f5a623" },
                  { label: "SO Delta", value: `+${selectedSignal.so_delta}%`, color: "#f5a623" },
                  { label: "CVEs (7d)", value: selectedSignal.cve_count, color: selectedSignal.cve_count > 0 ? "#c471ed" : "#3a4556" },
                  { label: "GH Mentions", value: selectedSignal.gh_mentions, color: "#4a9eff" },
                ].map(m => (
                  <div key={m.label} style={{
                    background: "#111720",
                    border: "1px solid #1c2230",
                    borderRadius: "4px",
                    padding: "12px",
                  }}>
                    <div style={{ color: "#3a4556", fontSize: "10px", letterSpacing: "0.08em", textTransform: "uppercase", marginBottom: "6px" }}>
                      {m.label}
                    </div>
                    <div style={{ color: m.color, fontSize: "20px", fontWeight: 700, fontFamily: "'IBM Plex Sans', sans-serif" }}>
                      {m.value}
                    </div>
                  </div>
                ))}
              </div>

              {/* Trigger Badges */}
              <div style={{ marginBottom: "20px" }}>
                <div style={{ color: "#3a4556", fontSize: "10px", letterSpacing: "0.1em", textTransform: "uppercase", marginBottom: "10px" }}>
                  Active Triggers
                </div>
                <div style={{ display: "flex", gap: "6px", flexWrap: "wrap" }}>
                  {selectedSignal.triggers.map(t => (
                    <div key={t} style={{
                      padding: "6px 12px",
                      borderRadius: "3px",
                      fontSize: "11px",
                      fontWeight: 600,
                      letterSpacing: "0.06em",
                      color: TRIGGER_LABELS[t]?.color,
                      background: `${TRIGGER_LABELS[t]?.color}15`,
                      border: `1px solid ${TRIGGER_LABELS[t]?.color}30`,
                    }}>
                      {t.replace("_", " ").toUpperCase()}
                    </div>
                  ))}
                </div>
              </div>

              {/* Recommended Action */}
              <div style={{
                background: "rgba(74,158,255,0.05)",
                border: "1px solid rgba(74,158,255,0.15)",
                borderRadius: "4px",
                padding: "16px",
              }}>
                <div style={{ color: "#4a9eff", fontSize: "10px", letterSpacing: "0.1em", textTransform: "uppercase", marginBottom: "10px" }}>
                  Suggested Action
                </div>
                <div style={{ color: "#8a9ab4", fontSize: "12px", lineHeight: "1.6", fontFamily: "'IBM Plex Sans', sans-serif" }}>
                  {selectedSignal.eol_days < 100
                    ? `Immediate outreach priority. ${selectedSignal.tech} reaches EOL in ${selectedSignal.eol_days} days — target IT leaders running this version with a direct extended support offer.`
                    : selectedSignal.so_delta > 30
                    ? `Demand surge detected. Stack Overflow volume is up ${selectedSignal.so_delta}% — queue a content asset now while the audience is actively searching.`
                    : `Monitor and queue. Signal is building but not yet urgent. Schedule a follow-up check in 2 weeks.`}
                </div>
              </div>
            </div>
          ) : (
            <div style={{
              height: "100%",
              display: "flex",
              flexDirection: "column",
              alignItems: "center",
              justifyContent: "center",
              color: "#2a3040",
              gap: "8px",
            }}>
              <div style={{ fontSize: "32px" }}>◈</div>
              <div style={{ fontSize: "11px", letterSpacing: "0.1em", textTransform: "uppercase" }}>
                Select a technology
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
