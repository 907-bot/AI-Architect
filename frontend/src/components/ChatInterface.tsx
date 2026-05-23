"use client";
import React, { useState } from "react";
import { MessageSquare, Send, Bot, User, X } from "lucide-react";

interface Message {
  id: number;
  role: "user" | "assistant";
  content: string;
  options?: string[];
}

export default function ChatInterface({ onSend }: { onSend: (prompt: string) => void }) {
  const [messages, setMessages] = useState<Message[]>([
    { id: 1, role: "assistant", content: "Hi! I'm your AI architect. Tell me what kind of building you'd like - I can help you choose colors, materials, floors, and features naturally!", options: undefined }
  ]);
  const [input, setInput] = useState("");
  const [isOpen, setIsOpen] = useState(true);

  const quickOptions = [
    "Modern white villa with pool",
    "Red brick house with garage",  
    "Cream apartment with balcony",
    "Dark minimalist with garden"
  ];

  const handleOption = (opt: string) => {
    const newMsg: Message = { id: messages.length + 1, role: "user", content: opt };
    setMessages([...messages, newMsg]);
    onSend(opt);
  };

  const handleSend = () => {
    if (!input.trim()) return;
    const newMsg: Message = { id: messages.length + 1, role: "user", content: input };
    setMessages([...messages, newMsg]);
    onSend(input);
    setInput("");
  };

  return (
    <div className={`fixed bottom-4 right-4 z-50 ${isOpen ? "w-80" : "w-16"}`}>
      {!isOpen && (
        <button onClick={() => setIsOpen(true)} className="w-12 h-12 bg-[#7c93c3] rounded-full flex items-center justify-center shadow-lg">
          <MessageSquare className="w-5 h-5 text-white" />
        </button>
      )}
      
      {isOpen && (
        <div className="bg-white rounded-2xl shadow-2xl border border-slate-200 overflow-hidden">
          <div className="bg-[#7c93c3] px-4 py-3 flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Bot className="w-4 h-4 text-white" />
              <span className="text-white text-sm font-medium">AI Architect Chat</span>
            </div>
            <button onClick={() => setIsOpen(false)}><X className="w-4 h-4 text-white/80" /></button>
          </div>
          
          <div className="h-64 overflow-y-auto p-3 space-y-3">
            {messages.map(m => (
              <div key={m.id} className={`flex ${m.role === "user" ? "justify-end" : "justify-start"}`}>
                <div className={`max-w-[85%] px-3 py-2 rounded-xl text-xs ${
                  m.role === "user" ? "bg-[#7c93c3] text-white" : "bg-slate-100 text-slate-700"
                }`}>
                  {m.role === "user" ? <User className="w-3 h-3 inline mr-1" /> : <Bot className="w-3 h-3 inline mr-1" />}
                  {m.content}
                </div>
              </div>
            ))}
            {messages.length <= 1 && (
              <div className="space-y-2 mt-3">
                <p className="text-xs text-slate-500 mb-2">Quick starts:</p>
                {quickOptions.map(opt => (
                  <button key={opt} onClick={() => handleOption(opt)}
                    className="block w-full text-left px-3 py-2 bg-slate-50 hover:bg-blue-50 rounded-lg text-xs text-slate-600 transition">
                    {opt}
                  </button>
                ))}
              </div>
            )}
          </div>
          
          <div className="p-2 border-t flex gap-2">
            <input value={input} onChange={e => setInput(e.target.value)}
              onKeyDown={e => e.key === "Enter" && handleSend()}
              placeholder="Describe your dream building..."
              className="flex-1 px-3 py-2 bg-slate-50 rounded-lg text-xs outline-none" />
            <button onClick={handleSend} className="p-2 bg-[#7c93c3] rounded-lg">
              <Send className="w-4 h-4 text-white" />
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
