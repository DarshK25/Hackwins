import React from "react";

export function AiLoader({
  size = 180,
  text = "Generating",
  overlay = false,
  className = "",
}) {
  return (
    <div
      className={`flex items-center justify-center ${
        overlay
          ? "fixed inset-0 z-50 bg-black/75 backdrop-blur-sm"
          : "w-full"
      } ${className}`}
    >
      <div
        className="relative flex select-none items-center justify-center font-inter"
        style={{ width: size, height: size }}
      >
        <div className="relative z-10 flex items-center justify-center px-3 text-center whitespace-nowrap">
          <span className="animate-pulse text-[9px] font-semibold uppercase tracking-[0.12em] text-[#D7FFD0] opacity-60">
            {text}
          </span>
        </div>

        <div className="absolute inset-0 rounded-full animate-loaderCircle" />
      </div>
    </div>
  );
}

export default AiLoader;