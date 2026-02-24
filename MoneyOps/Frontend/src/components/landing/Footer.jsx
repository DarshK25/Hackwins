export default function Footer() {
    return (
        <footer
            className="py-12 text-center"
            style={{ borderTop: "1px solid #2A2A2A", backgroundColor: "#000" }}
        >
            <div className="flex justify-center items-center gap-2.5 mb-3">
                {/* MoneyOps logo mark */}
                <div
                    className="flex items-center justify-center rounded-md"
                    style={{ width: 24, height: 24, backgroundColor: "#4CBB17", flexShrink: 0 }}
                >
                    <svg viewBox="0 0 32 32" width="16" height="16" fill="none">
                        <path d="M10 22 L14 14 L18 18 L22 10" stroke="#000" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round" />
                        <path d="M19 10 L22 10 L22 13" stroke="#000" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round" />
                    </svg>
                </div>
                <span className="text-lg font-bold text-white">
                    Money<span style={{ color: "#4CBB17" }}>Ops</span>
                </span>
            </div>
            <p className="text-sm mb-2" style={{ color: "#A0A0A0" }}>
                Enterprise AI Finance — built for operators who move fast.
            </p>
            <p className="text-xs" style={{ color: "#555" }}>
                © {new Date().getFullYear()} MoneyOps. All rights reserved.
            </p>
        </footer>
    );
}
