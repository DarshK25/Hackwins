import Navigation from "@/components/landing/Navigation";
import Hero from "@/components/landing/Hero";
import HowItWorks from "@/components/landing/Features";
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
        <main className="min-h-screen bg-black text-white selection:bg-[#4CBB1730]">
            <Navigation />
            <Hero />
            <HowItWorks />
            <AgentEcosystem />
            <Pricing />
            <Footer />
        </main>
    );
}
