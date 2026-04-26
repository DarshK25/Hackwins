import React from "react";

export function AiLoader({
  size = 180,
  text = "Generating",
  overlay = false,
  className = "",
}) {
  const letters = text.split("");

  return (
    <div
      className={`flex items-center justify-center ${
        overlay
          ? "fixed inset-0 z-50 bg-gradient-to-b from-[#1a3379] via-[#0f172a] to-black"
          : "w-full rounded-2xl bg-gradient-to-b from-[#1a3379] via-[#0f172a] to-black px-5 py-6"
      } ${className}`}
    >
      <div
        className="relative flex select-none items-center justify-center font-inter"
        style={{ width: size, height: size }}
      >
        <div className="relative z-10 flex flex-wrap items-center justify-center gap-[1px] px-6 text-center">
          {letters.map((letter, index) => (
            <span
              key={index}
              className="inline-block animate-loaderLetter text-sm font-semibold uppercase tracking-[0.18em] text-white opacity-40"
              style={{ animationDelay: `${index * 0.1}s` }}
            >
              {letter}
            </span>
          ))}
        </div>

        <div className="absolute inset-0 rounded-full animate-loaderCircle" />
      </div>
    </div>
  );
}

export default AiLoader;
