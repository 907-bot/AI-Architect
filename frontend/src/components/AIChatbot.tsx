"use client";
import React, { useState, useRef, useEffect, useCallback } from "react";
import { useStore } from "@/lib/store";
import { API_BASE } from "@/lib/mvpScene";
import {
  Send, Bot, User, Loader2, ImageIcon,
  RefreshCw, Lightbulb, Building2, Ruler, CheckCircle, AlertTriangle, X
} from "lucide-react";

interface ImageResult { url: string; title: string; thumb?: string; }
interface ToolResult {
  type: "images"|"edit"|"feasibility"|"suggestion"|"info"|"text";
  text?: string; images?: ImageResult[];
  feasible?: boolean; metrics?: any; issues?: string[]; suggestions?: string[];
  schema?: any; element?: string; value?: string;
}
interface Message {
  id: string; role: "user"|"assistant"; content: string;
  toolResults?: ToolResult[]; isStreaming?: boolean;
}

const SUGGESTIONS = [
  "What types of German roofs exist?",
  "Replace the roof with a mansard style",
  "My plot is 400 sq metres — what can I build?",
  "Show me Japanese interior styles",
  "Make the living room larger",
  "Change wall color to sage green",
  "Add a swimming pool on the left",
  "What are NBC setback rules for apartments?",
];

export default function AIChatbot() {
  const [messages, setMessages]     = useState<Message[]>([{
    id: "welcome", role: "assistant",
    content: "Hi! I'm your AI architect. I can answer questions about architectural styles with images, edit your building, check if your design fits your plot, and suggest optimal designs. What would you like to do?",
  }]);
  const [input, setInput]           = useState("");
  const [loading, setLoading]       = useState(false);
  const [apiKeyMissing, setApiKeyMissing] = useState(false);
  const bottomRef  = useRef<HTMLDivElement>(null);
  const inputRef   = useRef<HTMLInputElement>(null);

  const generatedGlbPath = useStore(s => s.generatedGlbPath);
  const geometryData     = useStore(s => s.geometryData);
  const setGeneratedGlbPath = useStore(s => s.setGeneratedGlbPath);
  const setIsGenerating  = useStore(s => s.setIsGenerating);
  const addChatMessage   = useStore(s => s.addChatMessage);
  const plotLat          = useStore(s => s.plotLat);
  const plotLng          = useStore(s => s.plotLng);
  const plotWidth        = useStore(s => s.plotWidth);
  const plotDepth        = useStore(s => s.plotDepth);

  const currentSchema = (geometryData as any)?.schema || {};

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const addMsg = (msg: Omit<Message,"id">) => {
    const id = `${msg.role}-${Date.now()}-${Math.random().toString(36).slice(2)}`;
    setMessages(prev => [...prev, { ...msg, id }]);
    return id;
  };

  const updateMsg = (id: string, updates: Partial<Message>) => {
    setMessages(prev => prev.map(m => m.id === id ? { ...m, ...updates } : m));
  };

  const triggerRegenerate = useCallback(async (schema: any) => {
    setIsGenerating(true);
    try {
      const resp = await fetch(`${API_BASE}/api/generate`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ prompt: "", style: schema.style, ...schema }),
      });
      const data = await resp.json();
      if (data.glb_path || data.model_path) {
        setGeneratedGlbPath(data.glb_path || data.model_path);
      }
    } catch (e) { console.error("Regen error:", e); }
    setIsGenerating(false);
  }, [setIsGenerating, setGeneratedGlbPath]);

  const sendMessage = async (text?: string) => {
    const msg = (text || input).trim();
    if (!msg || loading) return;
    setInput("");
    setLoading(true);

    addMsg({ role: "user", content: msg });
    const asstId = addMsg({ role: "assistant", content: "", isStreaming: true });

    const history = messages.slice(-8).map(m => ({
      role: m.role, content: m.content,
    }));

    try {
      const resp = await fetch(`${API_BASE}/api/ai-chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          message: msg,
          history,
          current_schema: currentSchema,
          plot_sqm: plotWidth * plotDepth || null,
          lat: plotLat, lng: plotLng,
        }),
      });

      if (!resp.ok || !resp.body) throw new Error(`HTTP ${resp.status}`);

      const reader = resp.body.getReader();
      const decoder = new TextDecoder();
      let textBuffer = "";
      let toolResults: ToolResult[] = [];

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        const chunk = decoder.decode(value);
        const lines = chunk.split("\n");

        for (const line of lines) {
          if (!line.startsWith("data: ")) continue;
          try {
            const ev = JSON.parse(line.slice(6));

            if (ev.type === "text_chunk") {
              textBuffer += ev.text;
              updateMsg(asstId, { content: textBuffer, isStreaming: true });
            } else if (ev.type === "tool_start") {
              updateMsg(asstId, {
                content: textBuffer || `Using ${ev.tool.replace(/_/g," ")}…`,
                isStreaming: true
              });
            } else if (ev.type === "tool_result") {
              toolResults = [...toolResults, ev.result];
              updateMsg(asstId, { content: textBuffer, toolResults, isStreaming: true });
            } else if (ev.type === "regenerate" && ev.schema) {
              updateMsg(asstId, {
                content: textBuffer,
                toolResults,
                isStreaming: true,
              });
              // Trigger building regeneration
              await triggerRegenerate(ev.schema);
            } else if (ev.type === "error") {
              if (ev.text?.includes("OPENAI_API_KEY")) setApiKeyMissing(true);
              textBuffer = ev.text;
              updateMsg(asstId, { content: textBuffer, isStreaming: false });
            } else if (ev.type === "done") {
              updateMsg(asstId, { content: textBuffer, toolResults, isStreaming: false });
            }
          } catch { /* skip malformed */ }
        }
      }
    } catch (err) {
      updateMsg(asstId, {
        content: "Connection error. Make sure the backend is running.",
        isStreaming: false
      });
    }
    setLoading(false);
    inputRef.current?.focus();
  };

  return (
    <div className="flex flex-col h-full bg-[#f8f9fb]">
      {/* API key warning */}
      {apiKeyMissing && (
        <div className="mx-3 mt-3 bg-amber-50 border border-amber-200 rounded-xl p-3 flex items-start gap-2">
          <AlertTriangle className="w-4 h-4 text-amber-500 flex-shrink-0 mt-0.5" />
          <div>
            <p className="text-[10px] font-bold text-amber-700">OpenAI API key not set</p>
            <p className="text-[9px] text-amber-600">Add <code className="bg-amber-100 px-1 rounded">OPENAI_API_KEY=sk-...</code> to your <code className="bg-amber-100 px-1 rounded">.env</code> file and restart the backend.</p>
          </div>
          <button onClick={() => setApiKeyMissing(false)} className="ml-auto"><X className="w-3 h-3 text-amber-400" /></button>
        </div>
      )}

      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-3 space-y-3">
        {messages.map(msg => (
          <div key={msg.id} className={`flex gap-2 ${msg.role==="user"?"justify-end":"justify-start"}`}>
            {msg.role === "assistant" && (
              <div className="w-6 h-6 rounded-full bg-[#7c93c3]/15 border border-[#7c93c3]/30 flex items-center justify-center flex-shrink-0 mt-0.5">
                <Bot className="w-3.5 h-3.5 text-[#7c93c3]" />
              </div>
            )}
            <div className={`max-w-[85%] space-y-2 ${msg.role==="user"?"items-end flex flex-col":""}`}>
              {/* Text bubble */}
              {(msg.content || msg.isStreaming) && (
                <div className={`rounded-2xl px-3.5 py-2.5 text-xs shadow-sm ${
                  msg.role==="user"
                    ? "bg-[#7c93c3] text-white rounded-br-sm"
                    : "bg-white border border-slate-100 text-slate-700 rounded-bl-sm"
                }`}>
                  {msg.isStreaming && !msg.content ? (
                    <div className="flex items-center gap-1.5 text-slate-400">
                      <Loader2 className="w-3 h-3 animate-spin text-[#7c93c3]" />
                      <span className="text-[10px]">Thinking…</span>
                    </div>
                  ) : (
                    <p className="whitespace-pre-line leading-relaxed">
                      {msg.content.split(/(\*\*[^*]+\*\*)/g).map((p,i) =>
                        p.startsWith("**") ? <strong key={i}>{p.slice(2,-2)}</strong> : p
                      )}
                    </p>
                  )}
                </div>
              )}

              {/* Tool results */}
              {msg.toolResults?.map((tr, ti) => (
                <div key={ti} className="w-full">
                  {tr.type === "images" && tr.images && (
                    <div className="bg-white rounded-xl border border-slate-100 p-2 shadow-sm">
                      <p className="text-[9px] font-bold text-slate-400 uppercase mb-2 px-1">
                        <ImageIcon className="w-3 h-3 inline mr-1" />
                        {tr.images.length} results
                      </p>
                      <div className="grid grid-cols-2 gap-1.5">
                        {tr.images.map((img, ii) => (
                          <div key={ii} className="relative group cursor-pointer"
                            onClick={() => window.open(img.url,"_blank")}>
                            <img src={img.thumb||img.url} alt={img.title}
                              className="w-full h-24 object-cover rounded-lg border border-slate-100 group-hover:opacity-90 transition"
                              onError={e => { (e.target as HTMLImageElement).src = `https://via.placeholder.com/200x120?text=${encodeURIComponent(img.title)}`; }}
                            />
                            <div className="absolute inset-x-0 bottom-0 bg-gradient-to-t from-black/60 to-transparent rounded-b-lg p-1.5 opacity-0 group-hover:opacity-100 transition">
                              <p className="text-white text-[8px] truncate">{img.title}</p>
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {tr.type === "edit" && (
                    <div className="bg-emerald-50 border border-emerald-200 rounded-xl px-3 py-2 flex items-center gap-2">
                      <CheckCircle className="w-3.5 h-3.5 text-emerald-500 flex-shrink-0" />
                      <div>
                        <p className="text-[10px] font-bold text-emerald-700">Building updated</p>
                        <p className="text-[9px] text-emerald-600">{tr.text}</p>
                      </div>
                      <div className="ml-auto animate-spin">
                        <RefreshCw className="w-3 h-3 text-emerald-400" />
                      </div>
                    </div>
                  )}

                  {tr.type === "feasibility" && (
                    <div className={`rounded-xl border p-3 ${tr.feasible ? "bg-emerald-50 border-emerald-200" : "bg-amber-50 border-amber-200"}`}>
                      <div className="flex items-center gap-2 mb-2">
                        {tr.feasible
                          ? <CheckCircle className="w-4 h-4 text-emerald-500" />
                          : <AlertTriangle className="w-4 h-4 text-amber-500" />}
                        <span className={`text-[10px] font-bold ${tr.feasible?"text-emerald-700":"text-amber-700"}`}>
                          {tr.feasible ? "Plot Feasible ✓" : "Needs Adjustment"}
                        </span>
                      </div>
                      {tr.metrics && (
                        <div className="grid grid-cols-3 gap-1 mb-2">
                          {[
                            ["Coverage", `${tr.metrics.coverage_pct}%`, `/${tr.metrics.cov_limit}%`],
                            ["FAR",      `${tr.metrics.far_actual}`,   `/${tr.metrics.far_limit}`],
                            ["Footprint",`${tr.metrics.footprint_sqm}m²`, ""],
                          ].map(([k,v,l]) => (
                            <div key={k} className="bg-white/70 rounded-lg p-1.5 text-center">
                              <p className="text-[8px] text-slate-400">{k}</p>
                              <p className="text-[9px] font-bold text-slate-700">{v}<span className="text-slate-400 font-normal">{l}</span></p>
                            </div>
                          ))}
                        </div>
                      )}
                      {tr.suggestions?.map((s,i) => (
                        <button key={i} onClick={() => sendMessage(s)}
                          className="text-[9px] text-amber-600 underline block hover:text-amber-800 transition">
                          → {s}
                        </button>
                      ))}
                    </div>
                  )}

                  {tr.type === "suggestion" && (
                    <div className="bg-[#7c93c3]/10 border border-[#7c93c3]/20 rounded-xl p-3">
                      <div className="flex items-center gap-2 mb-2">
                        <Building2 className="w-4 h-4 text-[#7c93c3]" />
                        <span className="text-[10px] font-bold text-[#5a73a3]">Recommended Design</span>
                      </div>
                      <p className="text-[9px] text-slate-600 whitespace-pre-line mb-2">{tr.text}</p>
                      {tr.schema && (
                        <button onClick={() => triggerRegenerate(tr.schema!)}
                          className="w-full py-1.5 bg-[#7c93c3] hover:bg-[#8da3d3] text-white text-[9px] font-bold rounded-lg transition">
                          Generate this design →
                        </button>
                      )}
                    </div>
                  )}
                </div>
              ))}
            </div>
            {msg.role === "user" && (
              <div className="w-6 h-6 rounded-full bg-slate-200 flex items-center justify-center flex-shrink-0 mt-0.5">
                <User className="w-3.5 h-3.5 text-slate-500" />
              </div>
            )}
          </div>
        ))}
        <div ref={bottomRef} />
      </div>

      {/* Quick suggestions */}
      <div className="px-3 py-1.5 flex gap-1.5 overflow-x-auto scrollbar-hide">
        {SUGGESTIONS.slice(0,4).map(s => (
          <button key={s} onClick={() => sendMessage(s)}
            className="flex-shrink-0 text-[8px] bg-white border border-slate-200 hover:border-[#7c93c3] text-slate-600 hover:text-[#7c93c3] rounded-full px-2.5 py-1 transition whitespace-nowrap">
            {s}
          </button>
        ))}
      </div>

      {/* Input */}
      <div className="p-3 pt-1.5 border-t border-slate-200 bg-white">
        <div className="flex gap-2 items-center bg-slate-50 rounded-xl border border-slate-200 focus-within:border-[#7c93c3] focus-within:bg-white transition px-3 py-2">
          <Lightbulb className="w-3.5 h-3.5 text-slate-300 flex-shrink-0" />
          <input ref={inputRef} value={input}
            onChange={e => setInput(e.target.value)}
            onKeyDown={e => e.key === "Enter" && !e.shiftKey && sendMessage()}
            placeholder="Ask about styles, edit the building, check plot feasibility…"
            className="flex-1 bg-transparent text-xs text-slate-700 placeholder-slate-400 outline-none" />
          <button onClick={() => sendMessage()} disabled={!input.trim() || loading}
            className={`w-7 h-7 rounded-lg flex items-center justify-center transition ${
              input.trim() && !loading
                ? "bg-[#7c93c3] hover:bg-[#8da3d3] text-white"
                : "bg-slate-100 text-slate-300 cursor-not-allowed"
            }`}>
            {loading ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Send className="w-3.5 h-3.5" />}
          </button>
        </div>
      </div>
    </div>
  );
}
