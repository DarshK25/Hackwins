import { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { 
  X, Mail, Phone, MapPin, Building, Hash, 
  Calendar, DollarSign, FileText, Plus, 
  Edit2, Save, Trash2, ArrowUpRight, TrendingUp, AlertCircle
} from 'lucide-react';
import { toast } from 'sonner';
import { useAuth } from '@clerk/clerk-react';

export default function ClientDetailDialog({ client, onClose, onUpdate, onDelete, internalUserId, internalOrgId }) {
  const { getToken } = useAuth();
  const [invoices, setInvoices] = useState([]);
  const [loadingInvoices, setLoadingInvoices] = useState(true);
  const [isEditMode, setIsEditMode] = useState(false);
  const [formData, setFormData] = useState({ ...client });
  const [isSaving, setIsSaving] = useState(false);

  useEffect(() => {
    if (client?.id || client?._id) {
       fetchInvoices();
    }
  }, [client]);

  const fetchInvoices = async () => {
    try {
      setLoadingInvoices(true);
      const token = await getToken();
      const id = client.id || client._id;
      const res = await fetch(`/api/invoices?clientId=${id}`, {
        headers: {
          'Authorization': `Bearer ${token}`,
          'X-User-Id': internalUserId,
          'X-Org-Id': internalOrgId
        }
      });
      if (!res.ok) throw new Error("Failed to fetch invoices");
      const data = await res.json();
      setInvoices(data);
    } catch (err) {
      console.error(err);
    } finally {
      setLoadingInvoices(false);
    }
  };

  const handleSave = async () => {
    setIsSaving(true);
    try {
      const token = await getToken();
      const id = client.id || client._id;
      const res = await fetch(`/api/clients/${id}`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`,
          'X-User-Id': internalUserId,
          'X-Org-Id': internalOrgId
        },
        body: JSON.stringify(formData)
      });
      if (!res.ok) throw new Error("Update failed");
      const updated = await res.json();
      onUpdate(updated);
      setIsEditMode(false);
      toast.success("Client updated successfully");
    } catch (err) {
      toast.error(err.message);
    } finally {
      setIsSaving(false);
    }
  };

  const totalBilled = invoices.reduce((sum, inv) => sum + (inv.totalAmount || 0), 0);
  const totalPaid = invoices.filter(inv => inv.status === 'PAID').reduce((sum, inv) => sum + (inv.totalAmount || 0), 0);
  const overdueAmount = invoices.filter(inv => inv.status === 'OVERDUE').reduce((sum, inv) => sum + (inv.totalAmount || 0), 0);

  return (
    <div className="fixed inset-0 z-[100] flex justify-end bg-black/40 backdrop-blur-[2px]">
      <motion.div 
        initial={{ x: '100%' }}
        animate={{ x: 0 }}
        exit={{ x: '100%' }}
        transition={{ type: 'spring', damping: 25, stiffness: 200 }}
        className="w-full max-w-[480px] bg-[#0d0d0d] border-l border-white/10 shadow-2xl h-full flex flex-col overflow-hidden"
      >
        {/* Header */}
        <div className="p-6 border-b border-white/10 flex items-center justify-between bg-white/[0.02]">
          <div className="flex items-center gap-4">
            <div className="h-12 w-12 rounded-2xl bg-blue-500/10 border border-blue-500/20 flex items-center justify-center">
              <Building className="h-6 w-6 text-blue-500" />
            </div>
            <div>
              <h2 className="text-xl font-bold text-white tracking-tight">{isEditMode ? 'Edit Client' : client.name}</h2>
              <p className="text-xs text-white/40 font-medium uppercase tracking-wider">
                {isEditMode ? 'Modify client profile' : `ID: ${client.id?.slice(0,8)}...`}
              </p>
            </div>
          </div>
          <button onClick={onClose} className="p-2 hover:bg-white/5 rounded-full transition-colors">
            <X className="h-5 w-5 text-white/40" />
          </button>
        </div>

        <div className="flex-1 overflow-y-auto custom-scrollbar p-6 space-y-8">
          {/* Quick Stats */}
          {!isEditMode && (
            <div className="grid grid-cols-3 gap-3">
              <div className="bg-white/[0.03] border border-white/5 rounded-2xl p-4 space-y-1">
                <p className="text-[10px] text-white/30 uppercase font-bold tracking-widest">Billed</p>
                <p className="text-lg font-bold text-white">₹{totalBilled.toLocaleString()}</p>
              </div>
              <div className="bg-[#4CBB17]/5 border border-[#4CBB17]/10 rounded-2xl p-4 space-y-1">
                <p className="text-[10px] text-[#4CBB17]/50 uppercase font-bold tracking-widest">Paid</p>
                <p className="text-lg font-bold text-[#4CBB17]">₹{totalPaid.toLocaleString()}</p>
              </div>
              <div className="bg-red-500/5 border border-red-500/10 rounded-2xl p-4 space-y-1">
                <p className="text-[10px] text-red-500/50 uppercase font-bold tracking-widest">Overdue</p>
                <p className="text-lg font-bold text-red-500">₹{overdueAmount.toLocaleString()}</p>
              </div>
            </div>
          )}

          {/* Form / Details */}
          <div className="space-y-6">
            <Section title="Basic Information">
              <div className="space-y-4">
                <Field 
                  label="Name" 
                  value={formData.name} 
                  edit={isEditMode} 
                  onChange={v => setFormData({ ...formData, name: v })} 
                  icon={Building} 
                />
                <Field 
                  label="Email" 
                  value={formData.email} 
                  edit={isEditMode} 
                  onChange={v => setFormData({ ...formData, email: v })} 
                  icon={Mail} 
                />
                <Field 
                  label="Phone" 
                  value={formData.phoneNumber || formData.phone} 
                  edit={isEditMode} 
                  onChange={v => setFormData({ ...formData, phoneNumber: v })} 
                  icon={Phone} 
                />
                <Field 
                  label="GSTIN / Tax ID" 
                  value={formData.taxId || formData.gstin} 
                  edit={isEditMode} 
                  onChange={v => setFormData({ ...formData, taxId: v })} 
                  icon={Hash} 
                />
              </div>
            </Section>

            <Section title="Company Address">
               <div className="space-y-4">
                 <Field 
                    label="Full Address" 
                    value={formData.address} 
                    edit={isEditMode} 
                    onChange={v => setFormData({ ...formData, address: v })} 
                    icon={MapPin} 
                    type="textarea"
                  />
                  <div className="grid grid-cols-2 gap-4">
                    <Field 
                      label="City" 
                      value={formData.city} 
                      edit={isEditMode} 
                      onChange={v => setFormData({ ...formData, city: v })} 
                    />
                    <Field 
                      label="State" 
                      value={formData.state} 
                      edit={isEditMode} 
                      onChange={v => setFormData({ ...formData, state: v })} 
                    />
                  </div>
               </div>
            </Section>

            <Section title="Internal Notes">
              <Field 
                label="Notes" 
                value={formData.notes} 
                edit={isEditMode} 
                onChange={v => setFormData({ ...formData, notes: v })} 
                type="textarea"
              />
            </Section>

            {/* Invoices List */}
            {!isEditMode && (
              <Section title={`Invoices (${invoices.length})`}>
                <div className="space-y-3">
                  {loadingInvoices ? (
                    <div className="flex justify-center p-8"><span className="animate-spin text-white/20">◌</span></div>
                  ) : invoices.length === 0 ? (
                    <div className="bg-white/[0.02] border border-dashed border-white/5 rounded-2xl p-8 text-center text-white/20 text-sm">
                      No invoices found for this client.
                    </div>
                  ) : (
                    invoices.map(inv => (
                      <div key={inv.id} className="bg-white/[0.03] border border-white/5 rounded-xl p-3 flex items-center justify-between group hover:bg-white/[0.05] transition-colors">
                        <div className="flex items-center gap-3">
                          <div className="h-8 w-8 rounded-lg bg-white/5 flex items-center justify-center">
                            <FileText className="h-4 w-4 text-white/40" />
                          </div>
                          <div>
                            <p className="text-xs font-semibold text-white">{inv.invoiceNumber}</p>
                            <p className="text-[10px] text-white/40">{new Date(inv.createdAt).toLocaleDateString()}</p>
                          </div>
                        </div>
                        <div className="text-right flex items-center gap-4">
                          <div>
                            <p className="text-xs font-bold text-white">₹{inv.totalAmount.toLocaleString()}</p>
                            <StatusBadge status={inv.status} />
                          </div>
                          <ArrowUpRight className="h-4 w-4 text-white/10 group-hover:text-white transition-colors" />
                        </div>
                      </div>
                    ))
                  )}
                  <button className="w-full py-3 rounded-xl border border-dashed border-white/10 text-white/40 text-xs font-bold hover:border-white/20 hover:text-white transition-all flex items-center justify-center gap-2">
                    <Plus className="h-4 w-4" /> Create New Invoice
                  </button>
                </div>
              </Section>
            )}
          </div>
        </div>

        {/* Footer Actions */}
        <div className="p-6 border-t border-white/10 bg-white/[0.02] flex gap-3">
          {isEditMode ? (
            <>
              <button 
                onClick={handleSave} 
                disabled={isSaving}
                className="flex-1 bg-blue-600 hover:bg-blue-500 text-white rounded-xl py-3 text-sm font-semibold transition-all flex items-center justify-center gap-2"
              >
                {isSaving ? <span className="animate-spin">◌</span> : <Save className="h-4 w-4" />}
                Save Changes
              </button>
              <button 
                onClick={() => setIsEditMode(false)} 
                className="flex-1 bg-white/5 hover:bg-white/10 text-white/70 rounded-xl py-3 text-sm font-medium transition-all"
              >
                Cancel
              </button>
            </>
          ) : (
            <>
              <button 
                onClick={() => setIsEditMode(true)} 
                className="flex-1 bg-white/[0.05] hover:bg-white/[0.08] text-white rounded-xl py-3 text-sm font-bold transition-all border border-white/5 flex items-center justify-center gap-2"
              >
                <Edit2 className="h-4 w-4" /> Edit Profile
              </button>
              <button 
                onClick={() => onDelete(client)}
                className="px-4 py-3 bg-red-500/10 hover:bg-red-500/20 text-red-500 rounded-xl transition-all border border-red-500/20"
              >
                <Trash2 className="h-4 w-4" />
              </button>
            </>
          )}
        </div>
      </motion.div>
    </div>
  );
}

function Section({ title, children }) {
  return (
    <div className="space-y-3">
      <h3 className="text-[10px] text-white/30 uppercase font-black tracking-[0.15em] ml-1">{title}</h3>
      <div className="space-y-4">{children}</div>
    </div>
  );
}

function Field({ label, value, edit, onChange, icon: Icon, type = 'text' }) {
  if (edit) {
    return (
      <div className="space-y-1.5 flex-1">
        <label className="text-[10px] text-white/40 font-bold ml-1">{label}</label>
        {type === 'textarea' ? (
          <textarea 
            className="w-full bg-white/[0.03] border border-white/10 rounded-xl px-4 py-2.5 text-sm text-white focus:border-blue-500/50 outline-none transition-all resize-none"
            value={value || ''}
            onChange={e => onChange(e.target.value)}
            rows={3}
          />
        ) : (
          <input 
            className="w-full bg-white/[0.03] border border-white/10 rounded-xl px-4 py-2.5 text-sm text-white focus:border-blue-500/50 outline-none transition-all"
            value={value || ''}
            onChange={e => onChange(e.target.value)}
          />
        )}
      </div>
    );
  }

  return (
    <div className="flex items-start gap-3 flex-1 group">
      {Icon && <div className="mt-1 h-7 w-7 rounded-lg bg-white/[0.02] border border-white/5 flex items-center justify-center group-hover:bg-white/5 transition-colors">
        <Icon className="h-3.5 w-3.5 text-white/30 group-hover:text-white/60" />
      </div>}
      <div className="flex-1">
        <p className="text-[10px] text-white/30 font-bold mb-0.5 tracking-wide">{label}</p>
        <p className="text-sm text-white/80 break-words line-clamp-2">{value || <span className="text-white/10 italic">Not set</span>}</p>
      </div>
    </div>
  );
}

function StatusBadge({ status }) {
  const styles = {
    'PAID': 'text-[#4CBB17]',
    'SENT': 'text-blue-400',
    'DRAFT': 'text-white/40',
    'OVERDUE': 'text-red-500'
  };
  return <span className={`text-[9px] font-black uppercase tracking-widest ${styles[status] || 'text-white/40'}`}>{status}</span>;
}
