import { useState, useEffect, useRef } from "react";
import { motion, AnimatePresence } from "framer-motion";

/**
 * AnimatedTextCycle
 * Cycles through `words` with a smooth blur/fade slide animation.
 *
 * Props:
 *   words    string[]   — array of words to cycle through
 *   interval number     — ms between transitions (default 3000)
 *   className string    — extra Tailwind classes applied to each word span
 */
export default function AnimatedTextCycle({ words, interval = 3000, className = "" }) {
    const [currentIndex, setCurrentIndex] = useState(0);
    const [width, setWidth] = useState("auto");
    const measureRef = useRef(null);

    // Measure the current word's width so the container springs to fit
    useEffect(() => {
        if (measureRef.current) {
            const elements = measureRef.current.children;
            if (elements.length > currentIndex) {
                const newWidth = elements[currentIndex].getBoundingClientRect().width;
                setWidth(`${newWidth}px`);
            }
        }
    }, [currentIndex]);

    // Tick the index
    useEffect(() => {
        const timer = setInterval(() => {
            setCurrentIndex((prev) => (prev + 1) % words.length);
        }, interval);
        return () => clearInterval(timer);
    }, [interval, words.length]);

    const containerVariants = {
        hidden: { y: -18, opacity: 0, filter: "blur(8px)" },
        visible: {
            y: 0,
            opacity: 1,
            filter: "blur(0px)",
            transition: { duration: 0.38, ease: "easeOut" },
        },
        exit: {
            y: 18,
            opacity: 0,
            filter: "blur(8px)",
            transition: { duration: 0.28, ease: "easeIn" },
        },
    };

    return (
        <>
            {/* Hidden ruler — renders all words invisibly to measure widths */}
            <div
                ref={measureRef}
                aria-hidden="true"
                className="absolute opacity-0 pointer-events-none"
                style={{ visibility: "hidden" }}
            >
                {words.map((word, i) => (
                    <span key={i} className={`font-bold ${className}`}>
                        {word}
                    </span>
                ))}
            </div>

            {/* Animated word container */}
            <motion.span
                className="relative inline-block"
                animate={{
                    width,
                    transition: { type: "spring", stiffness: 150, damping: 15, mass: 1.2 },
                }}
            >
                <AnimatePresence mode="wait" initial={false}>
                    <motion.span
                        key={currentIndex}
                        className={`inline-block font-bold ${className}`}
                        variants={containerVariants}
                        initial="hidden"
                        animate="visible"
                        exit="exit"
                        style={{ whiteSpace: "nowrap" }}
                    >
                        {words[currentIndex]}
                    </motion.span>
                </AnimatePresence>
            </motion.span>
        </>
    );
}
