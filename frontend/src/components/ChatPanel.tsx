"use client";

import React, { useEffect, useRef } from "react";
import { Bot, User, Loader2, CheckCircle2, AlertTriangle } from "lucide-react";
import { useStore, ChatMessage } from "@/lib/store";

function MessageBubble({ msg }: { msg: ChatMessage }) {
  const isUser = msg.role === "user";

  // Render markdown-like bold and italic
  const formatContent = (text: string) => {
    return text.split(/(\*\*[^*]+\*\*|\*[^*]+\*)/g).map((part, i) => {
      if (part.startsWith("**") && part.endsWith("**"))
        return <strong key={i}>{part.slice(2, -2)}</strong>;
      if (part.startsWith("*") && part.endsWith("*"))
        return <em key={i}>{part.slice(1, -1)}</em>;
      return part;
    });
  };

  if (isUser) {
    return (
      <div className="flex justify-end mb-3">
        <div className="flex items-end gap-2 max-w-[85%]">
          <div className="bg-[#7c93c3] text-white text-xs rounded-2xl rounded-br-sm px-3.5 py-2.5 shadow-sm">
            {msg.content}
          </div>
          <div className="w-6 h-6 rounded-full bg-slate-200 flex items-center justify-center flex-shrink-0 mb-0.5">
            <User className="w-3.5 h-3.5 text-slate-500" />
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="flex justify-start mb-3">
      <div className="flex items-end gap-2 max-w-[90%]">
        <div className="w-6 h-6 rounded-full bg-[#7c93c3]/15 border border-[#7c93c3]/30 flex items-center justify-center flex-shrink-0 mb-0.5">
          <Bot className="w-3.5 h-3.5 text-[#7c93c3]" />
        </div>
        <div className="bg-white border border-slate-100 rounded-2xl rounded-bl-sm px-3.5 py-2.5 shadow-sm">
          {msg.isStreaming ? (
            <div className="flex items-center gap-2 text-slate-400 text-xs">
              <Loader2 className="w-3 h-3 animate-spin text-[#7c93c3]" />
              <span>{msg.content}</span>
              <span className="inline-flex gap-0.5">
                {[0,1,2].map(i => (
                  <span key={i} className="w-1 h-1 rounded-full bg-[#7c93c3] animate-bounce"
                    style={{ animationDelay: `${i * 0.15}s` }} />
                ))}
              </span>
            </div>
          ) : (
            <>
              <p className="text-xs text-slate-700 leading-relaxed whitespace-pre-line">
                {formatContent(msg.content)}
              </p>
              {msg.buildingSummary && (
                <div className="mt-2 pt-2 border-t border-slate-100 flex items-center gap-1.5 flex-wrap">
                  <span className="text-[10px] bg-slate-100 text-slate-600 px-2 py-0.5 rounded-full">
                    {msg.buildingSummary.floors}F {msg.buildingSummary.type}
                  </span>
                  {msg.buildingSummary.features.map(f => (
                    <span key={f} className="text-[10px] bg-blue-50 text-blue-600 px-2 py-0.5 rounded-full">{f}</span>
                  ))}
                  {msg.buildingSummary.compliant
                    ? <span className="text-[10px] bg-emerald-50 text-emerald-700 px-2 py-0.5 rounded-full flex items-center gap-0.5">
                        <CheckCircle2 className="w-2.5 h-2.5" />NBC ✓
                      </span>
                    : <span className="text-[10px] bg-rose-50 text-rose-600 px-2 py-0.5 rounded-full flex items-center gap-0.5">
                        <AlertTriangle className="w-2.5 h-2.5" />NBC ✗
                      </span>
                  }
                </div>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  );
}

export default function ChatPanel() {
  const chatMessages = useStore((s) => s.chatMessages);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [chatMessages]);

  return (
    <div className="flex flex-col flex-1 min-h-0 overflow-y-auto px-3 py-3 space-y-1">
      {chatMessages.map((msg) => (
        <MessageBubble key={msg.id} msg={msg} />
      ))}
      <div ref={bottomRef} />
    </div>
  );
}
