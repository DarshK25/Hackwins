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
      if (topic !== "ui_events") return;
      
      try {
        const raw = new TextDecoder().decode(payload);
        const message = JSON.parse(raw);
        if (message.type === "moneyops_ui_event") {
          dispatchUIEvent(message.payload, navigate);
        }
      } catch (err) {
        console.warn("Malformed UI event payload", err);
      }
    };
    
    room.on("dataReceived", onDataReceived);
    return () => { room.off("dataReceived", onDataReceived); };
  }, [room, navigate]);
}

function dispatchUIEvent(event, navigate) {
  const { type, variant, title, message, duration, actions } = event;
  
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

  if (event.badge) {
    window.dispatchEvent(new CustomEvent("voice:badge", { detail: event.badge }));
  }
}

function handleAction(action, navigate) {
  if (action.startsWith("navigate:")) {
    navigate(action.replace("navigate:", ""));
  }
}
