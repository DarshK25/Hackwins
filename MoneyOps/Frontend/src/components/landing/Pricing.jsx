import { useState, useRef } from "react";
import { motion } from "framer-motion";
import { Check, Star, Zap } from "lucide-react";
import { Link } from "react-router-dom";
import { cn } from "@/lib/utils";
import { Switch } from "@/components/ui/switch";
import { Label } from "@/components/ui/label";
import { buttonVariants } from "@/components/ui/button";
import { useMediaQuery } from "@/hooks/use-media-query";
import NumberFlow from "@number-flow/react";
import confetti from "canvas-confetti";

// ── MoneyOps plan data ────────────────────────────────────────────────────

const PLANS = [
  {
    name: "Free",
    badge: "Try Before You Buy",
    monthlyPrice: 0,
    yearlyPrice: 0,
    period: "month",
    description: "Perfect for freelancers getting started with AI invoicing.",
    buttonText: "Start for Free",
    href: "/sign-up",
    isPopular: false,
    target: "Great for acquisition & viral growth",
    features: [
      "10 invoices / month",
      "Voice invoice creation",
      "Basic templates",
      "WhatsApp delivery",
    ],
  },
  {
    name: "Pro",
    badge: "Most Popular",
    monthlyPrice: 299,
    yearlyPrice: 239,
    period: "month",
    description: "For active consultants sending 20+ invoices a month.",
    buttonText: "Get Pro",
    href: "/sign-up",
    isPopular: true,
    target: "Target: Active consultants",
    features: [
      "Unlimited invoices",
      "Custom branding (logo & colors)",
      "Payment reminders (WhatsApp + Email)",
      "Invoice history & search",
      "Priority support",
    ],
  },
  {
    name: "Team",
    badge: "Best for Agencies",
    monthlyPrice: 799,
    yearlyPrice: 639,
    period: "month",
    description: "For small agencies with shared clients and team workflows.",
    buttonText: "Get Team",
    href: "/sign-up",
    isPopular: false,
    target: "Target: Small agencies (3–5 people)",
    features: [
      "Everything in Pro",
      "Multi-user access (3 users)",
      "Shared client database",
      "Team invoice templates",
      "Dedicated support",
    ],
  },
];

// ── Pricing card ──────────────────────────────────────────────────────────

function PricingCard({ plan, index, isMonthly, isDesktop }) {
  const price = isMonthly ? plan.monthlyPrice : plan.yearlyPrice;
  const isFree = plan.monthlyPrice === 0;

  return (
    <motion.div
      initial={{ y: 50, opacity: 0 }}
      whileInView={
        isDesktop
          ? {
              y: plan.isPopular ? -20 : 0,
              opacity: 1,
              x: index === 2 ? -30 : index === 0 ? 30 : 0,
              scale: index === 0 || index === 2 ? 0.94 : 1.0,
            }
          : { opacity: 1, y: 0 }
      }
      viewport={{ once: true }}
      transition={{
        duration: 1.4,
        type: "spring",
        stiffness: 100,
        damping: 30,
        delay: 0.3 + index * 0.05,
      }}
      className={cn(
        "relative rounded-2xl p-7 flex flex-col",
        plan.isPopular
          ? "border-2"
          : "border border-[#2A2A2A] mt-5",
        index === 0 && "origin-right",
        index === 2 && "origin-left"
      )}
      style={{
        backgroundColor: plan.isPopular ? "#0F1A0A" : "#111111",
        borderColor: plan.isPopular ? "#4CBB17" : undefined,
        boxShadow: plan.isPopular
          ? "0 0 60px #4CBB1720, 0 0 0 1px #4CBB1730"
          : "0 4px 24px rgba(0,0,0,0.4)",
        zIndex: plan.isPopular ? 10 : 0,
      }}
    >
      {/* Popular badge */}
      {plan.isPopular && (
        <div
          className="absolute -top-px right-6 flex items-center gap-1 px-3 py-1 rounded-b-xl text-xs font-semibold"
          style={{ backgroundColor: "#4CBB17", color: "#000" }}
        >
          <Star className="h-3 w-3 fill-current" />
          Popular
        </div>
      )}

      {/* Plan name + badge */}
      <div className="mb-5">
        <p
          className="text-xs font-semibold uppercase tracking-widest mb-1"
          style={{ color: plan.isPopular ? "#4CBB17" : "#A0A0A0" }}
        >
          {plan.badge}
        </p>
        <h3 className="text-xl font-bold text-white">{plan.name}</h3>
      </div>

      {/* Price */}
      <div className="flex items-baseline gap-1 mb-1">
        {isFree ? (
          <span className="text-5xl font-extrabold text-white tracking-tight">
            Free
          </span>
        ) : (
          <>
            <span className="text-2xl font-bold text-white">₹</span>
            <span className="text-5xl font-extrabold text-white tracking-tight">
              <NumberFlow
                value={price}
                transformTiming={{ duration: 500, easing: "ease-out" }}
                willChange
              />
            </span>
          </>
        )}
        {!isFree && (
          <span className="text-sm font-medium ml-1" style={{ color: "#A0A0A0" }}>
            / {plan.period}
          </span>
        )}
      </div>

      {/* Billing cycle note */}
      {!isFree && (
        <p className="text-xs mb-5" style={{ color: "#6A6A6A" }}>
          {isMonthly ? "billed monthly" : `₹${plan.yearlyPrice * 12}/yr · save ~20%`}
        </p>
      )}
      {isFree && <div className="mb-5" />}

      {/* Features */}
      <ul className="space-y-3 mb-6 flex-1">
        {plan.features.map((feat, i) => (
          <li key={i} className="flex items-start gap-2.5 text-sm">
            <Check
              className="h-4 w-4 mt-0.5 flex-shrink-0"
              style={{ color: "#4CBB17" }}
            />
            <span style={{ color: "#C0C0C0" }}>{feat}</span>
          </li>
        ))}
      </ul>

      {/* Divider */}
      <hr className="border-[#2A2A2A] mb-5" />

      {/* CTA button */}
      <Link to={plan.href} className="w-full">
        <button
          className={cn(
            "w-full py-2.5 px-4 rounded-xl text-sm font-semibold transition-all duration-200",
            "hover:scale-[1.02] active:scale-[0.98]"
          )}
          style={
            plan.isPopular
              ? { backgroundColor: "#4CBB17", color: "#000" }
              : {
                  backgroundColor: "transparent",
                  color: "#A0A0A0",
                  border: "1px solid #2A2A2A",
                }
          }
          onMouseEnter={(e) => {
            if (!plan.isPopular) {
              e.currentTarget.style.borderColor = "#4CBB17";
              e.currentTarget.style.color = "#4CBB17";
            }
          }}
          onMouseLeave={(e) => {
            if (!plan.isPopular) {
              e.currentTarget.style.borderColor = "#2A2A2A";
              e.currentTarget.style.color = "#A0A0A0";
            }
          }}
        >
          {plan.buttonText}
        </button>
      </Link>

      {/* Target audience note */}
      <p className="mt-4 text-xs text-center" style={{ color: "#555555" }}>
        {plan.target}
      </p>
    </motion.div>
  );
}

// ── Section ───────────────────────────────────────────────────────────────

export default function Pricing() {
  const [isMonthly, setIsMonthly] = useState(true);
  const isDesktop = useMediaQuery("(min-width: 768px)");
  const switchRef = useRef(null);

  const handleToggle = (checked) => {
    setIsMonthly(!checked);
    // Confetti celebration when switching to annual
    if (checked && switchRef.current) {
      const rect = switchRef.current.getBoundingClientRect();
      confetti({
        particleCount: 60,
        spread: 70,
        origin: {
          x: (rect.left + rect.width / 2) / window.innerWidth,
          y: (rect.top + rect.height / 2) / window.innerHeight,
        },
        colors: ["#4CBB17", "#60A5FA", "#A78BFA", "#FFB300"],
        ticks: 200,
        gravity: 1.2,
        decay: 0.94,
        startVelocity: 28,
        shapes: ["circle"],
      });
    }
  };

  return (
    <section id="pricing" className="py-24" style={{ backgroundColor: "#0A0A0A" }}>
      <div className="container mx-auto px-4">

        {/* ── Section heading ─────────────────────────────────────── */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.5 }}
          className="text-center mb-12"
        >
          <p
            className="text-xs font-semibold uppercase tracking-widest mb-3"
            style={{ color: "#4CBB17" }}
          >
            Simple Pricing
          </p>
          <h2 className="text-4xl font-bold mb-4 text-white">
            Start Free.{" "}
            <span style={{ color: "#4CBB17" }}>Scale as You Grow.</span>
          </h2>
          <p className="text-base max-w-lg mx-auto" style={{ color: "#A0A0A0" }}>
            No hidden fees. Cancel anytime.
            Switch to annual and save ~20%.
          </p>
        </motion.div>

        {/* ── Monthly / Annual toggle ──────────────────────────────── */}
        <motion.div
          initial={{ opacity: 0 }}
          whileInView={{ opacity: 1 }}
          viewport={{ once: true }}
          transition={{ duration: 0.4, delay: 0.2 }}
          className="flex items-center justify-center gap-3 mb-12"
        >
          <span
            className="text-sm font-medium"
            style={{ color: isMonthly ? "#fff" : "#A0A0A0" }}
          >
            Monthly
          </span>
          <Label htmlFor="billing-toggle">
            <Switch
              id="billing-toggle"
              ref={switchRef}
              checked={!isMonthly}
              onCheckedChange={handleToggle}
            />
          </Label>
          <span
            className="text-sm font-medium flex items-center gap-1.5"
            style={{ color: !isMonthly ? "#fff" : "#A0A0A0" }}
          >
            Annual
            <span
              className="inline-block text-xs font-semibold px-2 py-0.5 rounded-full"
              style={{
                backgroundColor: "#4CBB1720",
                color: "#4CBB17",
                border: "1px solid #4CBB1740",
              }}
            >
              Save 20%
            </span>
          </span>
        </motion.div>

        {/* ── Plan cards ──────────────────────────────────────────── */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 max-w-5xl mx-auto items-end">
          {PLANS.map((plan, index) => (
            <PricingCard
              key={plan.name}
              plan={plan}
              index={index}
              isMonthly={isMonthly}
              isDesktop={isDesktop}
            />
          ))}
        </div>

        {/* ── Bottom trust note ────────────────────────────────────── */}
        <motion.p
          initial={{ opacity: 0 }}
          whileInView={{ opacity: 1 }}
          viewport={{ once: true }}
          transition={{ duration: 0.4, delay: 0.5 }}
          className="text-center mt-10 text-sm"
          style={{ color: "#555555" }}
        >
          All plans include voice invoicing, WhatsApp delivery &amp; 7-day free trial on paid plans.
        </motion.p>
      </div>
    </section>
  );
}
