import Navigation from "@/components/landing/Navigation";
import Hero from "@/components/landing/Hero";
import Features from "@/components/landing/Features";
import AgentEcosystem from "@/components/landing/AgentEcosystem";
import Pricing from "@/components/landing/Pricing";
import Footer from "@/components/landing/Footer";

/**
 * LandingPage
 * Assembled from individual section components.
 * Add new sections here as the product grows.
 */
export default function LandingPage() {
    return (
        <main className="min-h-screen bg-white text-slate-900 selection:bg-blue-100">
            <Navigation />
            <Hero />
            <Features />
            <AgentEcosystem />
            <Pricing />
            <Footer />
        </main>
    );
}
