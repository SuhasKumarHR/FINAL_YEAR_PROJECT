"use client";

import { useState, FormEvent, useRef, useEffect } from "react";
import gsap from "gsap";
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from "recharts";
import { Terminal, CheckCircle2, GitPullRequest, Settings, Loader2 } from "lucide-react";

type LogEntry = { id: string; message: string; type: "info" | "success" | "error" | "warning" };
type FixEntry = { bug_type: string; file_path: string };
type SummaryData = { status: string; total_time: number; pr_link: string; branch: string; fixes: FixEntry[] };

export default function Home() {
  const [repoUrl, setRepoUrl] = useState("");
  const [teamName, setTeamName] = useState("");
  const [teamLeader, setTeamLeader] = useState("");
  
  // App State
  const [status, setStatus] = useState<"idle" | "running" | "completed">("idle");
  const [currentStage, setCurrentStage] = useState<string>("Initializing...");
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [summary, setSummary] = useState<SummaryData | null>(null);
  
  // Timer State
  const [elapsedSeconds, setElapsedSeconds] = useState(0);

  const logsEndRef = useRef<HTMLDivElement>(null);
  const logContainerRef = useRef<HTMLDivElement>(null);

  // Timer logic
  useEffect(() => {
    let interval: NodeJS.Timeout;
    if (status === "running") {
      interval = setInterval(() => setElapsedSeconds((prev) => prev + 1), 1000);
    }
    return () => clearInterval(interval);
  }, [status]);

  // GSAP Animation for new logs
  useEffect(() => {
    if (logContainerRef.current && logs.length > 0) {
      const lastElement = logContainerRef.current.lastElementChild;
      if (lastElement) {
        gsap.fromTo(lastElement, { opacity: 0, x: -10 }, { opacity: 1, x: 0, duration: 0.3 });
      }
      // Auto-scroll to bottom
      logsEndRef.current?.scrollIntoView({ behavior: "smooth" });
    }
  }, [logs]);

  const formatTime = (seconds: number) => {
    const m = Math.floor(seconds / 60).toString().padStart(2, "0");
    const s = (seconds % 60).toString().padStart(2, "0");
    return `${m}:${s}`;
  };

  const addLog = (message: string, type: LogEntry["type"], stage?: string) => {
    setLogs((prev) => [...prev, { id: Math.random().toString(36).substring(7), message, type }]);
    if (stage) setCurrentStage(stage);
  };

  // MOCK BACKEND EXECUTION
  const runMockBackend = () => {
    // Stage 1: Prep
    setTimeout(() => addLog("🚀 [SYSTEM START] Initializing Autonomous DevOps Agent...", "info", "Starting up"), 500);
    setTimeout(() => addLog("Cloning repository and preparing environment...", "info", "Stage 1: Prep"), 1500);
    setTimeout(() => addLog("Environment detected: Node.js (Next.js config found)", "info"), 2500);
    
    // Stage 2: Analysis & Healing (Iteration 1)
    setTimeout(() => addLog("🔄 Iteration 1/5 starting...", "info", "Stage 2: Analysis"), 4000);
    setTimeout(() => addLog("Running static code analysis...", "info"), 5000);
    setTimeout(() => addLog("⚠️ Failures detected: UnhandledPromiseRejection in src/api/route.ts", "warning"), 6500);
    setTimeout(() => addLog("⚠️ Failures detected: Missing dependency 'cors' in package.json", "warning"), 7000);
    
    setTimeout(() => addLog("Deploying Healing Agent...", "info", "Stage 3: Healing"), 8500);
    setTimeout(() => addLog("⚡ Applied fix for UnhandledPromiseRejection (added try/catch block)", "success"), 10500);
    setTimeout(() => addLog("⚡ Applied fix for Missing dependency (updated package.json)", "success"), 11500);

    // Stage 2: Analysis (Iteration 2 - Verify)
    setTimeout(() => addLog("🔄 Iteration 2/5 starting...", "info", "Verifying fixes"), 13000);
    setTimeout(() => addLog("✅ All checks passed! Repository is clean.", "success"), 14500);

    // Stage 4: Git Ops
    setTimeout(() => addLog("📦 Committing changes and pushing to remote...", "info", "Stage 4: Git Ops"), 16000);
    setTimeout(() => addLog("🎉 PR Created: https://github.com/demo/repo/pull/42", "success", "Finalizing"), 18000);

    // Complete Simulation
    setTimeout(() => {
      setStatus("completed");
      setSummary({
        status: "SUCCESS",
        total_time: 18,
        pr_link: "https://github.com/demo/repo/pull/42",
        branch: "agent-fix-branch",
        fixes: [
          { bug_type: "Unhandled Promise", file_path: "src/api/route.ts" },
          { bug_type: "Missing Dependency", file_path: "package.json" },
          { bug_type: "Missing Dependency", file_path: "package-lock.json" },
          { bug_type: "Type Error", file_path: "src/components/Button.tsx" }
        ]
      });
    }, 19000);
  };

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault();
    if (!repoUrl.trim() || !teamName.trim() || !teamLeader.trim()) return;

    setStatus("running");
    setLogs([]);
    setElapsedSeconds(0);
    setSummary(null);

    // Trigger our mock sequence instead of real sockets
    runMockBackend();
  };

  // Helper to aggregate data for Recharts
  const getChartData = () => {
    if (!summary?.fixes) return [];
    const counts: Record<string, number> = {};
    summary.fixes.forEach(f => { counts[f.bug_type] = (counts[f.bug_type] || 0) + 1; });
    return Object.keys(counts).map(key => ({ name: key, count: counts[key] }));
  };

  return (
    <div className="min-h-screen bg-white text-black font-mono selection:bg-black selection:text-white pb-20">
      {/* Header & Timer */}
      <header className="fixed top-0 left-0 right-0 border-b border-zinc-200 bg-white/80 backdrop-blur-md z-50 px-6 py-4 flex justify-between items-center">
        <div className="flex items-center gap-2 font-bold tracking-tighter text-lg">
          <Settings className="w-5 h-5" />
          <span>RIFT_AGENT</span>
        </div>
        {(status === "running" || status === "completed") && (
          <div className="flex items-center gap-2 font-mono text-sm bg-zinc-100 px-3 py-1 rounded-full border border-zinc-200">
            {status === "running" ? <Loader2 className="w-4 h-4 animate-spin" /> : <CheckCircle2 className="w-4 h-4" />}
            <span>{formatTime(elapsedSeconds)}</span>
          </div>
        )}
      </header>

      <main className="max-w-4xl mx-auto pt-24 px-6">
        {status === "idle" && (
          <div className="max-w-md mx-auto mt-20">
            <h1 className="text-3xl font-bold tracking-tight mb-2">Initialize Agent</h1>
            <p className="text-zinc-500 mb-8 text-sm">Deploy the autonomous healing agent to your repository.</p>
            
            <form onSubmit={handleSubmit} className="space-y-4">
              <input value={repoUrl} onChange={(e) => setRepoUrl(e.target.value)} placeholder="https://github.com/username/repository" className="w-full px-4 py-3 bg-zinc-50 border border-zinc-200 rounded-lg text-black placeholder-zinc-400 focus:outline-none focus:ring-2 focus:ring-black focus:border-transparent transition-all" required />
              <input value={teamName} onChange={(e) => setTeamName(e.target.value)} placeholder="Team Name (e.g. RIFT ORGANISERS)" className="w-full px-4 py-3 bg-zinc-50 border border-zinc-200 rounded-lg text-black placeholder-zinc-400 focus:outline-none focus:ring-2 focus:ring-black focus:border-transparent transition-all" required />
              <input value={teamLeader} onChange={(e) => setTeamLeader(e.target.value)} placeholder="Team Leader Name" className="w-full px-4 py-3 bg-zinc-50 border border-zinc-200 rounded-lg text-black placeholder-zinc-400 focus:outline-none focus:ring-2 focus:ring-black focus:border-transparent transition-all" required />
              
              <button type="submit" className="w-full bg-black text-white py-3 rounded-lg font-medium hover:bg-zinc-800 transition-colors mt-4">
                Deploy Agent
              </button>
            </form>
          </div>
        )}

        {status === "running" && (
          <div className="space-y-6 mt-10">
            <div className="flex items-center gap-3 text-lg font-medium border-b border-zinc-200 pb-4">
              <Loader2 className="w-5 h-5 animate-spin" />
              <span>{currentStage}</span>
            </div>
            
            {/* Terminal Window */}
            <div className="bg-[#0a0a0a] rounded-xl p-4 overflow-hidden border border-zinc-800 shadow-2xl relative h-[500px] flex flex-col">
              <div className="flex gap-2 mb-4 absolute top-4 left-4">
                <div className="w-3 h-3 rounded-full bg-zinc-700"></div>
                <div className="w-3 h-3 rounded-full bg-zinc-700"></div>
                <div className="w-3 h-3 rounded-full bg-zinc-700"></div>
              </div>
              <div ref={logContainerRef} className="flex-1 overflow-y-auto mt-8 text-sm font-mono space-y-2 pr-2 custom-scrollbar">
                {logs.map((log) => (
                  <div key={log.id} className={`${log.type === "error" ? "text-red-400" : log.type === "success" ? "text-green-400" : log.type === "warning" ? "text-yellow-400" : "text-zinc-300"}`}>
                    <span className="text-zinc-600 mr-2">[{new Date().toLocaleTimeString()}]</span>
                    {log.message}
                  </div>
                ))}
                <div ref={logsEndRef} />
              </div>
            </div>
          </div>
        )}

        {status === "completed" && summary && (
          <div className="mt-10 space-y-8 animate-in fade-in duration-700">
            <h2 className="text-3xl font-bold tracking-tight">Mission Report</h2>
            
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div className="p-6 border border-zinc-200 rounded-xl bg-zinc-50">
                <div className="text-zinc-500 text-sm mb-1">Status</div>
                <div className="text-2xl font-bold flex items-center gap-2">
                  <CheckCircle2 className="w-6 h-6 text-black" /> {summary.status}
                </div>
              </div>
              <div className="p-6 border border-zinc-200 rounded-xl bg-zinc-50">
                <div className="text-zinc-500 text-sm mb-1">Total Fixes Applied</div>
                <div className="text-2xl font-bold">{summary.fixes?.length || 0}</div>
              </div>
              <div className="p-6 border border-zinc-200 rounded-xl bg-zinc-50">
                <div className="text-zinc-500 text-sm mb-1">Pull Request</div>
                <a href={summary.pr_link} target="_blank" rel="noreferrer" className="text-lg font-bold flex items-center gap-2 hover:underline">
                  <GitPullRequest className="w-5 h-5" /> View on GitHub
                </a>
              </div>
            </div>

            {summary.fixes && summary.fixes.length > 0 && (
              <div className="border border-zinc-200 rounded-xl p-6 bg-white">
                <h3 className="font-bold text-lg mb-6 flex items-center gap-2">
                  <Terminal className="w-5 h-5" /> Vulnerability Distribution
                </h3>
                <div className="h-64 w-full">
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={getChartData()}>
                      <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#e4e4e7" />
                      <XAxis dataKey="name" tick={{ fill: '#71717a', fontSize: 12 }} tickLine={false} axisLine={false} />
                      <YAxis tick={{ fill: '#71717a', fontSize: 12 }} tickLine={false} axisLine={false} />
                      <Tooltip cursor={{ fill: '#f4f4f5' }} contentStyle={{ backgroundColor: '#fff', borderRadius: '8px', border: '1px solid #e4e4e7' }} />
                      <Bar dataKey="count" fill="#000000" radius={[4, 4, 0, 0]} />
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              </div>
            )}
            
            <button onClick={() => setStatus("idle")} className="w-full bg-zinc-100 text-black border border-zinc-200 py-3 rounded-lg font-medium hover:bg-zinc-200 transition-colors">
              Run Another Analysis
            </button>
          </div>
        )}
      </main>
    </div>
  );
}