import { useState, useMemo } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { ArrowUpRight } from "lucide-react";
import { cn } from "@/lib/utils";

/**
 * InteractiveTrendCard
 *
 * Props:
 *  title             string
 *  subtitle          string
 *  totalValue        number
 *  newValue          number
 *  totalValueLabel   string  (default "Total")
 *  newValueLabel     string  (default "New")
 *  chartData         { month: string, value: number }[]
 *  className         string
 *  icon              ReactNode
 *  defaultBarColor   string  (CSS color)
 *  barColor          string  (hovered bar)
 *  adjacentBarColor  string  (±1 from hover)
 *  formatValue       fn      (value → string for footer display)
 *  formatTooltip     fn      (value → string for tooltip)
 */
export function InteractiveTrendCard({
    title,
    subtitle,
    totalValue,
    newValue,
    totalValueLabel = "Total",
    newValueLabel = "New",
    chartData = [],
    className,
    icon = <ArrowUpRight className="h-4 w-4" />,
    defaultBarColor = "#2A2A2A",
    barColor = "#4CBB17",
    adjacentBarColor = "#4CBB1770",
    formatValue = (v) => (typeof v === "number" ? v.toLocaleString() : v),
    formatTooltip = (v) => String(v),
}) {
    const [hoveredIndex, setHoveredIndex] = useState(null);
    const maxValue = useMemo(
        () => Math.max(...chartData.map((d) => d.value), 1),
        [chartData]
    );

    return (
        <div
            className={cn("w-full rounded-2xl p-5", className)}
            style={{
                backgroundColor: "#111111",
                border: "1px solid #2A2A2A",
            }}
        >
            {/* Header */}
            <div className="flex items-start justify-between mb-2">
                <div>
                    <h3 className="text-lg font-bold text-white leading-tight">{title}</h3>
                    <p className="text-sm text-[#A0A0A0] mt-0.5">{subtitle}</p>
                </div>
                <button
                    className="rounded-full p-1.5 transition-colors"
                    style={{
                        backgroundColor: "#1A1A1A",
                        border: "1px solid #2A2A2A",
                        color: "#A0A0A0",
                    }}
                    onMouseEnter={(e) => {
                        e.currentTarget.style.color = "#4CBB17";
                        e.currentTarget.style.borderColor = "#4CBB17";
                    }}
                    onMouseLeave={(e) => {
                        e.currentTarget.style.color = "#A0A0A0";
                        e.currentTarget.style.borderColor = "#2A2A2A";
                    }}
                >
                    {icon}
                </button>
            </div>

            {/* Bar Chart */}
            <div
                className="relative mt-8 h-36"
                onMouseLeave={() => setHoveredIndex(null)}
                role="figure"
                aria-label={`Trend chart: ${title}`}
            >
                {/* Tooltip bubble */}
                <AnimatePresence>
                    {hoveredIndex !== null && chartData[hoveredIndex] && (
                        <motion.div
                            key={hoveredIndex}
                            initial={{ opacity: 0, y: -6, scale: 0.92 }}
                            animate={{ opacity: 1, y: 0, scale: 1 }}
                            exit={{ opacity: 0, y: -6, scale: 0.92 }}
                            transition={{ duration: 0.15, ease: "easeOut" }}
                            className="pointer-events-none absolute -top-7 z-10"
                            style={{
                                left: `${(hoveredIndex / Math.max(chartData.length - 1, 1)) * 100}%`,
                                transform: "translateX(-50%)",
                            }}
                        >
                            <div
                                className="rounded-lg px-2 py-1 text-xs font-semibold whitespace-nowrap shadow-lg"
                                style={{
                                    backgroundColor: "#4CBB17",
                                    color: "#000",
                                }}
                            >
                                {formatTooltip(chartData[hoveredIndex].value)}
                            </div>
                        </motion.div>
                    )}
                </AnimatePresence>

                {/* Bars + Labels */}
                <div className="flex h-full w-full items-end justify-between gap-1">
                    {chartData.map((data, index) => {
                        const barHeightPct = (data.value / maxValue) * 100;
                        const isHovered = hoveredIndex === index;
                        const isAdjacent =
                            hoveredIndex !== null &&
                            Math.abs(hoveredIndex - index) === 1;

                        return (
                            <div
                                key={index}
                                className="flex h-full flex-1 flex-col items-center justify-end"
                            >
                                <div
                                    className="relative h-full w-full flex items-end"
                                    onMouseEnter={() => setHoveredIndex(index)}
                                    role="img"
                                    aria-label={`${data.month}: ${data.value}`}
                                >
                                    <motion.div
                                        className="w-full rounded-t-sm"
                                        style={{ height: `${Math.max(barHeightPct, 4)}%` }}
                                        initial={{ backgroundColor: defaultBarColor }}
                                        animate={{
                                            backgroundColor: isHovered
                                                ? barColor
                                                : isAdjacent
                                                    ? adjacentBarColor
                                                    : defaultBarColor,
                                        }}
                                        transition={{ duration: 0.25, ease: "easeInOut" }}
                                    />
                                </div>
                                <span className="mt-1.5 text-[10px] text-[#A0A0A0] truncate max-w-full px-0.5">
                                    {data.month}
                                </span>
                            </div>
                        );
                    })}
                </div>
            </div>

            {/* Footer Stats */}
            <div
                className="mt-5 flex justify-between pt-4"
                style={{ borderTop: "1px solid #2A2A2A" }}
            >
                <div>
                    <p className="text-[10px] font-medium uppercase tracking-wider text-[#A0A0A0]">
                        {totalValueLabel}
                    </p>
                    <p className="text-2xl font-bold text-white mt-0.5">
                        {formatValue(totalValue)}
                    </p>
                </div>
                <div className="text-right">
                    <p className="text-[10px] font-medium uppercase tracking-wider text-[#A0A0A0]">
                        {newValueLabel}
                    </p>
                    <p className="text-2xl font-bold mt-0.5" style={{ color: "#4CBB17" }}>
                        {formatValue(newValue)}
                    </p>
                </div>
            </div>
        </div>
    );
}
