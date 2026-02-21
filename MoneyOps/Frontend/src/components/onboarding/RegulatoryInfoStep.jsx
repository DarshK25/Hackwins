import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
    Select,
    SelectContent,
    SelectItem,
    SelectTrigger,
    SelectValue,
} from "@/components/ui/select";
import { Switch } from "@/components/ui/switch";
import { Loader2 } from "lucide-react";

const INDIAN_STATES = [
    "Andhra Pradesh", "Arunachal Pradesh", "Assam", "Bihar", "Chhattisgarh",
    "Goa", "Gujarat", "Haryana", "Himachal Pradesh", "Jharkhand",
    "Karnataka", "Kerala", "Madhya Pradesh", "Maharashtra", "Manipur",
    "Meghalaya", "Mizoram", "Nagaland", "Odisha", "Punjab",
    "Rajasthan", "Sikkim", "Tamil Nadu", "Telangana", "Tripura",
    "Uttar Pradesh", "Uttarakhand", "West Bengal",
    "Delhi", "Puducherry", "Jammu and Kashmir", "Ladakh",
];

export function RegulatoryInfoStep({ initialData = {}, onNext, onBack, loading }) {
    const [formData, setFormData] = useState({
        panNumber: initialData.panNumber || "",
        gstRegistered: initialData.gstRegistered || false,
        gstin: initialData.gstin || "",
        gstFilingFrequency: initialData.gstFilingFrequency || "",
        stateOfRegistration: initialData.stateOfRegistration || "",
        tanNumber: initialData.tanNumber || "",
        cin: initialData.cin || "",
        llpin: initialData.llpin || "",
        msmeNumber: initialData.msmeNumber || "",
        iecCode: initialData.iecCode || "",
        professionalTaxReg: initialData.professionalTaxReg || "",
    });

    const handleSubmit = (e) => {
        e.preventDefault();
        onNext(formData);
    };

    const updateField = (field, value) =>
        setFormData((prev) => ({ ...prev, [field]: value }));

    return (
        <form onSubmit={handleSubmit} className="space-y-6">
            <div className="space-y-1">
                <h3 className="text-lg font-semibold">Regulatory Information</h3>
                <p className="text-sm text-muted-foreground">
                    Indian regulatory details. PAN is required, others are optional.
                </p>
            </div>

            {/* PAN + State */}
            <div className="grid gap-4 md:grid-cols-2">
                <div className="space-y-2">
                    <Label htmlFor="panNumber">PAN Number *</Label>
                    <Input
                        id="panNumber"
                        value={formData.panNumber}
                        onChange={(e) => updateField("panNumber", e.target.value.toUpperCase())}
                        required
                        placeholder="ABCDE1234F"
                        maxLength={10}
                        pattern="[A-Z]{5}[0-9]{4}[A-Z]{1}"
                    />
                </div>

                <div className="space-y-2">
                    <Label htmlFor="stateOfRegistration">State of Registration</Label>
                    <Select
                        value={formData.stateOfRegistration}
                        onValueChange={(v) => updateField("stateOfRegistration", v)}
                    >
                        <SelectTrigger id="stateOfRegistration">
                            <SelectValue placeholder="Select state" />
                        </SelectTrigger>
                        <SelectContent>
                            {INDIAN_STATES.map((state) => (
                                <SelectItem key={state} value={state}>
                                    {state}
                                </SelectItem>
                            ))}
                        </SelectContent>
                    </Select>
                </div>
            </div>

            {/* GST Section */}
            <div className="space-y-4 p-4 border rounded-lg bg-muted/30">
                <div className="flex items-center justify-between">
                    <Label htmlFor="gstRegistered" className="cursor-pointer">
                        GST Registered?
                    </Label>
                    <Switch
                        id="gstRegistered"
                        checked={formData.gstRegistered}
                        onCheckedChange={(v) => updateField("gstRegistered", v)}
                    />
                </div>

                {formData.gstRegistered && (
                    <div className="grid gap-4 md:grid-cols-2">
                        <div className="space-y-2">
                            <Label htmlFor="gstin">GSTIN *</Label>
                            <Input
                                id="gstin"
                                value={formData.gstin}
                                onChange={(e) => updateField("gstin", e.target.value.toUpperCase())}
                                required={formData.gstRegistered}
                                placeholder="22AAAAA0000A1Z5"
                                maxLength={15}
                            />
                        </div>

                        <div className="space-y-2">
                            <Label htmlFor="gstFilingFrequency">GST Filing Frequency *</Label>
                            <Select
                                value={formData.gstFilingFrequency}
                                onValueChange={(v) => updateField("gstFilingFrequency", v)}
                            >
                                <SelectTrigger id="gstFilingFrequency">
                                    <SelectValue placeholder="Select frequency" />
                                </SelectTrigger>
                                <SelectContent>
                                    <SelectItem value="monthly">Monthly</SelectItem>
                                    <SelectItem value="quarterly">Quarterly</SelectItem>
                                </SelectContent>
                            </Select>
                        </div>
                    </div>
                )}
            </div>

            {/* Optional IDs */}
            <div className="grid gap-4 md:grid-cols-2">
                <div className="space-y-2">
                    <Label htmlFor="tanNumber">TAN Number (Optional)</Label>
                    <Input
                        id="tanNumber"
                        value={formData.tanNumber}
                        onChange={(e) => updateField("tanNumber", e.target.value.toUpperCase())}
                        placeholder="ABCD12345E"
                    />
                </div>

                <div className="space-y-2">
                    <Label htmlFor="cin">CIN / LLPIN (Optional)</Label>
                    <Input
                        id="cin"
                        value={formData.cin || formData.llpin}
                        onChange={(e) => {
                            const val = e.target.value.toUpperCase();
                            if (val.startsWith("L") || val.startsWith("U")) {
                                updateField("cin", val);
                            } else {
                                updateField("llpin", val);
                            }
                        }}
                        placeholder="L12345MH2020PTC123456"
                    />
                </div>
            </div>

            <div className="flex justify-between">
                <Button type="button" variant="outline" onClick={onBack} disabled={loading}>
                    ← Back
                </Button>
                <Button type="submit" disabled={loading}>
                    {loading ? (
                        <Loader2 className="h-4 w-4 animate-spin" />
                    ) : (
                        "Next: Business Context →"
                    )}
                </Button>
            </div>
        </form>
    );
}
