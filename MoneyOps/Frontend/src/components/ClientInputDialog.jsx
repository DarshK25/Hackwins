import { useEffect, useMemo, useState } from 'react';
import { createPortal } from 'react-dom';
import { motion, AnimatePresence } from 'framer-motion';
import { X, Save, Phone, Mail, MapPin, Hash, User, IndianRupee, Calendar, FileText, Percent, Plus, Trash2 } from 'lucide-react';

const EMPTY_INVOICE_ROW = {
  type: 'SERVICE',
  description: '',
  quantity: '1',
  rate: '',
  gst: '18',
};

function parseInvoiceItemsText(rawText) {
  return String(rawText || '')
    .split('\n')
    .map((line) => line.trim())
    .filter(Boolean)
    .map((line) => {
      const [type, description, quantity, rate, gst] = line.split('|').map((part) => part.trim());
      return {
        type: type || 'SERVICE',
        description: description || '',
        quantity: quantity || '1',
        rate: rate || '',
        gst: gst || '18',
      };
    });
}

function formatInvoiceItemsText(rows) {
  return rows
    .map((row) => {
      const type = String(row.type || 'SERVICE').trim() || 'SERVICE';
      const description = String(row.description || '').trim();
      const quantity = String(row.quantity || '1').trim() || '1';
      const rate = String(row.rate || '').trim();
      const gst = String(row.gst || '18').trim() || '18';
      if (!description && !rate) return '';
      return [type, description, quantity, rate, gst].join(' | ');
    })
    .filter(Boolean)
    .join('\n');
}

export default function ClientInputDialog({ dialog, onSubmit, onClose }) {
  const [values, setValues] = useState({});
  const [isSubmitting, setIsSubmitting] = useState(false);
  const isInvoicePreview = dialog?.dialog_id === 'invoice_preview_form';

  useEffect(() => {
    setValues({});
  }, [dialog?.dialog_id, dialog?.session_id]);

  const invoiceItemsField = useMemo(
    () => dialog?.fields?.find((field) => field.id === 'invoice_items_text'),
    [dialog?.fields]
  );

  const invoiceRows = useMemo(() => {
    if (!isInvoicePreview) return [];
    const currentValue = values.invoice_items_text ?? invoiceItemsField?.defaultValue ?? '';
    const rows = parseInvoiceItemsText(currentValue);
    return rows.length ? rows : [{ ...EMPTY_INVOICE_ROW }];
  }, [isInvoicePreview, values.invoice_items_text, invoiceItemsField?.defaultValue]);

  const updateInvoiceRows = (nextRows) => {
    setValues((prev) => ({
      ...prev,
      invoice_items_text: formatInvoiceItemsText(nextRows),
    }));
  };

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
        window.dispatchEvent(new CustomEvent("voice:manual_ui_event", { detail: data.ui_event }));
      }
      onSubmit(data);
      if (data?.ui_event?.type !== "open_input_dialog") {
        onClose();
      }
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

  const renderInvoiceRowsEditor = () => (
    <div className="space-y-3">
      <div className="hidden gap-2 px-2 text-[10px] font-semibold uppercase tracking-[0.18em] text-white/35 md:grid md:grid-cols-[92px_minmax(0,1fr)_68px_88px_68px_40px]">
        <span>Type</span>
        <span>Description</span>
        <span>Qty</span>
        <span>Rate</span>
        <span>GST %</span>
        <span />
      </div>
      <div className="space-y-2">
        {invoiceRows.map((row, index) => (
          <div
            key={`invoice-row-${index}`}
            className="grid gap-2 rounded-2xl border border-white/8 bg-white/[0.035] p-3 md:grid-cols-[92px_minmax(0,1fr)_68px_88px_68px_40px]"
          >
            <input
              type="text"
              className="w-full rounded-xl border border-white/10 bg-black/20 px-3 py-2 text-sm text-white outline-none transition-all focus:border-[#4CBB17]/60"
              value={row.type}
              onChange={(e) => {
                const nextRows = invoiceRows.map((item, rowIndex) =>
                  rowIndex === index ? { ...item, type: e.target.value.toUpperCase() } : item
                );
                updateInvoiceRows(nextRows);
              }}
              placeholder="SERVICE"
            />
            <input
              type="text"
              className="w-full rounded-xl border border-white/10 bg-black/20 px-3 py-2 text-sm text-white outline-none transition-all focus:border-[#4CBB17]/60"
              value={row.description}
              onChange={(e) => {
                const nextRows = invoiceRows.map((item, rowIndex) =>
                  rowIndex === index ? { ...item, description: e.target.value } : item
                );
                updateInvoiceRows(nextRows);
              }}
              placeholder="Service or item description"
            />
            <input
              type="number"
              min="1"
              className="w-full rounded-xl border border-white/10 bg-black/20 px-3 py-2 text-sm text-white outline-none transition-all focus:border-[#4CBB17]/60"
              value={row.quantity}
              onChange={(e) => {
                const nextRows = invoiceRows.map((item, rowIndex) =>
                  rowIndex === index ? { ...item, quantity: e.target.value } : item
                );
                updateInvoiceRows(nextRows);
              }}
              placeholder="1"
            />
            <input
              type="number"
              min="0"
              className="w-full rounded-xl border border-white/10 bg-black/20 px-3 py-2 text-sm text-white outline-none transition-all focus:border-[#4CBB17]/60"
              value={row.rate}
              onChange={(e) => {
                const nextRows = invoiceRows.map((item, rowIndex) =>
                  rowIndex === index ? { ...item, rate: e.target.value } : item
                );
                updateInvoiceRows(nextRows);
              }}
              placeholder="50000"
            />
            <input
              type="number"
              min="0"
              className="w-full rounded-xl border border-white/10 bg-black/20 px-3 py-2 text-sm text-white outline-none transition-all focus:border-[#4CBB17]/60"
              value={row.gst}
              onChange={(e) => {
                const nextRows = invoiceRows.map((item, rowIndex) =>
                  rowIndex === index ? { ...item, gst: e.target.value } : item
                );
                updateInvoiceRows(nextRows);
              }}
              placeholder="18"
            />
            <button
              type="button"
              onClick={() => {
                const nextRows = invoiceRows.filter((_, rowIndex) => rowIndex !== index);
                updateInvoiceRows(nextRows.length ? nextRows : [{ ...EMPTY_INVOICE_ROW }]);
              }}
              className="flex h-10 w-10 items-center justify-center rounded-xl border border-white/10 bg-white/[0.04] text-white/45 transition-colors hover:border-[#CD1C18]/50 hover:text-[#CD1C18]"
              aria-label="Remove line item"
            >
              <Trash2 className="h-4 w-4" />
            </button>
          </div>
        ))}
      </div>
      <button
        type="button"
        onClick={() => updateInvoiceRows([...invoiceRows, { ...EMPTY_INVOICE_ROW }])}
        className="inline-flex items-center gap-2 rounded-xl border border-white/10 bg-white/[0.05] px-3 py-2 text-sm font-medium text-white/80 transition-colors hover:border-[#4CBB17]/40 hover:text-white"
      >
        <Plus className="h-4 w-4" />
        Add Line Item
      </button>
    </div>
  );

  const renderField = (field) => (
    <div key={field.id} className="space-y-1.5">
      <label className="text-white/60 text-[11px] font-medium uppercase tracking-wider flex items-center gap-2">
        {getIcon(field.id)}
        {field.label}
      </label>
      {isInvoicePreview && field.id === 'invoice_items_text' ? (
        renderInvoiceRowsEditor()
      ) : field.type === 'textarea' ? (
        <textarea
          className="w-full bg-white/[0.03] text-white rounded-xl px-4 py-2.5 text-sm border border-white/10 focus:border-blue-500/50 focus:bg-white/[0.05] outline-none transition-all resize-none"
          value={values[field.id] ?? field.defaultValue ?? ''}
          onChange={e => setValues(v => ({ ...v, [field.id]: e.target.value }))}
          placeholder={field.placeholder || ''}
          rows={isInvoicePreview && field.id === 'invoice_items_text' ? 8 : 2}
        />
      ) : (
        <input
          type={field.type}
          className="w-full bg-white/[0.03] text-white rounded-xl px-4 py-2.5 text-sm border border-white/10 focus:border-blue-500/50 focus:bg-white/[0.05] outline-none transition-all"
          value={values[field.id] ?? field.defaultValue ?? ''}
          onChange={e => setValues(v => ({ ...v, [field.id]: e.target.value }))}
          placeholder={field.placeholder || ''}
        />
      )}
    </div>
  );

  const dialogContent = isInvoicePreview ? (
    <div className="fixed inset-0 z-[9999] pointer-events-none">
      <div className="pointer-events-auto fixed left-6 top-1/2 -translate-y-1/2">
        <motion.div
          initial={{ opacity: 0, x: -36, scale: 0.97 }}
          animate={{ opacity: 1, x: 0, scale: 1 }}
          exit={{ opacity: 0, x: -36, scale: 0.97 }}
          className="w-[min(560px,calc(100vw-48px))] max-w-[560px] rounded-[26px] border border-white/10 bg-[#111111]/95 shadow-2xl backdrop-blur-2xl"
          style={{
            boxShadow: "0 20px 60px rgba(0,0,0,0.5), 0 0 40px rgba(76,187,23,0.08)",
          }}
        >
        <div className="flex max-h-[58vh] flex-col">
          <div className="flex items-start justify-between border-b border-white/10 px-6 py-5">
            <div className="space-y-1">
              <p className="text-[10px] font-semibold uppercase tracking-[0.22em] text-[#4CBB17]/80">Voice Sync Active</p>
              <h2 className="text-white text-xl font-semibold tracking-tight">{dialog.title || 'Live Invoice Preview'}</h2>
              <p className="text-white/45 text-xs leading-relaxed max-w-[320px]">
                {dialog.message || 'Check the details and update if needed.'}
              </p>
            </div>
            <button onClick={onClose} className="text-white/20 hover:text-white transition-colors">
              <X className="h-5 w-5" />
            </button>
          </div>

          <div className="flex-1 overflow-y-auto px-6 py-5 scrollbar-none">
            <div className="grid gap-4 md:grid-cols-3">
              {dialog.fields
                .filter((field) => field.id !== 'invoice_items_text' && field.id !== 'notes')
                .map(renderField)}
            </div>

            <div className="mt-5 space-y-4">
              {dialog.fields.filter((field) => field.id === 'invoice_items_text').map(renderField)}
            </div>

            <div className="mt-5">
              {dialog.fields.filter((field) => field.id === 'notes').map(renderField)}
            </div>
          </div>

          <div className="border-t border-white/10 px-6 py-4">
            <div className="flex gap-3">
              <button
                onClick={handleSubmit}
                disabled={isSubmitting}
                className="flex-1 rounded-xl border border-[#4CBB17]/35 bg-[#4CBB17]/14 py-3 text-sm font-semibold text-[#d9ffe2] transition-all flex items-center justify-center gap-2 disabled:opacity-50 hover:bg-[#4CBB17]/20"
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
          </div>
        </div>
        </motion.div>
      </div>
    </div>
  ) : (
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
          {dialog.fields.map(renderField)}
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
