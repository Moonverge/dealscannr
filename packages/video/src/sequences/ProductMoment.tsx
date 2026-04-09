import { interpolate, spring, useCurrentFrame } from "remotion";
import { SceneShell } from "../components/SceneShell";
import { theme } from "../theme";
import { FRAMES, SNAP } from "../timing";

const LANES = [
  { icon: "⚖", label: "Litigation", searching: "Searching SEC EDGAR, CourtListener…" },
  { icon: "⚙", label: "Engineering", searching: "Analyzing GitHub activity…" },
  { icon: "👥", label: "Hiring", searching: "Scanning job boards…" },
  { icon: "📰", label: "News", searching: "Fetching recent coverage…" },
] as const;

const LANE_DONE_AT = [52, 64, 76, 88];

const REPORT_LANES = [
  { icon: "⚖", label: "Litigation", status: "Complete", signals: 5, tone: theme.green },
  { icon: "⚙", label: "Engineering", status: "Complete", signals: 5, tone: theme.green },
  { icon: "👥", label: "Hiring", status: "Partial", signals: 3, tone: theme.yellow },
  { icon: "📰", label: "News", status: "Complete", signals: 5, tone: theme.green },
] as const;

export function ProductMoment() {
  const frame = useCurrentFrame();

  const browserIn = spring({ frame, fps: 30, config: SNAP });

  const url =
    frame < 36
      ? "dealscannr.com"
      : frame < 106
        ? "dealscannr.com/scan/abc-1234/progress"
        : "dealscannr.com/scan/abc-1234/report";

  const tabTitle =
    frame < 36
      ? "DealScannr — Due diligence in 60 seconds"
      : frame < 106
        ? "Scan in progress — DealScannr"
        : "Atlassian — Report — DealScannr";

  const load1 = frame >= 34 && frame <= 40;
  const load2 = frame >= 104 && frame <= 110;
  const showLoad = load1 || load2;
  const loadProg = load2
    ? interpolate(frame, [104, 110], [0, 1], {
        extrapolateLeft: "clamp",
        extrapolateRight: "clamp",
      })
    : interpolate(frame, [34, 40], [0, 1], {
        extrapolateLeft: "clamp",
        extrapolateRight: "clamp",
      });

  const pageFlash = Math.max(
    interpolate(frame, [35, 36, 38], [0, 0.1, 0], {
      extrapolateLeft: "clamp",
      extrapolateRight: "clamp",
    }),
    interpolate(frame, [105, 106, 108], [0, 0.1, 0], {
      extrapolateLeft: "clamp",
      extrapolateRight: "clamp",
    }),
  );

  const p1 = interpolate(frame, [0, 6, 32, 38], [0, 1, 1, 0], {
    extrapolateRight: "clamp",
  });
  const p2 = interpolate(frame, [36, 42, 100, 108], [0, 1, 1, 0], {
    extrapolateRight: "clamp",
  });
  const p3 = interpolate(frame, [106, 114], [0, 1], {
    extrapolateRight: "clamp",
  });

  const searchText = "Atlassian";
  const typed = Math.floor(
    interpolate(frame, [8, 20], [0, searchText.length], {
      extrapolateLeft: "clamp",
      extrapolateRight: "clamp",
    }),
  );
  const cur = frame >= 8 && frame < 28 && Math.floor(frame / 3) % 2 === 0;
  const btnGlow = frame >= 22 && frame < 35;

  const progPct = interpolate(frame, [42, 95], [0, 100], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  const elSec = Math.max(0, Math.floor((frame - 42) * 0.7));
  const elStr = `${Math.floor(elSec / 60)}:${String(elSec % 60).padStart(2, "0")}`;

  // Phase 3 springs
  const verdictS = spring({ frame: frame - 116, fps: 30, config: { damping: 14, mass: 0.35, stiffness: 260 } });
  const riskS = spring({ frame: frame - 120, fps: 30, config: SNAP });
  const actionS = spring({ frame: frame - 118, fps: 30, config: SNAP });
  const signalOverS = spring({ frame: frame - 126, fps: 30, config: SNAP });
  const confidenceS = spring({ frame: frame - 132, fps: 30, config: SNAP });
  const execS = spring({ frame: frame - 138, fps: 30, config: SNAP });
  const probeS = spring({ frame: frame - 146, fps: 30, config: SNAP });

  const scrollY = interpolate(frame, [155, 185], [0, -340], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  const laneCards = REPORT_LANES.map((_, i) =>
    spring({ frame: frame - (162 + i * 3), fps: 30, config: SNAP }),
  );
  const unknownsS = spring({ frame: frame - 178, fps: 30, config: SNAP });
  const disclaimerS = interpolate(frame, [186, 196], [0, 1], { extrapolateRight: "clamp" });

  const confidencePct = interpolate(frame, [134, 150], [0, 72], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  const noShrink: React.CSSProperties = { flexShrink: 0 };

  return (
    <SceneShell accent durationFrames={FRAMES.product}>
      {/* Browser window */}
      <div
        style={{
          position: "absolute",
          inset: 0,
          borderRadius: 14,
          overflow: "hidden",
          border: `1px solid ${theme.border}`,
          backgroundColor: theme.canvas,
          boxShadow:
            "0 20px 60px rgba(0,0,0,0.55), 0 0 0 1px rgba(255,255,255,0.04)",
          display: "flex",
          flexDirection: "column",
          opacity: browserIn,
          transform: `translateY(${interpolate(browserIn, [0, 1], [14, 0])}px)`,
        }}
      >
        {/* Title bar */}
        <div
          style={{
            ...noShrink,
            height: 38,
            backgroundColor: theme.shellNav,
            display: "flex",
            alignItems: "center",
            padding: "0 14px",
            gap: 8,
            borderBottom: `1px solid ${theme.border}`,
          }}
        >
          {["#ff5f57", "#febc2e", "#28c840"].map((c) => (
            <div
              key={c}
              style={{
                width: 12,
                height: 12,
                borderRadius: "50%",
                backgroundColor: c,
              }}
            />
          ))}
          <div
            style={{
              marginLeft: 10,
              padding: "4px 14px",
              borderRadius: 6,
              backgroundColor: theme.surface2,
              fontSize: 12,
              color: theme.muted,
              fontFamily: theme.fontSans,
              whiteSpace: "nowrap",
              overflow: "hidden",
              maxWidth: 420,
            }}
          >
            {tabTitle}
          </div>
        </div>

        {/* Address bar */}
        <div
          style={{
            ...noShrink,
            height: 34,
            backgroundColor: theme.surface,
            display: "flex",
            alignItems: "center",
            padding: "0 14px",
            borderBottom: `1px solid ${theme.border}`,
          }}
        >
          <div
            style={{
              flex: 1,
              maxWidth: 560,
              padding: "3px 12px",
              borderRadius: 6,
              backgroundColor: theme.surface2,
              fontSize: 13,
              fontFamily: theme.fontMono,
              color: theme.muted,
              display: "flex",
              alignItems: "center",
              gap: 4,
            }}
          >
            <span style={{ color: theme.green, fontSize: 11 }}>🔒</span>
            <span style={{ color: theme.subtle }}>https://</span>
            {url}
          </div>
        </div>

        {/* Loading bar */}
        {showLoad && (
          <div
            style={{
              ...noShrink,
              height: 2,
              backgroundColor: theme.accent,
              width: `${loadProg * 100}%`,
              boxShadow: `0 0 6px ${theme.accent}`,
            }}
          />
        )}

        {/* Viewport */}
        <div
          style={{
            flex: 1,
            position: "relative",
            overflow: "hidden",
            backgroundColor: theme.canvas,
          }}
        >
          {/* ▸ Phase 1 — Landing page */}
          <div style={{ position: "absolute", inset: 0, opacity: p1 }}>
            <div
              style={{
                height: 44,
                display: "flex",
                alignItems: "center",
                justifyContent: "space-between",
                padding: "0 28px",
                borderBottom: `1px solid ${theme.border}`,
              }}
            >
              <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                <span
                  style={{
                    fontSize: 16,
                    fontWeight: 700,
                    color: theme.text,
                    fontFamily: theme.fontDisplay,
                  }}
                >
                  DealScannr
                </span>
                <span
                  style={{
                    fontSize: 10,
                    color: theme.accent,
                    border: `1px solid ${theme.accentBorder}`,
                    borderRadius: 4,
                    padding: "1px 5px",
                    fontWeight: 500,
                  }}
                >
                  beta
                </span>
              </div>
              <div style={{ display: "flex", gap: 18, alignItems: "center" }}>
                {["Pricing", "Methodology"].map((n) => (
                  <span
                    key={n}
                    style={{
                      fontSize: 13,
                      color: theme.muted,
                      fontFamily: theme.fontSans,
                    }}
                  >
                    {n}
                  </span>
                ))}
                <span
                  style={{
                    fontSize: 13,
                    fontWeight: 600,
                    color: "#fff",
                    backgroundColor: theme.accent,
                    padding: "5px 14px",
                    borderRadius: 7,
                    fontFamily: theme.fontSans,
                  }}
                >
                  Get started
                </span>
              </div>
            </div>

            <div
              style={{
                display: "flex",
                flexDirection: "column",
                alignItems: "center",
                justifyContent: "center",
                height: "calc(100% - 44px)",
                textAlign: "center",
              }}
            >
              <div
                style={{
                  fontSize: 40,
                  fontWeight: 600,
                  lineHeight: 1.1,
                  color: theme.text,
                  fontFamily: theme.fontDisplay,
                  letterSpacing: "-0.02em",
                }}
              >
                Due diligence in
                <br />
                60 seconds.
              </div>
              <p
                style={{
                  marginTop: 12,
                  fontSize: 18,
                  color: theme.muted,
                  fontFamily: theme.fontSans,
                }}
              >
                Surface litigation risk, engineering health,
                <br />
                and hiring signals — before the meeting.
              </p>
              <div
                style={{
                  marginTop: 24,
                  width: 560,
                  display: "flex",
                  borderRadius: theme.radiusLg,
                  border: `1px solid ${btnGlow ? theme.accent : theme.border}`,
                  backgroundColor: theme.surface,
                  boxShadow: btnGlow
                    ? `0 0 0 3px ${theme.accentSoft}`
                    : theme.shadowSm,
                  overflow: "hidden",
                }}
              >
                <div
                  style={{
                    flex: 1,
                    padding: "14px 18px",
                    fontSize: 20,
                    color: theme.text,
                    fontFamily: theme.fontSans,
                  }}
                >
                  {typed > 0 ? (
                    searchText.slice(0, typed)
                  ) : (
                    <span style={{ color: theme.subtle }}>
                      Enter company name...
                    </span>
                  )}
                  {cur && (
                    <span style={{ color: theme.accent, fontWeight: 300 }}>│</span>
                  )}
                </div>
                <div
                  style={{
                    display: "flex",
                    alignItems: "center",
                    padding: "0 18px",
                    backgroundColor: theme.accent,
                    color: "#fff",
                    fontSize: 17,
                    fontWeight: 600,
                    fontFamily: theme.fontSans,
                  }}
                >
                  Scan →
                </div>
              </div>
              <p
                style={{
                  marginTop: 10,
                  fontSize: 13,
                  color: theme.subtle,
                  fontFamily: theme.fontSans,
                }}
              >
                No account needed for your first scan
              </p>
            </div>
          </div>

          {/* ▸ Phase 2 — Scan progress */}
          <div
            style={{
              position: "absolute",
              inset: 0,
              opacity: p2,
              display: "flex",
              justifyContent: "center",
            }}
          >
            <div style={{ width: 680, padding: "24px 0" }}>
              <p
                style={{
                  fontSize: 12,
                  fontFamily: theme.fontMono,
                  color: theme.muted,
                }}
              >
                Scan abc-1234
              </p>
              <div
                style={{
                  marginTop: 4,
                  fontSize: 28,
                  fontWeight: 600,
                  color: theme.text,
                  fontFamily: theme.fontDisplay,
                }}
              >
                Atlassian
              </div>
              <p
                style={{
                  marginTop: 2,
                  fontSize: 13,
                  fontFamily: theme.fontMono,
                  color: theme.muted,
                }}
              >
                atlassian.com
              </p>
              <p
                style={{
                  marginTop: 8,
                  fontSize: 15,
                  color: theme.muted,
                  fontFamily: theme.fontSans,
                }}
              >
                Scanning…{" "}
                <span style={{ fontFamily: theme.fontMono, color: theme.text }}>
                  {elStr}
                </span>{" "}
                elapsed
              </p>

              <div
                style={{
                  marginTop: 16,
                  display: "flex",
                  flexDirection: "column",
                  gap: 8,
                }}
              >
                {LANES.map((lane, i) => {
                  const done = frame >= LANE_DONE_AT[i];
                  const active = frame >= 42 + i * 4 && !done;
                  return (
                    <div
                      key={lane.label}
                      style={{
                        display: "flex",
                        alignItems: "center",
                        gap: 10,
                        padding: "10px 14px",
                        borderRadius: theme.radiusLg,
                        border: `1px solid ${done ? theme.green + "40" : theme.border}`,
                        backgroundColor: theme.surface,
                        boxShadow: theme.shadowSm,
                        opacity: spring({
                          frame: frame - (38 + i * 3),
                          fps: 30,
                          config: SNAP,
                        }),
                      }}
                    >
                      <div
                        style={{
                          width: 8,
                          height: 8,
                          borderRadius: "50%",
                          backgroundColor: done
                            ? theme.green
                            : active
                              ? theme.accent
                              : theme.surface3,
                          boxShadow:
                            done || active
                              ? `0 0 5px ${done ? theme.green : theme.accent}`
                              : "none",
                          flexShrink: 0,
                        }}
                      />
                      <span style={{ fontSize: 15 }}>{lane.icon}</span>
                      <span
                        style={{
                          fontSize: 15,
                          fontWeight: 500,
                          color: theme.text,
                          fontFamily: theme.fontSans,
                          flex: 1,
                        }}
                      >
                        {lane.label}
                      </span>
                      <span
                        style={{
                          fontSize: 12,
                          color: done ? theme.green : theme.muted,
                          fontFamily: theme.fontSans,
                        }}
                      >
                        {done ? "Complete" : active ? lane.searching : "Queued"}
                      </span>
                    </div>
                  );
                })}
              </div>

              <div
                style={{
                  marginTop: 16,
                  height: 6,
                  borderRadius: 999,
                  backgroundColor: theme.surface3,
                  overflow: "hidden",
                  border: `1px solid ${theme.border}`,
                }}
              >
                <div
                  style={{
                    height: "100%",
                    borderRadius: 999,
                    width: `${Math.min(progPct, 100)}%`,
                    background: `linear-gradient(90deg, ${theme.accent}, ${theme.accentHover} 55%, ${theme.accent})`,
                    boxShadow: "0 0 10px rgba(61,212,192,0.15)",
                  }}
                />
              </div>
              <p
                style={{
                  marginTop: 10,
                  textAlign: "center",
                  fontSize: 13,
                  color: theme.muted,
                  fontFamily: theme.fontSans,
                }}
              >
                This usually takes 30–60 seconds
              </p>
            </div>
          </div>

          {/* ▸ Phase 3 — Full report with scroll */}
          <div
            style={{
              position: "absolute",
              inset: 0,
              opacity: p3,
              overflow: "hidden",
            }}
          >
            <div
              style={{
                display: "flex",
                justifyContent: "center",
                transform: `translateY(${scrollY}px)`,
              }}
            >
              <div style={{ width: 760, padding: "18px 0 40px" }}>
                {/* Header */}
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
                  <div>
                    <p
                      style={{
                        fontSize: 10,
                        fontWeight: 600,
                        textTransform: "uppercase",
                        letterSpacing: "0.14em",
                        color: theme.subtle,
                        fontFamily: theme.fontSans,
                      }}
                    >
                      Intelligence report
                    </p>
                    <div
                      style={{
                        marginTop: 3,
                        fontSize: 24,
                        fontWeight: 600,
                        letterSpacing: "-0.02em",
                        color: theme.text,
                        fontFamily: theme.fontDisplay,
                      }}
                    >
                      Atlassian
                    </div>
                    <p
                      style={{
                        marginTop: 1,
                        fontSize: 12,
                        fontFamily: theme.fontMono,
                        color: theme.muted,
                      }}
                    >
                      atlassian.com
                    </p>
                  </div>

                  {/* Action buttons */}
                  <div
                    style={{
                      display: "flex",
                      gap: 6,
                      opacity: actionS,
                      marginTop: 16,
                    }}
                  >
                    {["↻ Rescan", "↓ Export PDF", "⤴ Share"].map((label) => (
                      <div
                        key={label}
                        style={{
                          padding: "5px 12px",
                          borderRadius: theme.radiusMd,
                          border: `1px solid ${theme.border}`,
                          backgroundColor: theme.surface,
                          fontSize: 11,
                          fontWeight: 500,
                          color: theme.muted,
                          fontFamily: theme.fontSans,
                          whiteSpace: "nowrap",
                        }}
                      >
                        {label}
                      </div>
                    ))}
                  </div>
                </div>

                {/* Badges row */}
                <div
                  style={{
                    marginTop: 10,
                    display: "flex",
                    flexWrap: "wrap",
                    gap: 7,
                    alignItems: "center",
                  }}
                >
                  <span
                    style={{
                      padding: "4px 12px",
                      borderRadius: 999,
                      fontSize: 12,
                      fontWeight: 600,
                      color: "#fff",
                      backgroundColor: theme.yellow,
                      fontFamily: theme.fontSans,
                      opacity: verdictS,
                      transform: `scale(${interpolate(verdictS, [0, 1], [1.2, 1])})`,
                    }}
                  >
                    PASS
                  </span>
                  <span
                    style={{
                      padding: "4px 12px",
                      borderRadius: 999,
                      fontSize: 11,
                      fontWeight: 500,
                      color: theme.text,
                      border: `1px solid ${theme.yellow}`,
                      backgroundColor: theme.surface2,
                      fontFamily: theme.fontSans,
                      opacity: riskS,
                    }}
                  >
                    Risk: Signals worth monitoring
                  </span>
                  <span
                    style={{
                      padding: "4px 10px",
                      borderRadius: 999,
                      fontSize: 10,
                      color: theme.muted,
                      backgroundColor: theme.surface,
                      fontFamily: theme.fontSans,
                      opacity: riskS,
                      boxShadow: theme.shadowSm,
                    }}
                  >
                    4/4 lanes · 18 chunks
                  </span>
                </div>

                {/* Signal overview card */}
                <div
                  style={{
                    marginTop: 12,
                    padding: "14px 16px",
                    borderRadius: theme.radiusXl,
                    border: `1px solid rgba(210,153,34,0.3)`,
                    backgroundColor: theme.yellowSoft,
                    boxShadow: theme.shadowMd,
                    opacity: signalOverS,
                    transform: `translateY(${interpolate(signalOverS, [0, 1], [8, 0])}px)`,
                  }}
                >
                  <p
                    style={{
                      fontSize: 10,
                      fontWeight: 600,
                      textTransform: "uppercase",
                      letterSpacing: "0.14em",
                      color: theme.subtle,
                      fontFamily: theme.fontSans,
                    }}
                  >
                    Signal overview
                  </p>
                  <div
                    style={{
                      marginTop: 6,
                      display: "flex",
                      alignItems: "center",
                      gap: 6,
                    }}
                  >
                    <span
                      style={{
                        padding: "3px 10px",
                        borderRadius: 999,
                        fontSize: 11,
                        fontWeight: 600,
                        color: "#fff",
                        backgroundColor: theme.yellow,
                        fontFamily: theme.fontSans,
                      }}
                    >
                      PASS
                    </span>
                    <span
                      style={{
                        padding: "3px 10px",
                        borderRadius: 999,
                        fontSize: 10,
                        fontWeight: 500,
                        color: theme.text,
                        border: `1px solid ${theme.yellow}`,
                        backgroundColor: theme.surface2,
                        fontFamily: theme.fontSans,
                      }}
                    >
                      Signals worth monitoring
                    </span>
                  </div>
                  <p
                    style={{
                      marginTop: 8,
                      fontSize: 12,
                      lineHeight: 1.5,
                      color: theme.muted,
                      fontFamily: theme.fontSans,
                    }}
                  >
                    Based on 18 evidence chunks · 4 of 4 signal lanes returned usable text
                  </p>
                  {/* Per-lane signal chips */}
                  <div style={{ marginTop: 8, display: "flex", flexWrap: "wrap", gap: 6 }}>
                    {[
                      { icon: "⚖", label: "Litigation", n: 5 },
                      { icon: "⚙", label: "Engineering", n: 5 },
                      { icon: "👥", label: "Hiring", n: 4 },
                      { icon: "📰", label: "News", n: 4 },
                    ].map((chip) => (
                      <span
                        key={chip.label}
                        style={{
                          padding: "3px 10px",
                          borderRadius: 999,
                          border: `1px solid ${theme.border}`,
                          backgroundColor: theme.surface,
                          fontSize: 11,
                          color: theme.text,
                          fontFamily: theme.fontSans,
                        }}
                      >
                        {chip.icon} {chip.label}: ~{chip.n} signals
                      </span>
                    ))}
                  </div>
                </div>

                {/* Confidence bar */}
                <div
                  style={{
                    marginTop: 10,
                    padding: "12px 16px",
                    borderRadius: theme.radiusLg,
                    border: `1px solid ${theme.border}`,
                    backgroundColor: theme.surface,
                    boxShadow: theme.shadowSm,
                    opacity: confidenceS,
                    transform: `translateY(${interpolate(confidenceS, [0, 1], [6, 0])}px)`,
                  }}
                >
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                    <p
                      style={{
                        fontSize: 10,
                        fontWeight: 600,
                        textTransform: "uppercase",
                        letterSpacing: "0.14em",
                        color: theme.subtle,
                        fontFamily: theme.fontSans,
                      }}
                    >
                      Model confidence
                    </p>
                    <span
                      style={{
                        fontSize: 12,
                        fontWeight: 600,
                        color: theme.accent,
                        fontFamily: theme.fontMono,
                      }}
                    >
                      {Math.round(confidencePct)}%
                    </span>
                  </div>
                  <div
                    style={{
                      marginTop: 6,
                      height: 6,
                      borderRadius: 999,
                      backgroundColor: theme.surface3,
                      overflow: "hidden",
                    }}
                  >
                    <div
                      style={{
                        height: "100%",
                        borderRadius: 999,
                        width: `${confidencePct}%`,
                        backgroundColor: theme.accent,
                        boxShadow: `0 0 8px rgba(61,212,192,0.2)`,
                      }}
                    />
                  </div>
                </div>

                {/* Executive readout */}
                <div
                  style={{
                    marginTop: 10,
                    padding: "14px 16px",
                    borderRadius: theme.radiusXl,
                    border: `1px solid ${theme.border}`,
                    backgroundColor: theme.surface,
                    boxShadow: theme.shadowMd,
                    opacity: execS,
                    transform: `translateY(${interpolate(execS, [0, 1], [8, 0])}px)`,
                  }}
                >
                  <p
                    style={{
                      fontSize: 10,
                      fontWeight: 600,
                      textTransform: "uppercase",
                      letterSpacing: "0.14em",
                      color: theme.subtle,
                      fontFamily: theme.fontSans,
                    }}
                  >
                    Executive readout
                  </p>
                  <p
                    style={{
                      marginTop: 6,
                      fontSize: 13,
                      lineHeight: 1.7,
                      color: theme.text,
                      fontFamily: theme.fontSans,
                    }}
                  >
                    Atlassian is publicly traded (NASDAQ: TEAM) with stable
                    engineering velocity. No active federal litigation flagged.
                    Hiring velocity flat QoQ — consistent with post-layoff stabilization.{" "}
                    <span
                      style={{
                        fontFamily: theme.fontMono,
                        fontSize: 10,
                        color: theme.accent,
                      }}
                    >
                      [1][2][3]
                    </span>
                  </p>
                </div>

                {/* Probes card */}
                <div
                  style={{
                    marginTop: 10,
                    padding: "14px 16px",
                    borderRadius: theme.radiusLg,
                    border: `1px solid ${theme.border}`,
                    backgroundColor: theme.surface2,
                    opacity: probeS,
                    transform: `translateY(${interpolate(probeS, [0, 1], [8, 0])}px)`,
                  }}
                >
                  <p
                    style={{
                      fontSize: 10,
                      fontWeight: 600,
                      textTransform: "uppercase",
                      letterSpacing: "0.14em",
                      color: theme.accent,
                      fontFamily: theme.fontSans,
                      marginBottom: 6,
                    }}
                  >
                    Before the call, probe
                  </p>
                  {[
                    "Market positioning post-Jira Cloud migration",
                    "Recent executive departures and board changes",
                    "Competitive pressure from Linear, Notion, Monday",
                  ].map((q, i) => (
                    <div
                      key={q}
                      style={{
                        display: "flex",
                        gap: 6,
                        marginTop: i > 0 ? 4 : 0,
                        fontSize: 12,
                        lineHeight: 1.5,
                        color: theme.text,
                        fontFamily: theme.fontSans,
                      }}
                    >
                      <span style={{ color: theme.accent }}>•</span>
                      {q}
                    </div>
                  ))}
                </div>

                {/* Lane section cards (collapsed) */}
                <div style={{ marginTop: 12, display: "flex", flexDirection: "column", gap: 6 }}>
                  {REPORT_LANES.map((lane, i) => (
                    <div
                      key={lane.label}
                      style={{
                        display: "flex",
                        alignItems: "center",
                        gap: 10,
                        padding: "10px 14px",
                        borderRadius: theme.radiusLg,
                        border: `1px solid ${theme.border}`,
                        backgroundColor: theme.surface,
                        boxShadow: theme.shadowSm,
                        opacity: laneCards[i],
                        transform: `translateY(${interpolate(laneCards[i], [0, 1], [6, 0])}px)`,
                      }}
                    >
                      <span style={{ fontSize: 10, color: theme.muted, transform: "rotate(-90deg)" }}>▸</span>
                      <span style={{ fontSize: 14 }}>{lane.icon}</span>
                      <span
                        style={{
                          fontSize: 13,
                          fontWeight: 600,
                          color: theme.text,
                          fontFamily: theme.fontDisplay,
                          flex: 1,
                        }}
                      >
                        {lane.label}
                      </span>
                      <span
                        style={{
                          fontSize: 11,
                          fontWeight: 500,
                          color: lane.tone,
                          fontFamily: theme.fontSans,
                        }}
                      >
                        {lane.status}
                      </span>
                      <span
                        style={{
                          padding: "2px 8px",
                          borderRadius: 999,
                          backgroundColor: theme.surface2,
                          fontSize: 10,
                          color: theme.muted,
                          fontFamily: theme.fontMono,
                        }}
                      >
                        {lane.signals} signals
                      </span>
                    </div>
                  ))}
                </div>

                {/* Known unknowns */}
                <div
                  style={{
                    marginTop: 12,
                    padding: "12px 16px",
                    borderRadius: theme.radiusLg,
                    borderLeft: `4px solid ${theme.yellow}`,
                    border: `1px solid ${theme.noticeBorder}`,
                    borderLeftWidth: 4,
                    backgroundColor: theme.yellowSoft,
                    boxShadow: theme.shadowSm,
                    opacity: unknownsS,
                    transform: `translateY(${interpolate(unknownsS, [0, 1], [6, 0])}px)`,
                  }}
                >
                  <p
                    style={{
                      fontSize: 12,
                      fontWeight: 600,
                      color: theme.yellow,
                      fontFamily: theme.fontDisplay,
                    }}
                  >
                    What we couldn&apos;t find
                  </p>
                  {[
                    "No OSHA workplace safety complaints surfaced",
                    "Private market valuation data not available",
                    "Pre-IPO cap table details not indexed",
                  ].map((item, i) => (
                    <div
                      key={item}
                      style={{
                        marginTop: i === 0 ? 6 : 3,
                        fontSize: 11,
                        lineHeight: 1.5,
                        color: theme.muted,
                        fontFamily: theme.fontSans,
                        display: "flex",
                        gap: 6,
                      }}
                    >
                      <span style={{ color: theme.yellow }}>•</span>
                      {item}
                    </div>
                  ))}
                </div>

                {/* Disclaimer */}
                <div
                  style={{
                    marginTop: 10,
                    padding: "10px 14px",
                    borderRadius: theme.radiusMd,
                    border: `1px solid ${theme.border}`,
                    backgroundColor: `${theme.surface}99`,
                    opacity: disclaimerS,
                  }}
                >
                  <p
                    style={{
                      fontSize: 10,
                      lineHeight: 1.5,
                      color: theme.subtle,
                      fontFamily: theme.fontSans,
                    }}
                  >
                    AI-generated report based on automated evidence retrieval. Citations link to source captures but do not constitute legal, financial, or investment advice. Verify all claims against primary sources before acting.
                  </p>
                </div>
              </div>
            </div>
          </div>

          {/* Page-transition flash */}
          <div
            style={{
              position: "absolute",
              inset: 0,
              backgroundColor: "#fff",
              opacity: pageFlash,
              pointerEvents: "none",
            }}
          />
        </div>
      </div>
    </SceneShell>
  );
}
