import { useState } from 'react';
import { createPortal } from 'react-dom';
import { motion, AnimatePresence } from 'framer-motion';
import { X, Save, Phone, Mail, MapPin, Hash, User, IndianRupee, Calendar, FileText, Percent } from 'lucide-react';

export default function ClientInputDialog({ dialog, onSubmit, onClose }) {
  const [values, setValues] = useState({});
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleSubmit = async () => {
    setIsSubmitting(true);
    try {
      const res = await fetch(dialog.submit_endpoint, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          session_id: dialog.session_id,
          dialog_id: dialog.dialog_id,
          fields: values
        })
      });
      const data = await res.json();
      if (data.ui_event) {
        window.dispatchEvent(new CustomEvent("voice:" + data.ui_event.type.replace('_', '-'), { detail: data.ui_event }));
      }
      onSubmit(data);
      onClose();
    } catch (err) {
      console.error("Failed to submit dialog", err);
    } finally {
      setIsSubmitting(false);
    }
  };

  const getIcon = (id) => {
    switch (id) {
      case 'phone': case 'phoneNumber': return <Phone className="h-4 w-4" />;
      case 'email': return <Mail className="h-4 w-4" />;
      case 'address': return <MapPin className="h-4 w-4" />;
      case 'gst_number': case 'taxId': case 'tax_id': return <Hash className="h-4 w-4" />;
      case 'client_name': case 'name': case 'company_name': return <User className="h-4 w-4" />;
      case 'amount': case 'total_amount': return <IndianRupee className="h-4 w-4" />;
      case 'due_date': case 'issue_date': return <Calendar className="h-4 w-4" />;
      case 'service_description': case 'description': case 'notes': return <FileText className="h-4 w-4" />;
      case 'gst_percent': case 'gst': return <Percent className="h-4 w-4" />;
      default: return null;
    }
  };

  const dialogContent = (
    <div className="fixed inset-0 bg-black/80 backdrop-blur-md flex items-center justify-center z-[9999] p-4">
      <motion.div 
        initial={{ opacity: 0, scale: 0.9, y: 20 }}
        animate={{ opacity: 1, scale: 1, y: 0 }}
        exit={{ opacity: 0, scale: 0.9, y: 20 }}
        className="bg-[#111] border border-white/10 rounded-2xl p-6 w-full max-w-sm shadow-2xl space-y-5"
      >
        <div className="flex justify-between items-start">
          <div className="space-y-1">
            <h2 className="text-white text-lg font-semibold tracking-tight">{dialog.title || 'Review Details'}</h2>
            <p className="text-white/40 text-xs leading-relaxed">{dialog.message || 'Check the details and update if needed.'}</p>
          </div>
          <button onClick={onClose} className="text-white/20 hover:text-white transition-colors">
            <X className="h-5 w-5" />
          </button>
        </div>

        <div className="space-y-4 max-h-[60vh] overflow-y-auto px-1 -mx-1 scrollbar-none">
          {dialog.fields.map(field => (
            <div key={field.id} className="space-y-1.5">
              <label className="text-white/60 text-[11px] font-medium uppercase tracking-wider flex items-center gap-2">
                {getIcon(field.id)}
                {field.label}
              </label>
              {field.type === 'textarea' ? (
                <textarea 
                  className="w-full bg-white/[0.03] text-white rounded-xl px-4 py-2.5 text-sm border border-white/10 focus:border-blue-500/50 focus:bg-white/[0.05] outline-none transition-all resize-none"
                  defaultValue={field.defaultValue || values[field.id] || ''}
                  onChange={e => setValues(v => ({...v, [field.id]: e.target.value}))}
                  placeholder={field.placeholder || ''} 
                  rows={2} 
                />
              ) : (
                <input 
                  type={field.type} 
                  className="w-full bg-white/[0.03] text-white rounded-xl px-4 py-2.5 text-sm border border-white/10 focus:border-blue-500/50 focus:bg-white/[0.05] outline-none transition-all"
                  defaultValue={field.defaultValue || values[field.id] || ''}
                  onChange={e => setValues(v => ({...v, [field.id]: e.target.value}))}
                  placeholder={field.placeholder || ''} 
                />
              )}
            </div>
          ))}
        </div>

        <div className="flex gap-3 pt-2">
          <button 
            onClick={handleSubmit} 
            disabled={isSubmitting}
            className="flex-1 bg-blue-600 hover:bg-blue-500 text-white rounded-xl py-3 text-sm font-semibold transition-all flex items-center justify-center gap-2 disabled:opacity-50"
          >
            {isSubmitting ? <span className="animate-spin text-lg">◌</span> : <Save className="h-4 w-4" />}
            {dialog.submit_btn_label || 'Update Draft'}
          </button>
          <button 
            onClick={onClose} 
            className="flex-1 bg-white/5 hover:bg-white/10 text-white/70 rounded-xl py-3 text-sm font-medium transition-all"
          >
            {dialog.cancel_btn_label || 'Close'}
          </button>
        </div>
      </motion.div>
    </div>
  );

  return createPortal(dialogContent, document.body);
}
