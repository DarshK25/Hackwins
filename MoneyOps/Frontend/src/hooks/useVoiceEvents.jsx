import { useRoomContext } from "@livekit/components-react";
import { useEffect } from "react";
import { toast } from "sonner";
import { useNavigate } from "react-router-dom";

export function useVoiceEvents() {
  const room = useRoomContext();
  const navigate = useNavigate();
  
  useEffect(() => {
    if (!room) return;
    
    const onDataReceived = (payload, participant, kind, topic) => {
      console.log(`[VoiceEvents] Received packet on topic: ${topic}`, { kind, participantIdentity: participant?.identity });
      
      try {
        const raw = new TextDecoder().decode(payload);
        const message = JSON.parse(raw);
        console.log("[VoiceEvents] Parsed message:", message);

        // Handle direct UI events
        if (topic === "ui_events" && message.type === "moneyops_ui_event") {
          dispatchUIEvent(message.payload, navigate);
        }
        
        // Also handle UI events nested in gateway results (fallback/sync)
        if (topic === "gateway_results" && message.ui_event) {
          console.log("[VoiceEvents] Handling nested UI event from gateway_results");
          dispatchUIEvent(message.ui_event, navigate);
        }
      } catch (err) {
        console.warn("[VoiceEvents] Malformed payload", err);
      }
    };
    
    room.on("dataReceived", onDataReceived);
    return () => { room.off("dataReceived", onDataReceived); };
  }, [room, navigate]);
}

function dispatchUIEvent(event, navigate) {
  const { type, variant, title, message, duration, actions } = event;
  
  // Custom deep-link handler for invoice creation
  if (type === "invoice_created") {
    toast.success(
      <div className="flex flex-col gap-1">
        <span className="font-semibold text-sm">Invoice Created ✓</span>
        <span className="text-xs text-white/70">{event.invoice_number} · {event.client_name}</span>
        <span className="text-xs font-semibold">₹{Number(event.total).toLocaleString('en-IN')}</span>
        <button
          onClick={() => navigate(`/invoices/${event.invoice_id}`)}
          className="mt-1.5 py-1 px-2.5 rounded bg-white/10 hover:bg-white/20 text-[10px] font-medium transition-colors text-left w-fit"
        >
          View Invoice →
        </button>
      </div>,
      { 
        duration: 8000, 
        id: "invoice-created",
        className: "bg-[#111] border border-white/10 text-white"
      }
    );
    return;
  }

  const primaryAction = actions?.[0];
  const toastAction = primaryAction?.action ? {
    label: primaryAction.label,
    onClick: () => handleAction(primaryAction.action, navigate)
  } : undefined;

  // Dismiss any existing loading/progress toast first
  if (variant === "success" || variant === "error") {
    toast.dismiss("voice-progress");
  }

  if (type === "toast" || type === "progress" || type === "notification") {
    const opts = {
      description: message,
      duration: duration ?? 4000,
      action: toastAction,
      id: variant === "progress" || variant === "loading" ? "voice-progress" : undefined,
    };

    switch (variant) {
      case "success": toast.success(title, opts); break;
      case "error":   toast.error(title, { ...opts, duration: duration ?? 6000 }); break;
      case "warning": toast.warning(title, opts); break;
      case "progress":
      case "loading": toast.loading(title, opts); break;
      default:        toast.info(title, opts); break;
    }
  }

  if (type === "confirmation") {
    window.dispatchEvent(new CustomEvent("voice:confirmation", { detail: event }));
  }

  if (type === "open_input_dialog") {
    window.dispatchEvent(new CustomEvent("voice:open_input_dialog", { detail: event }));
  }

  if (type === "client_created") {
    window.dispatchEvent(new CustomEvent("voice:client-created", { detail: event }));
  }

  if (event.badge) {
    window.dispatchEvent(new CustomEvent("voice:badge", { detail: event.badge }));
  }
}

function handleAction(action, navigate) {
  if (action.startsWith("navigate:")) {
    navigate(action.replace("navigate:", ""));
  }
}
