import { motion } from "framer-motion";
import { Mic, Zap, Send } from "lucide-react";
import { Timeline } from "@/components/ui/timeline";

// ── Step content cards ────────────────────────────────────────────────────

function StepCard({ icon: Icon, iconColor, headline, subheadline, body, badge }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 20, scale: 0.97 }}
      whileInView={{ opacity: 1, y: 0, scale: 1 }}
      viewport={{ once: true, amount: 0.2 }}
      transition={{ duration: 0.45, ease: "easeOut" }}
      className="rounded-2xl p-6 mb-0"
      style={{
        backgroundColor: "#131313",
        border: "1px solid #2A2A2A",
        boxShadow: "0 8px 40px rgba(0,0,0,0.6), 0 0 0 1px #1e1e1e",
      }}
    >
      {/* Icon + headline */}
      <div className="flex items-center gap-3 mb-3">
        <div
          className="w-11 h-11 rounded-xl flex items-center justify-center flex-shrink-0"
          style={{
            backgroundColor: `${iconColor}18`,
            border: `1px solid ${iconColor}35`,
          }}
        >
          <Icon className="w-5 h-5" style={{ color: iconColor }} />
        </div>
        <div>
          <p className="text-xs font-semibold uppercase tracking-widest" style={{ color: iconColor }}>
            {badge}
          </p>
          <h4 className="text-lg font-bold text-white leading-tight">{headline}</h4>
        </div>
      </div>

      {/* Sub-headline: speech bubble or code mock */}
      {subheadline && (
        <div
          className="rounded-xl px-4 py-3 mb-4 text-sm font-mono leading-relaxed"
          style={{
            backgroundColor: "#0A0A0A",
            border: "1px solid #2A2A2A",
            color: "#4CBB17",
          }}
        >
          {subheadline}
        </div>
      )}

      {/* Body lines */}
      <div className="space-y-2">
        {body.map((line, i) => (
          <p key={i} className="text-sm leading-relaxed" style={{ color: "#A0A0A0" }}>
            {line}
          </p>
        ))}
      </div>
    </motion.div>
  );
}

// ── Channel pills for Step 3 ──────────────────────────────────────────────
function ChannelPill({ emoji, label, color }) {
  return (
    <span
      className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-semibold"
      style={{
        backgroundColor: `${color}18`,
        border: `1px solid ${color}35`,
        color: color,
      }}
    >
      {emoji} {label}
    </span>
  );
}

// ── Timeline data ─────────────────────────────────────────────────────────

const steps = [
  {
    title: "01",
    content: (
      <StepCard
        icon={Mic}
        iconColor="#4CBB17"
        badge="Step 1"
        headline="Speak Your Invoice"
        subheadline={`"Create invoice for Rahul\n₹15,000 consulting\nDue next Friday"`}
        body={[
          "Just talk.",
          "No forms. No typing. Your voice converts directly into structured invoice data.",
        ]}
      />
    ),
  },
  {
    title: "02",
    content: (
      <StepCard
        icon={Zap}
        iconColor="#60A5FA"
        badge="Step 2"
        headline="Instant Invoice Creation"
        subheadline={`Preview → Edit → Confirm`}
        body={[
          "Review it, tweak any detail if needed, and confirm — all within the same flow.",
        ]}
      />
    ),
  },
  {
    title: "03",
    content: (
      <div>
        <StepCard
          icon={Send}
          iconColor="#A78BFA"
          badge="Step 3"
          headline="Send & Get Paid"
          subheadline={null}
          body={[
            "Deliver the invoice through your preferred channel"
          ]}
        />
        {/* Channel pills */}
        <motion.div
          initial={{ opacity: 0, y: 12 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.4, delay: 0.15 }}
          className="flex flex-wrap gap-2 mt-2 pl-1"
        >
          <ChannelPill emoji="" label="WhatsApp" color="#25D366" />
          <ChannelPill emoji="" label="Email" color="#60A5FA" />
          <ChannelPill emoji="" label="Payment Link" color="#A78BFA" />
        </motion.div>
      </div>
    ),
  },
];

// ── Section component ─────────────────────────────────────────────────────

export default function HowItWorks() {
  return (
    <section id="how-it-works" style={{ backgroundColor: "#0A0A0A" }}>
      {/* Section heading */}
      <div className="container mx-auto px-4 pt-24 pb-4">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.5 }}
          className="text-center"
        >
          <p
            className="text-xs font-semibold uppercase tracking-widest mb-3"
            style={{ color: "#4CBB17" }}
          >
            The Workflow
          </p>
          <h2 className="text-4xl font-bold mb-4 text-white">
            How MoneyOps{" "}
            <span style={{ color: "#4CBB17" }}>Works</span>
          </h2>
          <p className="text-base max-w-xl mx-auto" style={{ color: "#A0A0A0" }}>
            From voice to paid — three steps is all it takes.
          </p>
        </motion.div>
      </div>

      {/* Timeline */}
      <Timeline data={steps} />
    </section>
  );
}
