"use client";

import React, { useEffect, useRef } from "react";
import { Terminal, Shield, Cpu, Activity, Info } from "lucide-react";
import { useStore } from "@/lib/store";

export default function AgentConsole() {
  const agentLogs = useStore((state) => state.agentLogs);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [agentLogs]);

  // Helper to format metadata payload safely
  const formatPayload = (data: any) => {
    if (!data) return null;
    return (
      <pre className="mt-2 text-[11px] font-mono bg-slate-50 p-2.5 rounded border border-slate-100 text-emerald-700/90 overflow-x-auto max-h-48 whitespace-pre-wrap">
        {JSON.stringify(data, null, 2)}
      </pre>
    );
  };

  const getAgentIcon = (agent: string) => {
    const lower = agent.toLowerCase();
    if (lower === "orchestrator") return <Cpu className="w-4 h-4 text-indigo-500" />;
    if (lower === "skeptic" || lower === "compliance") return <Shield className="w-4 h-4 text-rose-500" />;
    if (lower === "bull" || lower === "bear") return <Activity className="w-4 h-4 text-amber-500" />;
    return <Terminal className="w-4 h-4 text-slate-500" />;
  };

  return (
    <div className="flex flex-col h-full glass-panel rounded-xl overflow-hidden">
      <div className="flex items-center gap-2 px-4 py-3 border-b border-slate-100 bg-slate-50/50">
        <Terminal className="w-4 h-4 text-slate-600" />
        <h2 className="text-sm font-semibold tracking-wide text-slate-800 font-outfit uppercase">
          AI Multi-Agent Console
        </h2>
      </div>

      <div className="flex-1 overflow-y-auto p-4 space-y-4 max-h-[400px] md:max-h-none">
        {agentLogs.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full text-slate-400 py-12">
            <Info className="w-8 h-8 mb-2 stroke-[1.5]" />
            <p className="text-xs">No active agent workflows running.</p>
            <p className="text-[10px] mt-1 text-slate-500">Enter a prompt to spin up the agents.</p>
          </div>
        ) : (
          (agentLogs || []).map((log, index) => (
            <div 
              key={index} 
              className="p-3 rounded-lg bg-slate-50/30 border border-slate-100 animate-fadeIn"
            >
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  {getAgentIcon(log.agent)}
                  <span className="text-xs font-semibold capitalize text-slate-700">
                    {log.agent}
                  </span>
                </div>
                <span className="text-[10px] text-slate-400 font-mono">
                  {new Date().toLocaleTimeString()}
                </span>
              </div>
              <p className="text-xs text-slate-600 mt-1.5 leading-relaxed">
                {log.message}
              </p>
              {formatPayload(log.data)}
            </div>
          ))
        )}
        <div ref={bottomRef} />
      </div>
    </div>
  );
}
