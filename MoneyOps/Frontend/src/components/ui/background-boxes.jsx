"use client";
import React, { useCallback } from "react";
import { motion } from "framer-motion";
import { cn } from "@/lib/utils";

// MoneyOps-themed hover colors — green + grey palette as requested
const HOVER_COLORS = [
    "rgb(74, 222, 128)",    // green-400
    "rgb(134, 239, 172)",   // green-300
    "rgb(22, 163, 74)",     // green-600
    "rgb(21, 128, 61)",     // green-700
    "rgb(20, 83, 45)",      // green-900
    "rgb(100, 116, 139)",   // slate-500 (grey)
    "rgb(71, 85, 105)",     // slate-600 (grey)
    "rgb(51, 65, 85)",      // slate-700 (dark grey)
    "rgb(148, 163, 184)",   // slate-400 (light grey)
];

const getRandomColor = () =>
    HOVER_COLORS[Math.floor(Math.random() * HOVER_COLORS.length)];

export const BoxesCore = ({ className, ...rest }) => {
    const rows = new Array(150).fill(1);
    const cols = new Array(100).fill(1);

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
            {rows.map((_, i) => (
                <motion.div
                    key={`row-${i}`}
                    className="w-16 h-8 border-l border-slate-700 relative"
                >
                    {cols.map((_, j) => (
                        <motion.div
                            key={`col-${j}`}
                            whileHover={{
                                backgroundColor: getRandomColor(),
                                transition: { duration: 0 },
                            }}
                            animate={{
                                transition: { duration: 2 },
                            }}
                            className="w-16 h-8 border-r border-t border-slate-700 relative"
                        >
                            {j % 2 === 0 && i % 2 === 0 ? (
                                <svg
                                    xmlns="http://www.w3.org/2000/svg"
                                    fill="none"
                                    viewBox="0 0 24 24"
                                    strokeWidth="1.5"
                                    stroke="currentColor"
                                    className="absolute h-6 w-10 -top-[14px] -left-[22px] text-slate-700 stroke-[1px] pointer-events-none"
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
};

export const Boxes = React.memo(BoxesCore);
