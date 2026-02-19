import { motion } from "framer-motion";
import { Circle, ArrowRight } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Link } from "react-router-dom";

const floatingShapes = [
    {
        width: 600,
        height: 140,
        rotate: 12,
        gradient: "from-blue-500/10 to-cyan-500/10",
        top: "20%",
        left: "-10%",
    },
    {
        width: 300,
        height: 80,
        rotate: -8,
        gradient: "from-blue-500/20 to-transparent",
        bottom: "10%",
        left: "10%",
    },
];

export default function Hero() {
    return (
        <section className="relative min-h-screen flex items-center justify-center overflow-hidden pt-16">
            {/* Decorative floating shapes */}
            {floatingShapes.map((shape, i) => (
                <motion.div
                    key={i}
                    className="absolute pointer-events-none"
                    initial={{ opacity: 0, y: 100 }}
                    animate={{ opacity: 1, y: 0 }}
                    style={{
                        width: shape.width,
                        height: shape.height,
                        rotate: shape.rotate,
                        top: shape.top,
                        left: shape.left,
                        bottom: shape.bottom,
                        borderRadius: "999px",
                    }}
                    transition={{ duration: 2, delay: i * 0.2 }}
                >
                    <div className={`w-full h-full rounded-[999px] bg-gradient-to-r ${shape.gradient}`} />
                </motion.div>
            ))}

            <div className="relative z-10 container mx-auto text-center px-4">
                {/* Badge */}
                <motion.div
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ duration: 0.6 }}
                    className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full bg-blue-50 border border-blue-100 mb-8"
                >
                    <Circle className="h-2 w-2 fill-blue-600 text-blue-600 animate-pulse" />
                    <span className="text-sm text-blue-700 font-medium">AI-Powered Finance OS</span>
                </motion.div>

                {/* Headline */}
                <motion.h1
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ duration: 0.6, delay: 0.1 }}
                    className="text-5xl md:text-7xl font-bold mb-6 tracking-tight"
                >
                    Your Intelligent <br />
                    <span className="text-blue-600">Financial Companion</span>
                </motion.h1>

                {/* Subheadline */}
                <motion.p
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ duration: 0.6, delay: 0.2 }}
                    className="text-lg text-slate-600 max-w-2xl mx-auto mb-8"
                >
                    From talking about finances to running your finances — autonomously. AI agents that
                    think, decide, and act on your behalf.
                </motion.p>

                {/* CTAs */}
                <motion.div
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ duration: 0.6, delay: 0.3 }}
                    className="flex flex-wrap gap-4 justify-center"
                >
                    <Link to="/analytics">
                        <Button size="lg" className="rounded-full">
                            Get Started <ArrowRight className="ml-2 w-4 h-4" />
                        </Button>
                    </Link>
                    <Link to="/analytics">
                        <Button size="lg" variant="outline" className="rounded-full">
                            Try AI Assistant
                        </Button>
                    </Link>
                </motion.div>
            </div>
        </section>
    );
}
