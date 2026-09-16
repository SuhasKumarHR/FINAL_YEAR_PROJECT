"use client";

import { useState, FormEvent, useRef, useEffect, useMemo } from "react";
import { toast } from "sonner";
import { io, Socket } from "socket.io-client";
import gsap from "gsap";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from "recharts";
import {
  Terminal,
  CheckCircle2,
  GitPullRequest,
  Settings,
  Loader2,
  Download,
  ChevronDown,
  ShieldCheck,
  Zap,
  GitBranch,
  Cpu,
  Server,
  Code2,
  ArrowRight,
  Activity,
  Sparkles,
  CircleDot,
  RotateCcw,
} from "lucide-react";

/*
  ACR AGENT — Autonomous Code Recovery

  IMPORTANT:
  - Backend/socket behavior is intentionally kept compatible with the old page.
  - Put the generated HUD background image at:
      /public/acr-hud-bg.png
  - Set:
      NEXT_PUBLIC_BACKEND_URL=http://127.0.0.1:8000
    or your actual backend URL in .env.local
*/

const BACKEND_URL =
  process.env.NEXT_PUBLIC_BACKEND_URL || "http://127.0.0.1:8000";

type LogEntry = {
  id: string;
  message: string;
  type: "info" | "success" | "error" | "warning";
};

type FixEntry = {
  bug_type: string;
  file_path: string;
  line_number?: number;
  commit_message?: string;
  status?: "Fixed" | "Failed";
};

type SummaryData = {
  status: string;
  total_time: number;
  pr_link: string;
  branch: string;
  fixes: FixEntry[];
  iterations_used?: number;
  total_failures?: number;
  commits_count?: number;
};

export default function Home() {
  const [repoUrl, setRepoUrl] = useState("");
  const [teamName, setTeamName] = useState("");
  const [teamLeader, setTeamLeader] = useState("");
  const [retryLimit, setRetryLimit] = useState(5);
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [isGeminiError, setIsGeminiError] = useState(false);

  const socketRef = useRef<Socket | null>(null);

  const [status, setStatus] = useState<"idle" | "running" | "completed">(
    "idle",
  );
  const [currentStage, setCurrentStage] = useState("Initializing...");
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [summary, setSummary] = useState<SummaryData | null>(null);
  const [elapsedSeconds, setElapsedSeconds] = useState(0);

  const logsEndRef = useRef<HTMLDivElement>(null);
  const logContainerRef = useRef<HTMLDivElement>(null);

  const isRunning = status === "running";
  const isCompleted = status === "completed";

  useEffect(() => {
    const newSocket = io(BACKEND_URL, {
      autoConnect: false,
      rejectUnauthorized: false,
      extraHeaders: {
        "ngrok-skip-browser-warning": "true",
      },
    });

    socketRef.current = newSocket;

    const detectGeminiError = (message: string) => {
      const lower = message.toLowerCase();
      return (
        lower.includes("gemini") ||
        lower.includes("unavailable") ||
        lower.includes("resource_exhausted") ||
        lower.includes("rate limit") ||
        lower.includes("quota")
      );
    };

    newSocket.on(
      "log",
      (data: {
        message: string;
        type: LogEntry["type"];
        stage?: string;
      }) => {
        if (detectGeminiError(data.message)) {
          setIsGeminiError(true);
          setErrorMessage((prev) => prev || data.message);
        }

        setLogs((prev) => [
          ...prev,
          {
            id: Math.random().toString(36).substring(7),
            message: data.message,
            type: data.type,
          },
        ]);

        if (data.stage) setCurrentStage(data.stage);
      },
    );

    newSocket.on("completed", (data: SummaryData) => {
      setStatus("completed");
      setSummary(data);
      setErrorMessage(null);
      setIsGeminiError(false);
      toast.success("Analysis and healing complete!");
      newSocket.disconnect();
    });

    newSocket.on("error_fatal", (data: { message: string }) => {
      setStatus("completed");
      setSummary(null);
      setErrorMessage(data.message);
      setIsGeminiError(detectGeminiError(data.message));
      toast.error(data.message);
      newSocket.disconnect();
    });

    newSocket.on("connect_error", (err) => {
      setStatus("completed");
      setSummary(null);
      setErrorMessage(
        `Unable to connect to ACR backend: ${err.message}`,
      );
      toast.error("Backend connection failed");
    });

    return () => {
      newSocket.disconnect();
    };
  }, []);

  useEffect(() => {
    let interval: NodeJS.Timeout;

    if (status === "running") {
      interval = setInterval(
        () => setElapsedSeconds((prev) => prev + 1),
        1000,
      );
    }

    return () => clearInterval(interval);
  }, [status]);

  useEffect(() => {
    if (logContainerRef.current && logs.length > 0) {
      const lastElement = logContainerRef.current.lastElementChild;

      if (lastElement) {
        gsap.fromTo(
          lastElement,
          { opacity: 0, x: -10 },
          { opacity: 1, x: 0, duration: 0.3 },
        );
      }

      logsEndRef.current?.scrollIntoView({ behavior: "smooth" });
    }
  }, [logs]);

  const formatTime = (seconds: number) => {
    const m = Math.floor(seconds / 60)
      .toString()
      .padStart(2, "0");
    const s = (seconds % 60).toString().padStart(2, "0");
    return `${m}:${s}`;
  };

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();

    if (!repoUrl.trim() || !teamName.trim() || !teamLeader.trim()) {
      toast.error("Please fill in all fields");
      return;
    }

    setStatus("running");
    setLogs([]);
    setElapsedSeconds(0);
    setSummary(null);
    setErrorMessage(null);
    setIsGeminiError(false);
    setCurrentStage("Connecting to deployment fabric...");

    socketRef.current?.connect();

    socketRef.current?.emit("start_agent", {
      repo_url: repoUrl,
      team_name: teamName,
      leader_name: teamLeader,
      retry_limit: retryLimit,
    });
  };

  const getChartData = () => {
    if (!summary?.fixes) return [];

    const counts: Record<string, number> = {};

    summary.fixes.forEach((f) => {
      counts[f.bug_type] = (counts[f.bug_type] || 0) + 1;
    });

    return Object.keys(counts).map((key) => ({
      name: key,
      count: counts[key],
    }));
  };

  const calculateScore = () => {
    if (!summary) {
      return {
        baseScore: 100,
        speedBonus: 0,
        efficiencyPenalty: 0,
        finalScore: 100,
      };
    }

    const baseScore = 100;
    const timeInMinutes = summary.total_time;
    const speedBonus = timeInMinutes < 5 ? 10 : 0;
    const commitsCount = summary.commits_count || 1;
    const efficiencyPenalty =
      commitsCount > 20 ? (commitsCount - 20) * -2 : 0;

    const finalScore = Math.max(
      0,
      baseScore + speedBonus + efficiencyPenalty,
    );

    return {
      baseScore,
      speedBonus,
      efficiencyPenalty,
      finalScore,
    };
  };

  const downloadResults = () => {
    if (!summary) return;

    const score = calculateScore();

    const resultsData = {
      repository_url: repoUrl,
      team_details: {
        team_name: teamName,
        leader_name: teamLeader,
      },
      branch_name: summary.branch,
      total_failures: summary.total_failures || summary.fixes.length,
      total_fixes: summary.fixes.length,
      iterations_used: summary.iterations_used || 1,
      ci_timeline: {
        start_time: new Date(
          Date.now() - elapsedSeconds * 1000,
        ).toISOString(),
        end_time: new Date().toISOString(),
        total_duration_minutes: summary.total_time,
        total_duration_seconds: elapsedSeconds,
      },
      final_status: summary.status,
      score_breakdown: {
        base_score: score.baseScore,
        speed_bonus: score.speedBonus,
        speed_bonus_description: "Applied if total time < 5 minutes",
        efficiency_penalty: score.efficiencyPenalty,
        efficiency_penalty_description:
          "-2 points per commit over 20",
        final_total_score: score.finalScore,
      },
      fixes_details: summary.fixes,
      pull_request_link: summary.pr_link,
      generated_at: new Date().toISOString(),
    };

    const blob = new Blob(
      [JSON.stringify(resultsData, null, 2)],
      { type: "application/json" },
    );

    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");

    link.href = url;
    link.download = `rift-results-${teamName
      .replace(/\s+/g, "-")
      .toLowerCase()}-${Date.now()}.json`;

    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  };

  const score = useMemo(() => calculateScore(), [summary]);

  const resetRun = () => {
    socketRef.current?.disconnect();
    setStatus("idle");
    setSummary(null);
    setLogs([]);
    setElapsedSeconds(0);
    setErrorMessage(null);
    setIsGeminiError(false);
    setCurrentStage("Initializing...");
  };

  return (
    <div className="min-h-screen overflow-x-hidden bg-[#020817] text-white selection:bg-cyan-400 selection:text-black">
      <style jsx global>{`
        html {
          background: #020817;
        }

        body {
          margin: 0;
          background: #020817;
        }

        .acr-bg {
          background:
            radial-gradient(
              circle at 82% 20%,
              rgba(0, 132, 255, 0.22),
              transparent 28%
            ),
            radial-gradient(
              circle at 18% 68%,
              rgba(0, 225, 255, 0.13),
              transparent 26%
            ),
            linear-gradient(
              180deg,
              rgba(1, 9, 31, 0.9),
              rgba(2, 8, 23, 0.98)
            ),
            url("/acr-hud-bg.png") center top / cover fixed no-repeat;
        }

        .acr-grid {
          background-image:
            linear-gradient(
              rgba(30, 125, 255, 0.08) 1px,
              transparent 1px
            ),
            linear-gradient(
              90deg,
              rgba(30, 125, 255, 0.08) 1px,
              transparent 1px
            );
          background-size: 52px 52px;
          mask-image: linear-gradient(
            to bottom,
            black,
            transparent 88%
          );
        }

        .acr-panel {
          background: linear-gradient(
            145deg,
            rgba(7, 21, 49, 0.92),
            rgba(2, 9, 23, 0.84)
          );
          border: 1px solid rgba(47, 167, 255, 0.28);
          box-shadow:
            0 0 0 1px rgba(0, 191, 255, 0.03) inset,
            0 20px 80px rgba(0, 20, 80, 0.32);
          backdrop-filter: blur(18px);
        }

        .acr-input {
          background: rgba(2, 10, 25, 0.88);
          border: 1px solid rgba(70, 155, 220, 0.28);
        }

        .acr-input:focus {
          border-color: rgba(34, 211, 238, 0.8);
          box-shadow: 0 0 0 3px rgba(34, 211, 238, 0.09);
        }

        .acr-card {
          background: linear-gradient(
            145deg,
            rgba(10, 30, 62, 0.72),
            rgba(2, 10, 25, 0.82)
          );
          border: 1px solid rgba(54, 170, 255, 0.24);
          box-shadow: 0 12px 45px rgba(0, 25, 90, 0.2);
        }

        .acr-glow {
          box-shadow:
            0 0 20px rgba(0, 191, 255, 0.25),
            0 0 70px rgba(0, 119, 255, 0.12);
        }

        .acr-scan {
          position: relative;
          overflow: hidden;
        }

        .acr-scan::after {
          content: "";
          position: absolute;
          inset: 0;
          pointer-events: none;
          background: linear-gradient(
            to bottom,
            transparent,
            rgba(37, 211, 255, 0.05),
            transparent
          );
          transform: translateY(-100%);
          animation: scan 5s linear infinite;
        }

        @keyframes scan {
          to {
            transform: translateY(100%);
          }
        }

        @keyframes pulseDot {
          0%, 100% {
            opacity: 0.35;
            transform: scale(0.85);
          }
          50% {
            opacity: 1;
            transform: scale(1.15);
          }
        }

        .pulse-dot {
          animation: pulseDot 1.7s ease-in-out infinite;
        }

        .tech-border {
          position: relative;
        }

        .tech-border::before,
        .tech-border::after {
          content: "";
          position: absolute;
          width: 30px;
          height: 2px;
          background: #22d3ee;
          box-shadow: 0 0 12px #22d3ee;
        }

        .tech-border::before {
          left: 20px;
          top: -1px;
        }

        .tech-border::after {
          right: 20px;
          bottom: -1px;
        }
      `}</style>

      <div className="fixed inset-0 pointer-events-none acr-bg" />
      <div className="fixed inset-0 pointer-events-none acr-grid opacity-80" />

      {/* Header */}
      <header className="sticky top-0 z-50 border-b border-cyan-500/15 bg-[#020713]/85 backdrop-blur-xl">
        <div className="mx-auto flex max-w-7xl items-center justify-between px-5 py-4 md:px-8">
          <div className="flex items-center gap-3">
            <div className="acr-glow flex h-11 w-11 items-center justify-center rounded-xl border border-cyan-400/60 bg-[#031329]">
              <div className="relative flex h-8 w-8 items-center justify-center rounded-full border-2 border-cyan-300">
                <span className="text-lg font-black text-cyan-200">
                  A
                </span>
                <Settings className="absolute -right-3 -top-3 h-4 w-4 text-cyan-300" />
              </div>
            </div>

            <div>
              <div className="text-lg font-black tracking-tight">
                ACR <span className="text-cyan-300">AGENT</span>
              </div>
              <div className="text-[9px] font-semibold tracking-[0.28em] text-slate-400">
                AUTONOMOUS CODE RECOVERY
              </div>
            </div>
          </div>

          <div className="hidden items-center gap-3 sm:flex">
            <div className="flex items-center gap-2 rounded-full border border-emerald-400/25 bg-emerald-400/5 px-4 py-2 text-xs font-bold text-emerald-300">
              <CircleDot className="pulse-dot h-3 w-3 fill-current" />
              SYSTEM READY
            </div>

            {(isRunning || isCompleted) && (
              <div className="flex items-center gap-2 rounded-full border border-cyan-400/25 bg-cyan-400/5 px-4 py-2 font-mono text-xs text-cyan-200">
                {isRunning ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <CheckCircle2 className="h-4 w-4" />
                )}
                {formatTime(elapsedSeconds)}
              </div>
            )}

            <div className="flex h-10 w-10 items-center justify-center rounded-xl border border-cyan-400/25 bg-cyan-400/5">
              <Settings className="h-4 w-4 text-cyan-300" />
            </div>
          </div>
        </div>
      </header>

      <main className="relative z-10 mx-auto max-w-7xl px-5 pb-24 pt-12 md:px-8 md:pt-16">
        {/* IDLE / HERO */}
        {status === "idle" && (
          <>
            <section className="relative">
              <div className="mx-auto max-w-5xl text-center">
                <div className="mx-auto mb-6 inline-flex items-center gap-2 rounded-full border border-cyan-400/35 bg-cyan-400/5 px-4 py-2 text-xs font-bold tracking-wide text-cyan-200 shadow-[0_0_30px_rgba(0,191,255,.12)]">
                  <Sparkles className="h-4 w-4" />
                  AI-POWERED RELEASE HEALTH
                </div>

                <h1 className="text-5xl font-black tracking-[-0.055em] text-white sm:text-6xl md:text-8xl">
                  Connect Your{" "}
                  <span className="bg-gradient-to-r from-white via-cyan-100 to-cyan-400 bg-clip-text text-transparent">
                    Codebase
                  </span>
                </h1>

                <p className="mx-auto mt-6 max-w-3xl text-base leading-7 text-slate-400 md:text-lg">
                  Detect failures, diagnose root causes, automatically heal
                  defects and prepare your release with a clean audit trail.
                </p>
              </div>

              {/* Feature cards */}
              <div className="mx-auto mt-12 grid max-w-5xl gap-4 md:grid-cols-3">
                {[
                  {
                    icon: ShieldCheck,
                    title: "Detect",
                    text: "Find CI and code failures",
                  },
                  {
                    icon: Zap,
                    title: "Heal",
                    text: "Apply targeted fixes",
                  },
                  {
                    icon: GitBranch,
                    title: "Deliver",
                    text: "Prepare the PR output",
                  },
                ].map((item) => (
                  <div
                    key={item.title}
                    className="acr-card group rounded-2xl p-6 transition-all duration-300 hover:-translate-y-1 hover:border-cyan-400/60 hover:shadow-[0_0_35px_rgba(0,174,255,.14)]"
                  >
                    <item.icon className="h-7 w-7 text-cyan-300 transition-transform group-hover:scale-110" />
                    <div className="mt-7 flex items-center justify-between">
                      <h3 className="text-lg font-bold">{item.title}</h3>
                      <ArrowRight className="h-4 w-4 text-cyan-400 opacity-0 transition-all group-hover:translate-x-1 group-hover:opacity-100" />
                    </div>
                    <p className="mt-2 text-sm text-slate-500">
                      {item.text}
                    </p>
                  </div>
                ))}
              </div>

              {/* Architecture */}
              <div className="mx-auto mt-8 grid max-w-5xl items-center gap-3 md:grid-cols-[1fr_auto_1fr_auto_1fr]">
                {[
                  {
                    icon: Code2,
                    title: "SOURCE",
                    sub: "REPOSITORY",
                  },
                  {
                    icon: Cpu,
                    title: "AGENT CORE",
                    sub: "ANALYZE + HEAL",
                  },
                  {
                    icon: Server,
                    title: "RELEASE",
                    sub: "PR + REPORT",
                  },
                ].map((item, index) => (
                  <div key={item.title} className="contents">
                    <div className="tech-border acr-panel rounded-2xl p-6 text-center">
                      <item.icon className="mx-auto h-7 w-7 text-cyan-300" />
                      <div className="mt-3 text-sm font-black tracking-wider">
                        {item.title}
                      </div>
                      <div className="mt-1 text-[10px] tracking-wider text-slate-500">
                        {item.sub}
                      </div>
                    </div>

                    {index < 2 && (
                      <ArrowRight className="mx-auto hidden h-6 w-6 text-cyan-400 md:block" />
                    )}
                  </div>
                ))}
              </div>
            </section>

            {/* Deployment form */}
            <section className="mx-auto mt-10 max-w-5xl">
              <div className="mb-5 flex justify-center">
                <div className="flex items-center gap-2 rounded-full border border-cyan-400/25 bg-cyan-400/5 px-5 py-2 text-[11px] font-bold tracking-[0.16em] text-cyan-200">
                  <Activity className="h-4 w-4" />
                  DEPLOYMENT FABRIC · LIVE CODE INTELLIGENCE
                </div>
              </div>

              <div className="acr-panel acr-scan tech-border rounded-3xl p-5 md:p-8">
                <div className="mb-7 flex flex-col justify-between gap-4 md:flex-row md:items-center">
                  <div>
                    <h2 className="text-xl font-bold">
                      Deployment details
                    </h2>
                    <p className="mt-1 text-sm text-slate-500">
                      Connect the repository and configure healing.
                    </p>
                  </div>

                  <div className="flex w-fit items-center gap-2 rounded-full border border-emerald-400/20 bg-emerald-400/5 px-4 py-2 text-[10px] font-bold tracking-wider text-emerald-300">
                    <CircleDot className="h-3 w-3 fill-current" />
                    AGENT READY
                  </div>
                </div>

                <form onSubmit={handleSubmit} className="space-y-4">
                  <div>
                    <label className="mb-2 block text-[10px] font-bold uppercase tracking-[0.18em] text-slate-500">
                      Repository
                    </label>
                    <input
                      value={repoUrl}
                      onChange={(e) => setRepoUrl(e.target.value)}
                      placeholder="https://github.com/username/repository"
                      className="acr-input w-full rounded-xl px-4 py-4 font-mono text-sm text-white outline-none transition-all placeholder:text-slate-700"
                      required
                    />
                  </div>

                  <div className="grid gap-4 md:grid-cols-2">
                    <div>
                      <label className="mb-2 block text-[10px] font-bold uppercase tracking-[0.18em] text-slate-500">
                        Team name
                      </label>
                      <input
                        value={teamName}
                        onChange={(e) => setTeamName(e.target.value)}
                        placeholder="ACR ORGANISERS"
                        className="acr-input w-full rounded-xl px-4 py-4 text-sm text-white outline-none transition-all placeholder:text-slate-700"
                        required
                      />
                    </div>

                    <div>
                      <label className="mb-2 block text-[10px] font-bold uppercase tracking-[0.18em] text-slate-500">
                        Team leader
                      </label>
                      <input
                        value={teamLeader}
                        onChange={(e) => setTeamLeader(e.target.value)}
                        placeholder="Team Leader Name"
                        className="acr-input w-full rounded-xl px-4 py-4 text-sm text-white outline-none transition-all placeholder:text-slate-700"
                        required
                      />
                    </div>
                  </div>

                  <div className="overflow-hidden rounded-xl border border-cyan-400/15">
                    <button
                      type="button"
                      onClick={() =>
                        setShowAdvanced((prev) => !prev)
                      }
                      className="flex w-full items-center justify-between bg-cyan-400/[0.025] px-4 py-4 text-left text-sm font-semibold transition hover:bg-cyan-400/[0.06]"
                    >
                      <span className="flex items-center gap-2">
                        <Settings className="h-4 w-4 text-cyan-300" />
                        Advanced Options
                      </span>

                      <ChevronDown
                        className={`h-4 w-4 text-cyan-300 transition-transform ${
                          showAdvanced ? "rotate-180" : ""
                        }`}
                      />
                    </button>

                    {showAdvanced && (
                      <div className="border-t border-cyan-400/10 p-4">
                        <label className="mb-2 block text-xs font-semibold text-slate-300">
                          Retry Limit · Max Healing Iterations
                        </label>

                        <select
                          value={retryLimit}
                          onChange={(e) =>
                            setRetryLimit(Number(e.target.value))
                          }
                          className="acr-input w-full rounded-xl px-4 py-3 text-sm text-white outline-none"
                        >
                          <option value={1}>1 iteration</option>
                          <option value={3}>3 iterations</option>
                          <option value={5}>5 iterations (default)</option>
                          <option value={7}>7 iterations</option>
                          <option value={10}>10 iterations</option>
                          <option value={15}>15 iterations</option>
                        </select>

                        <p className="mt-2 text-xs text-slate-600">
                          Controls how many times the agent attempts to
                          fix remaining errors.
                        </p>
                      </div>
                    )}
                  </div>

                  <button
                    type="submit"
                    className="group flex w-full items-center justify-center gap-3 rounded-xl bg-gradient-to-r from-cyan-500 to-blue-600 py-4 font-black tracking-wide text-white shadow-[0_0_35px_rgba(0,174,255,.22)] transition hover:scale-[1.01] hover:shadow-[0_0_50px_rgba(0,174,255,.35)]"
                  >
                    <Zap className="h-5 w-5 transition-transform group-hover:scale-110" />
                    DEPLOY ACR AGENT
                    <ArrowRight className="h-5 w-5 transition-transform group-hover:translate-x-1" />
                  </button>
                </form>
              </div>
            </section>
          </>
        )}

        {/* RUNNING */}
        {status === "running" && (
          <section className="mx-auto max-w-6xl space-y-6">
            <div className="acr-panel flex flex-col justify-between gap-4 rounded-2xl p-5 md:flex-row md:items-center">
              <div className="flex items-center gap-3">
                <div className="flex h-11 w-11 items-center justify-center rounded-xl border border-cyan-400/25 bg-cyan-400/5">
                  <Loader2 className="h-5 w-5 animate-spin text-cyan-300" />
                </div>

                <div>
                  <div className="text-xs font-bold uppercase tracking-[0.18em] text-cyan-400">
                    Agent execution
                  </div>
                  <div className="mt-1 text-lg font-bold">
                    {currentStage}
                  </div>
                </div>
              </div>

              <div className="font-mono text-sm text-cyan-200">
                {formatTime(elapsedSeconds)}
              </div>
            </div>

            <div className="acr-panel overflow-hidden rounded-3xl">
              <div className="flex items-center justify-between border-b border-cyan-400/10 bg-[#010916] px-5 py-4">
                <div className="flex items-center gap-3">
                  <Terminal className="h-4 w-4 text-cyan-300" />
                  <span className="text-xs font-bold tracking-wider text-slate-300">
                    ACR RUNTIME TELEMETRY
                  </span>
                </div>

                <div className="flex items-center gap-2 text-[10px] font-bold text-emerald-300">
                  <CircleDot className="h-3 w-3 fill-current" />
                  LIVE
                </div>
              </div>

              <div
                ref={logContainerRef}
                className="h-[520px] overflow-y-auto bg-[#01050c] p-5 font-mono text-xs leading-6"
              >
                {logs.length === 0 && (
                  <div className="flex h-full items-center justify-center text-slate-700">
                    Waiting for agent telemetry...
                  </div>
                )}

                {logs.map((log) => (
                  <div
                    key={log.id}
                    className={
                      log.type === "error"
                        ? "text-red-400"
                        : log.type === "success"
                          ? "text-emerald-400"
                          : log.type === "warning"
                            ? "text-amber-300"
                            : "text-slate-300"
                    }
                  >
                    <span className="mr-2 text-slate-700">
                      [{new Date().toLocaleTimeString()}]
                    </span>
                    {log.message}
                  </div>
                ))}

                <div ref={logsEndRef} />
              </div>
            </div>
          </section>
        )}

        {/* COMPLETED */}
        {status === "completed" && (
          <section className="mx-auto max-w-6xl space-y-7">
            <div className="flex flex-col justify-between gap-4 md:flex-row md:items-end">
              <div>
                <div className="mb-2 flex items-center gap-2 text-xs font-bold uppercase tracking-[0.2em] text-cyan-400">
                  <CheckCircle2 className="h-4 w-4" />
                  Execution complete
                </div>

                <h2 className="text-4xl font-black tracking-tight md:text-5xl">
                  Mission Report
                </h2>
              </div>

              <button
                onClick={resetRun}
                className="flex items-center justify-center gap-2 rounded-xl border border-cyan-400/20 bg-cyan-400/5 px-4 py-3 text-sm font-bold text-cyan-200 transition hover:bg-cyan-400/10"
              >
                <RotateCcw className="h-4 w-4" />
                New Analysis
              </button>
            </div>

            {summary ? (
              <>
                <div className="acr-panel rounded-3xl p-6 md:p-8">
                  <div className="mb-7 flex flex-col justify-between gap-4 md:flex-row md:items-center">
                    <div>
                      <div className="text-xs uppercase tracking-[0.2em] text-slate-500">
                        Run Summary
                      </div>
                      <h3 className="mt-2 text-2xl font-bold">
                        {teamName}
                      </h3>
                    </div>

                    <div
                      className={`rounded-full border px-4 py-2 text-xs font-black tracking-wider ${
                        summary.status === "SUCCESS"
                          ? "border-emerald-400/30 bg-emerald-400/10 text-emerald-300"
                          : "border-red-400/30 bg-red-400/10 text-red-300"
                      }`}
                    >
                      {summary.status === "SUCCESS"
                        ? "✓ PASSED"
                        : "✗ FAILED"}
                    </div>
                  </div>

                  <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
                    {[
                      ["Branch", summary.branch || "N/A"],
                      [
                        "Failures",
                        String(
                          summary.total_failures ||
                            summary.fixes.length,
                        ),
                      ],
                      ["Fixes Applied", String(summary.fixes.length)],
                      [
                        "Iterations",
                        String(summary.iterations_used || 1),
                      ],
                    ].map(([label, value]) => (
                      <div
                        key={label}
                        className="rounded-2xl border border-cyan-400/10 bg-black/20 p-4"
                      >
                        <div className="text-[10px] uppercase tracking-[0.18em] text-slate-600">
                          {label}
                        </div>
                        <div className="mt-2 break-all text-lg font-bold text-cyan-100">
                          {value}
                        </div>
                      </div>
                    ))}
                  </div>

                  <div className="mt-4 rounded-2xl border border-cyan-400/10 bg-black/20 p-4">
                    <div className="text-[10px] uppercase tracking-[0.18em] text-slate-600">
                      Repository
                    </div>
                    <div className="mt-2 break-all font-mono text-xs text-slate-300">
                      {repoUrl}
                    </div>
                  </div>
                </div>

                <div className="grid gap-4 md:grid-cols-3">
                  <div className="acr-card rounded-2xl p-6">
                    <div className="text-xs uppercase tracking-[0.16em] text-slate-500">
                      Status
                    </div>
                    <div className="mt-3 flex items-center gap-2 text-2xl font-black">
                      <CheckCircle2 className="h-6 w-6 text-emerald-300" />
                      {summary.status}
                    </div>
                  </div>

                  <div className="acr-card rounded-2xl p-6">
                    <div className="text-xs uppercase tracking-[0.16em] text-slate-500">
                      Total Fixes
                    </div>
                    <div className="mt-3 text-3xl font-black text-cyan-200">
                      {summary.fixes?.length || 0}
                    </div>
                  </div>

                  <div className="acr-card rounded-2xl p-6">
                    <div className="text-xs uppercase tracking-[0.16em] text-slate-500">
                      Pull Request
                    </div>

                    <a
                      href={summary.pr_link}
                      target="_blank"
                      rel="noreferrer"
                      className="mt-3 flex items-center gap-2 text-lg font-bold text-cyan-300 hover:text-cyan-100 hover:underline"
                    >
                      <GitPullRequest className="h-5 w-5" />
                      View on GitHub
                    </a>
                  </div>
                </div>

                {/* Score */}
                <div className="acr-panel rounded-3xl p-6 md:p-8">
                  <div className="flex flex-col justify-between gap-5 md:flex-row md:items-center">
                    <div>
                      <div className="text-xs uppercase tracking-[0.2em] text-slate-500">
                        Autonomous quality score
                      </div>
                      <h3 className="mt-2 text-2xl font-bold">
                        Release Health
                      </h3>
                    </div>

                    <div className="text-5xl font-black text-cyan-200">
                      {score.finalScore}
                    </div>
                  </div>

                  <div className="mt-7 h-3 overflow-hidden rounded-full bg-slate-900">
                    <div
                      className="h-full rounded-full bg-gradient-to-r from-cyan-500 to-blue-500 transition-all duration-1000"
                      style={{
                        width: `${Math.min(
                          100,
                          (score.finalScore / 110) * 100,
                        )}%`,
                      }}
                    />
                  </div>

                  <div className="mt-5 grid gap-3 text-sm md:grid-cols-3">
                    <div className="rounded-xl bg-white/[0.025] p-4">
                      <span className="text-slate-500">Base</span>
                      <strong className="ml-2">
                        {score.baseScore}
                      </strong>
                    </div>

                    <div className="rounded-xl bg-white/[0.025] p-4">
                      <span className="text-slate-500">Speed bonus</span>
                      <strong className="ml-2 text-emerald-300">
                        +{score.speedBonus}
                      </strong>
                    </div>

                    <div className="rounded-xl bg-white/[0.025] p-4">
                      <span className="text-slate-500">Efficiency</span>
                      <strong className="ml-2 text-amber-300">
                        {score.efficiencyPenalty}
                      </strong>
                    </div>
                  </div>
                </div>

                {/* Fix table */}
                {summary.fixes?.length > 0 && (
                  <div className="acr-panel overflow-hidden rounded-3xl">
                    <div className="border-b border-cyan-400/10 p-6">
                      <div className="flex items-center gap-2">
                        <Terminal className="h-5 w-5 text-cyan-300" />
                        <h3 className="text-lg font-bold">
                          Fixes Applied
                        </h3>
                      </div>
                    </div>

                    <div className="overflow-x-auto">
                      <table className="w-full text-sm">
                        <thead className="bg-black/20">
                          <tr className="border-b border-cyan-400/10">
                            <th className="px-4 py-4 text-left text-xs uppercase tracking-wider text-slate-500">
                              File
                            </th>
                            <th className="px-4 py-4 text-left text-xs uppercase tracking-wider text-slate-500">
                              Bug Type
                            </th>
                            <th className="px-4 py-4 text-left text-xs uppercase tracking-wider text-slate-500">
                              Commit
                            </th>
                            <th className="px-4 py-4 text-center text-xs uppercase tracking-wider text-slate-500">
                              Status
                            </th>
                          </tr>
                        </thead>

                        <tbody>
                          {summary.fixes.map((fix, index) => {
                            const fixed = (fix.status || "Fixed") === "Fixed";

                            return (
                              <tr
                                key={index}
                                className="border-b border-cyan-400/5 transition hover:bg-cyan-400/[0.025]"
                              >
                                <td className="max-w-xs break-all px-4 py-4 font-mono text-xs text-slate-300">
                                  {fix.file_path}
                                </td>

                                <td className="px-4 py-4">
                                  <span className="rounded-md border border-cyan-400/20 bg-cyan-400/5 px-2 py-1 text-[10px] font-bold text-cyan-200">
                                    {fix.bug_type}
                                  </span>
                                </td>

                                <td className="max-w-md truncate px-4 py-4 text-xs text-slate-400">
                                  {fix.commit_message ||
                                    "Applied automated fix"}
                                </td>

                                <td className="px-4 py-4 text-center">
                                  <span
                                    className={`rounded-full px-3 py-1 text-[10px] font-bold ${
                                      fixed
                                        ? "bg-emerald-400/10 text-emerald-300"
                                        : "bg-red-400/10 text-red-300"
                                    }`}
                                  >
                                    {fixed ? "✓ Fixed" : "✗ Failed"}
                                  </span>
                                </td>
                              </tr>
                            );
                          })}
                        </tbody>
                      </table>
                    </div>
                  </div>
                )}

                {/* Chart */}
                {summary.fixes?.length > 0 && (
                  <div className="acr-panel rounded-3xl p-6">
                    <div className="mb-6 flex items-center gap-2">
                      <Activity className="h-5 w-5 text-cyan-300" />
                      <h3 className="text-lg font-bold">
                        Vulnerability Distribution
                      </h3>
                    </div>

                    <div className="h-72 w-full">
                      <ResponsiveContainer width="100%" height="100%">
                        <BarChart data={getChartData()}>
                          <CartesianGrid
                            strokeDasharray="3 3"
                            vertical={false}
                            stroke="rgba(90,150,200,.12)"
                          />
                          <XAxis
                            dataKey="name"
                            tick={{
                              fill: "#64748b",
                              fontSize: 11,
                            }}
                            tickLine={false}
                            axisLine={false}
                          />
                          <YAxis
                            tick={{
                              fill: "#64748b",
                              fontSize: 11,
                            }}
                            tickLine={false}
                            axisLine={false}
                          />
                          <Tooltip
                            cursor={{
                              fill: "rgba(34,211,238,.04)",
                            }}
                            contentStyle={{
                              background: "#061225",
                              borderRadius: "12px",
                              border:
                                "1px solid rgba(34,211,238,.25)",
                              color: "#e2e8f0",
                            }}
                          />
                          <Bar
                            dataKey="count"
                            fill="#22d3ee"
                            radius={[5, 5, 0, 0]}
                          />
                        </BarChart>
                      </ResponsiveContainer>
                    </div>
                  </div>
                )}

                <button
                  onClick={downloadResults}
                  className="flex w-full items-center justify-center gap-2 rounded-xl bg-gradient-to-r from-cyan-500 to-blue-600 py-4 font-black text-white shadow-[0_0_35px_rgba(0,174,255,.2)] transition hover:shadow-[0_0_50px_rgba(0,174,255,.32)]"
                >
                  <Download className="h-5 w-5" />
                  DOWNLOAD RESULTS · JSON
                </button>
              </>
            ) : (
              <div className="acr-panel rounded-3xl border-red-400/20 p-8">
                <div className="flex items-center gap-3 text-red-300">
                  <ShieldCheck className="h-6 w-6" />
                  <h3 className="text-2xl font-bold">
                    Mission Failed
                  </h3>
                </div>

                <p className="mt-5 rounded-xl border border-red-400/15 bg-red-400/5 p-4 font-mono text-sm leading-6 text-red-200">
                  {errorMessage ||
                    "An unexpected error stopped the run."}
                </p>

                {isGeminiError && (
                  <p className="mt-3 text-xs text-amber-300">
                    Gemini issue detected. If this is a rate-limit or
                    availability problem, retry after a short wait.
                  </p>
                )}
              </div>
            )}
          </section>
        )}
      </main>

      <footer className="relative z-10 border-t border-cyan-400/10 bg-[#010713]/70 px-5 py-6 text-center text-[10px] font-semibold tracking-[0.18em] text-slate-600">
        ACR AGENT · AUTONOMOUS CODE RECOVERY · DEPLOYMENT FABRIC
      </footer>
    </div>
  );
}
