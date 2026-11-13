"use client";

import React, { useState } from "react";
import {
  ReactFlow,
  Controls,
  Background,
  BackgroundVariant,
  useNodesState,
  useEdgesState,
  Node,
  Edge,
} from "@xyflow/react";
import { Play, Pause, RotateCcw, Upload, FileCode, CheckCircle2, ShieldAlert } from "lucide-react";

const INITIAL_NODES: Node[] = [
  {
    id: "supervisor",
    type: "default",
    data: { label: "🛰️ Dynamic Supervisor" },
    position: { x: 300, y: 40 },
    style: {
      background: "#0f172a",
      color: "#38bdf8",
      border: "2px solid #38bdf8",
      borderRadius: "10px",
      fontWeight: "bold",
      padding: "12px 20px",
    },
  },
  {
    id: "worker-coder",
    type: "default",
    data: { label: "👨‍💻 Worker: Coder (DeepSeek)" },
    position: { x: 120, y: 180 },
    style: {
      background: "#0f172a",
      color: "#2dd4bf",
      border: "1px solid #2dd4bf",
      borderRadius: "8px",
      padding: "10px 16px",
    },
  },
  {
    id: "worker-tester",
    type: "default",
    data: { label: "🧪 Worker: Fast Tester (Groq)" },
    position: { x: 480, y: 180 },
    style: {
      background: "#0f172a",
      color: "#f59e0b",
      border: "1px solid #f59e0b",
      borderRadius: "8px",
      padding: "10px 16px",
    },
  },
];

const INITIAL_EDGES: Edge[] = [
  {
    id: "e1-2",
    source: "supervisor",
    target: "worker-coder",
    animated: true,
    style: { stroke: "#38bdf8", strokeWidth: 2 },
  },
  {
    id: "e1-3",
    source: "supervisor",
    target: "worker-tester",
    animated: true,
    style: { stroke: "#38bdf8", strokeWidth: 2 },
  },
];

const SAMPLE_TIMELINE = [
  {
    step: 1,
    time: "00:01",
    actor: "supervisor",
    event: "PLAN_DRAFTED",
    details: "Decomposed goal into 2 parallel contracts: Coder & Fast Tester.",
  },
  {
    step: 2,
    time: "00:04",
    actor: "worker-coder",
    event: "LOCK_ACQUIRED",
    details: "Acquired exclusive write lock on src/engine/patcher.py.",
  },
  {
    step: 3,
    time: "00:09",
    actor: "worker-coder",
    event: "DIFF_APPLIED",
    details: "Applied atomic unified diff patch to patcher.py.",
  },
  {
    step: 4,
    time: "00:14",
    actor: "worker-tester",
    event: "TESTS_PASSED",
    details: "Pytest passed with 100% assertions green in sandbox container.",
  },
  {
    step: 5,
    time: "00:18",
    actor: "supervisor",
    event: "ORBIT_COMPLETED",
    details: "All contracts reconciled cleanly. Task complete.",
  },
];

export default function ReplayerPage() {
  const [nodes] = useNodesState(INITIAL_NODES);
  const [edges] = useEdgesState(INITIAL_EDGES);
  const [currentStep, setCurrentStep] = useState(0);
  const [isPlaying, setIsPlaying] = useState(false);

  const activeEvent = SAMPLE_TIMELINE[currentStep];

  return (
    <main className="flex flex-col h-screen w-screen overflow-hidden bg-slate-950 text-slate-100">
      {/* Top Navigation Bar */}
      <header className="flex items-center justify-between px-6 py-4 border-b border-slate-800 bg-slate-900/60 backdrop-blur-md">
        <div className="flex items-center gap-3">
          <span className="text-2xl">🛰️</span>
          <div>
            <h1 className="text-lg font-bold tracking-tight text-slate-100">
              KEPLIX <span className="text-cyan-400 font-mono text-sm font-normal">REPLAYER</span>
            </h1>
            <p className="text-xs text-slate-400 font-mono">Multi-Agent Swarm Orbit Visualizer</p>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <label className="flex items-center gap-2 px-3 py-1.5 rounded-lg border border-slate-700 bg-slate-800/80 hover:bg-slate-700 text-xs font-medium cursor-pointer transition">
            <Upload size={14} className="text-cyan-400" />
            <span>Load trace.json</span>
            <input type="file" accept=".json" className="hidden" />
          </label>
          <div className="flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-emerald-950/70 border border-emerald-800/60 text-emerald-400 text-xs font-mono">
            <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse"></span>
            ORBIT READY
          </div>
        </div>
      </header>

      {/* Main Workspace Layout */}
      <div className="flex flex-1 overflow-hidden">
        {/* React Flow Canvas */}
        <div className="flex-1 h-full relative">
          <ReactFlow nodes={nodes} edges={edges} fitView>
            <Background variant={BackgroundVariant.Dots} gap={20} size={1} color="#334155" />
            <Controls className="bg-slate-900 border border-slate-800 text-slate-300" />
          </ReactFlow>

          {/* Floating Orbit Overlay */}
          <div className="absolute top-4 left-4 bg-slate-900/90 border border-slate-800 rounded-xl p-3 shadow-xl backdrop-blur-md max-w-sm pointer-events-none">
            <div className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-1 font-mono">
              Active Orbit Spec
            </div>
            <div className="text-sm font-medium text-slate-200">
              Build a fast AST-driven search-and-replace patch engine
            </div>
          </div>
        </div>

        {/* Right Event Inspector Panel */}
        <aside className="w-96 border-l border-slate-800 bg-slate-900/40 p-5 flex flex-col justify-between overflow-y-auto">
          <div>
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-sm font-semibold tracking-wide uppercase text-slate-300 font-mono">
                Trace Inspector
              </h2>
              <span className="text-xs text-cyan-400 font-mono">
                Step {currentStep + 1} of {SAMPLE_TIMELINE.length}
              </span>
            </div>

            {activeEvent && (
              <div className="space-y-4">
                <div className="p-4 rounded-xl border border-slate-800 bg-slate-900/80 space-y-2">
                  <div className="flex items-center justify-between text-xs text-slate-400 font-mono">
                    <span>{activeEvent.time}</span>
                    <span className="px-2 py-0.5 rounded bg-cyan-950 text-cyan-400 border border-cyan-800/40">
                      {activeEvent.actor}
                    </span>
                  </div>
                  <div className="text-sm font-bold text-slate-100 flex items-center gap-2">
                    <CheckCircle2 size={16} className="text-emerald-400" />
                    {activeEvent.event}
                  </div>
                  <p className="text-xs text-slate-300 leading-relaxed">
                    {activeEvent.details}
                  </p>
                </div>

                <div className="p-4 rounded-xl border border-slate-800 bg-slate-950/60 font-mono text-xs text-slate-400 space-y-2">
                  <div className="flex items-center gap-2 text-slate-300 font-semibold">
                    <FileCode size={14} className="text-cyan-400" />
                    <span>Contract Blackboard</span>
                  </div>
                  <div className="text-[11px] text-slate-400 leading-snug">
                    • Subgraph locks: <span className="text-emerald-400">clean</span><br />
                    • Git commit: <span className="text-slate-300">b4a72d1</span><br />
                    • Budget consumed: <span className="text-amber-400">$0.04</span>
                  </div>
                </div>
              </div>
            )}
          </div>

          <div className="text-xs text-slate-500 font-mono flex items-center gap-1 mt-6">
            <ShieldAlert size={14} className="text-slate-500" />
            <span>Telemetry verified & zero secrets exposed</span>
          </div>
        </aside>
      </div>

      {/* Bottom Timeline Controls */}
      <footer className="border-t border-slate-800 bg-slate-900/90 px-6 py-3 flex items-center justify-between backdrop-blur-md">
        <div className="flex items-center gap-2">
          <button
            onClick={() => setIsPlaying(!isPlaying)}
            className="p-2 rounded-lg bg-cyan-500 hover:bg-cyan-400 text-slate-950 transition font-bold"
          >
            {isPlaying ? <Pause size={16} /> : <Play size={16} />}
          </button>
          <button
            onClick={() => setCurrentStep(0)}
            className="p-2 rounded-lg border border-slate-700 bg-slate-800 hover:bg-slate-700 text-slate-300 transition"
          >
            <RotateCcw size={16} />
          </button>
          <span className="text-xs font-mono text-slate-400 ml-2">
            Playback Scrubbing
          </span>
        </div>

        <div className="flex-1 max-w-xl mx-8">
          <input
            type="range"
            min={0}
            max={SAMPLE_TIMELINE.length - 1}
            value={currentStep}
            onChange={(e) => setCurrentStep(Number(e.target.value))}
            className="w-full h-1.5 bg-slate-700 rounded-lg appearance-none cursor-pointer accent-cyan-400"
          />
        </div>

        <div className="text-xs font-mono text-slate-400">
          Target Orbit: <span className="text-slate-200">v0.1.0-alpha</span>
        </div>
      </footer>
    </main>
  );
}

