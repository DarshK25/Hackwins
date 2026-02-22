import React from "react";
import { motion } from "framer-motion";
import { cn } from "@/lib/utils";

// MoneyOps-themed hover colors — subtle, matching the dark brand palette
const HOVER_COLORS = [
    "rgba(76, 187, 23, 0.35)",   // brand green
    "rgba(76, 187, 23, 0.18)",   // brand green soft
    "rgba(96, 165, 250, 0.25)",  // blue-400
    "rgba(167, 139, 250, 0.25)", // violet-400
    "rgba(251, 191, 36, 0.25)",  // amber-400
    "rgba(205, 28, 24, 0.20)",   // brand red
    "rgba(52, 211, 153, 0.22)",  // emerald-400
    "rgba(248, 113, 113, 0.18)", // red-400 soft
    "rgba(147, 197, 253, 0.20)", // sky-300
];

const getRandomColor = () => HOVER_COLORS[Math.floor(Math.random() * HOVER_COLORS.length)];

export function BoxesCore({ className, rows = 60, cols = 40, ...rest }) {
    const rowArr = new Array(rows).fill(1);
    const colArr = new Array(cols).fill(1);

    return (
        <div
            style={{
                transform:
                    "translate(-40%,-60%) skewX(-48deg) skewY(14deg) scale(0.675) rotate(0deg) translateZ(0)",
            }}
            className={cn(
                "absolute left-1/4 p-4 -top-1/4 flex -translate-x-1/2 -translate-y-1/2 w-full h-full z-0",
                className
            )}
            {...rest}
        >
            {rowArr.map((_, i) => (
                <motion.div
                    key={`row-${i}`}
                    className="w-16 h-8 relative"
                    style={{ borderLeft: "1px solid #2A2A2A" }}
                >
                    {colArr.map((_, j) => (
                        <motion.div
                            key={`col-${j}`}
                            whileHover={{
                                backgroundColor: getRandomColor(),
                                transition: { duration: 0 },
                            }}
                            animate={{ transition: { duration: 2 } }}
                            className="w-16 h-8 relative"
                            style={{ borderRight: "1px solid #2A2A2A", borderTop: "1px solid #2A2A2A" }}
                        >
                            {/* Plus intersections at every other cell */}
                            {j % 2 === 0 && i % 2 === 0 ? (
                                <svg
                                    xmlns="http://www.w3.org/2000/svg"
                                    fill="none"
                                    viewBox="0 0 24 24"
                                    strokeWidth="1.5"
                                    stroke="currentColor"
                                    className="absolute h-6 w-10 -top-[14px] -left-[22px] pointer-events-none"
                                    style={{ color: "#2A2A2A", strokeWidth: "1px" }}
                                >
                                    <path
                                        strokeLinecap="round"
                                        strokeLinejoin="round"
                                        d="M12 6v12m6-6H6"
                                    />
                                </svg>
                            ) : null}
                        </motion.div>
                    ))}
                </motion.div>
            ))}
        </div>
    );
}

export const Boxes = React.memo(BoxesCore);
