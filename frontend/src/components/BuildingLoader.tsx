/**
 * BuildingLoader — inline progress bar (not a full-screen overlay).
 * Shows for a minimum of 2 seconds, then fades out once isLoading = false.
 */
"use client";
import React, { useEffect, useRef, useState } from "react";

interface BuildingLoaderProps { isLoading: boolean; }

export const BuildingLoader = ({ isLoading }: BuildingLoaderProps) => {
  const [visible, setVisible] = useState(false);
  const [progress, setProgress] = useState(0);
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const startRef = useRef<number>(0);
  const rafRef = useRef<number>(0);

  useEffect(() => {
    if (isLoading) {
      setVisible(true);
      setProgress(0);
      startRef.current = Date.now();

      // Animate progress: fast to 80%, then stalls until done
      const animate = () => {
        const elapsed = Date.now() - startRef.current;
        const t = Math.min(elapsed / 2000, 1); // 2 seconds to reach ~80%
        const p = t < 1 ? Math.round(t * 80) : 80;
        setProgress(p);
        if (t < 1) rafRef.current = requestAnimationFrame(animate);
      };
      rafRef.current = requestAnimationFrame(animate);
    } else {
      // Loading done: sprint to 100%, hold 400ms, then hide
      cancelAnimationFrame(rafRef.current);
      const elapsed = Date.now() - startRef.current;
      const remaining = Math.max(0, 2000 - elapsed); // honour 2s minimum

      timerRef.current = setTimeout(() => {
        setProgress(100);
        setTimeout(() => setVisible(false), 500);
      }, remaining);
    }
    return () => {
      cancelAnimationFrame(rafRef.current);
      if (timerRef.current) clearTimeout(timerRef.current);
    };
  }, [isLoading]);

  if (!visible) return null;

  const steps = ["Parsing prompt", "Planning layout", "Generating geometry", "Applying materials", "NBC audit"];
  const stepIdx = Math.min(Math.floor((progress / 100) * steps.length), steps.length - 1);

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center"
      style={{ background: "rgba(15,23,42,0.82)", backdropFilter: "blur(6px)" }}
    >
      <div
        className="bg-white rounded-2xl shadow-2xl px-8 py-7 flex flex-col items-center gap-5"
        style={{ width: 320, border: "1px solid rgba(124,147,195,0.2)" }}
      >
        {/* Animated crane icon */}
        <div className="relative w-16 h-16 flex items-center justify-center">
          <svg width="64" height="64" viewBox="0 0 64 64" fill="none">
            {/* Tower */}
            <rect x="28" y="16" width="8" height="36" rx="2" fill="#f59e0b"/>
            {/* Arm */}
            <rect x="10" y="16" width="44" height="5" rx="2" fill="#f59e0b"
              style={{ transformOrigin: "32px 18px", animation: "craneSwing 2s ease-in-out infinite alternate" }} />
            {/* Hook wire */}
            <line x1="46" y1="21" x2="46" y2="36" stroke="#6b7280" strokeWidth="1.5"
              style={{ animation: "hookLift 2s ease-in-out infinite alternate" }} />
            {/* Hook */}
            <rect x="42" y="36" width="8" height="5" rx="1" fill="#4b5563"
              style={{ animation: "hookLift 2s ease-in-out infinite alternate" }} />
            {/* Bricks */}
            <rect x="22" y="49" width="12" height="6" rx="1" fill="#dc2626" opacity="0.9"/>
            <rect x="30" y="43" width="12" height="6" rx="1" fill="#b91c1c" opacity="0.8"/>
          </svg>
          <style>{`
            @keyframes craneSwing { 0%{transform:rotate(-4deg)} 100%{transform:rotate(4deg)} }
            @keyframes hookLift { 0%{transform:translateY(0)} 100%{transform:translateY(-6px)} }
          `}</style>
        </div>

        <div className="text-center">
          <p className="font-bold text-slate-800 text-base mb-0.5">Building your house…</p>
          <p className="text-slate-400 text-xs">{steps[stepIdx]}</p>
        </div>

        {/* Progress bar */}
        <div className="w-full h-2 bg-slate-100 rounded-full overflow-hidden">
          <div
            className="h-full rounded-full transition-all duration-300"
            style={{
              width: `${progress}%`,
              background: "linear-gradient(90deg,#f59e0b,#f97316,#f59e0b)",
              backgroundSize: "200% 100%",
              animation: "shimmer 1.5s linear infinite",
            }}
          />
        </div>
        <style>{`@keyframes shimmer{0%{background-position:200% 0}100%{background-position:-200% 0}}`}</style>
        <p className="text-slate-300 text-[10px]">{progress}%</p>
      </div>
    </div>
  );
};

export default BuildingLoader;
