import React from "react";

export function AiLoader({
  size = 168,
  text = "Analyzing",
  overlay = false,
  className = "",
}) {
  const letters = text.split("");

  return (
    <div
      className={`flex items-center justify-center ${
        overlay ? "fixed inset-0 z-50 bg-[#050505]/95 backdrop-blur-sm" : "w-full py-12"
      } ${className}`}
    >
      <div
        className="relative flex items-center justify-center rounded-full border border-[#4CBB1725] bg-[#0E120A] shadow-[0_0_0_1px_rgba(76,187,23,0.1),0_24px_60px_rgba(0,0,0,0.35)]"
        style={{ width: size, height: size }}
      >
        <div className="pointer-events-none absolute inset-[10%] rounded-full border border-[#4CBB1720]" />
        <div className="pointer-events-none absolute inset-[18%] rounded-full border border-dashed border-[#4CBB1735] animate-[moLoaderOrbit_5s_linear_infinite]" />

        <div className="relative z-10 flex flex-wrap items-center justify-center gap-[1px] px-6 text-center">
          {letters.map((letter, index) => (
            <span
              key={`${letter}-${index}`}
              className="animate-[moLoaderLetter_2.8s_ease-in-out_infinite] text-sm font-semibold uppercase tracking-[0.22em] text-white/80"
              style={{ animationDelay: `${index * 0.08}s` }}
            >
              {letter}
            </span>
          ))}
        </div>

        <div className="pointer-events-none absolute inset-0 rounded-full animate-[moLoaderGlow_3.8s_ease-in-out_infinite]" />
      </div>
    </div>
  );
}

export default AiLoader;
