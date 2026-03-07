import {
  useScroll,
  useTransform,
  motion,
} from "framer-motion";
import React, { useEffect, useRef, useState } from "react";

/**
 * Timeline — scroll-driven vertical timeline.
 * Clean natural flow: no sticky stacking, no card overlap.
 */
export const Timeline = ({ data }) => {
  const ref = useRef(null);
  const containerRef = useRef(null);
  const [height, setHeight] = useState(0);

  useEffect(() => {
    if (ref.current) {
      setHeight(ref.current.getBoundingClientRect().height);
    }
  }, [ref]);

  const { scrollYProgress } = useScroll({
    target: containerRef,
    offset: ["start 10%", "end 50%"],
  });

  const heightTransform = useTransform(scrollYProgress, [0, 1], [0, height]);
  const opacityTransform = useTransform(scrollYProgress, [0, 0.1], [0, 1]);

  return (
    <div
      className="w-full font-sans md:px-10"
      style={{ backgroundColor: "#0A0A0A" }}
      ref={containerRef}
    >
      <div ref={ref} className="relative max-w-5xl mx-auto pb-20">
        {data.map((item, index) => (
          <div
            key={index}
            className="flex justify-start md:gap-10 pt-16 md:pt-24"
          >
            {/* ── Left column: step number ─────────────────────────────── */}
            <div className="flex flex-col md:flex-row items-center self-start max-w-xs lg:max-w-sm md:w-full flex-shrink-0">
              {/* Timeline dot */}
              <div
                className="h-10 w-10 rounded-full flex items-center justify-center flex-shrink-0"
                style={{
                  backgroundColor: "#111111",
                  border: "1px solid #2A2A2A",
                  // keep it anchored on the line
                  position: "absolute",
                  left: "0.75rem",
                }}
              >
                <div
                  className="h-4 w-4 rounded-full"
                  style={{
                    backgroundColor: "#4CBB17",
                    boxShadow: "0 0 8px #4CBB1780",
                  }}
                />
              </div>

              {/* Large step number — desktop only */}
              <h3
                className="hidden md:block md:pl-20 font-extrabold select-none"
                style={{
                  fontSize: "clamp(3.5rem, 6vw, 5rem)",
                  color: "#222222",
                  letterSpacing: "-0.04em",
                  lineHeight: 1,
                }}
              >
                {item.title}
              </h3>
            </div>

            {/* ── Right column: card ───────────────────────────────────── */}
            <div className="relative pl-20 pr-4 md:pl-4 w-full min-w-0">
              {/* Mobile step label */}
              <h3
                className="md:hidden block text-3xl mb-3 font-extrabold select-none"
                style={{ color: "#222222", letterSpacing: "-0.04em" }}
              >
                {item.title}
              </h3>
              {item.content}
            </div>
          </div>
        ))}

        {/* ── Vertical track line ──────────────────────────────────────── */}
        <div
          className="absolute md:left-8 left-8 top-0 overflow-hidden w-[2px]"
          style={{
            height: height + "px",
            background:
              "linear-gradient(to bottom, transparent 0%, #2A2A2A 10%, #2A2A2A 90%, transparent 100%)",
            maskImage:
              "linear-gradient(to bottom, transparent 0%, black 10%, black 90%, transparent 100%)",
            WebkitMaskImage:
              "linear-gradient(to bottom, transparent 0%, black 10%, black 90%, transparent 100%)",
          }}
        >
          {/* Scroll-driven animated fill */}
          <motion.div
            className="absolute inset-x-0 top-0 w-[2px] rounded-full"
            style={{
              height: heightTransform,
              opacity: opacityTransform,
              background:
                "linear-gradient(to bottom, transparent 0%, #4CBB17 50%, #60A5FA 100%)",
            }}
          />
        </div>
      </div>
    </div>
  );
};
