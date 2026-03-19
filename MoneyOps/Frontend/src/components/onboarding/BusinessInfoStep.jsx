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
import { Textarea } from "@/components/ui/textarea";
import { Loader2 } from "lucide-react";

export function BusinessInfoStep({ initialData = {}, onNext, loading }) {
    const [formData, setFormData] = useState({
        legalName: initialData.legalName || "",
        tradingName: initialData.tradingName || "",
        businessType: initialData.businessType || "",
        industry: initialData.industry || "",
        registrationDate: initialData.registrationDate || "",
        primaryEmail: initialData.primaryEmail || "",
        primaryPhone: initialData.primaryPhone || "",
        website: initialData.website || "",
        registeredAddress: initialData.registeredAddress || "",
        numberOfEmployees: initialData.numberOfEmployees || null,
        annualTurnover: initialData.annualTurnover || "",
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
                <h3 className="text-lg font-semibold">Business Information</h3>
                <p className="text-sm text-muted-foreground">
                    Tell us about your business. Fields marked with * are required.
                </p>
            </div>

            <div className="grid gap-4 md:grid-cols-2">
                {/* Business Name */}
                <div className="space-y-2">
                    <Label htmlFor="legalName">Business Name *</Label>
                    <Input
                        id="legalName"
                        value={formData.legalName}
                        onChange={(e) => updateField("legalName", e.target.value)}
                        required
                        placeholder="ABC Private Limited"
                    />
                </div>

                {/* Trading Name */}
                <div className="space-y-2">
                    <Label htmlFor="tradingName">Trading Name (Optional)</Label>
                    <Input
                        id="tradingName"
                        value={formData.tradingName}
                        onChange={(e) => updateField("tradingName", e.target.value)}
                        placeholder="ABC Co."
                    />
                </div>

                {/* Business Type */}
                <div className="space-y-2">
                    <Label htmlFor="businessType">Business Type *</Label>
                    <Select
                        value={formData.businessType}
                        onValueChange={(v) => updateField("businessType", v)}
                        required
                    >
                        <SelectTrigger id="businessType">
                            <SelectValue placeholder="Select type" />
                        </SelectTrigger>
                        <SelectContent>
                            <SelectItem value="sole_proprietorship">Sole Proprietorship</SelectItem>
                            <SelectItem value="partnership">Partnership</SelectItem>
                            <SelectItem value="llp">Limited Liability Partnership (LLP)</SelectItem>
                            <SelectItem value="private_limited">Private Limited Company</SelectItem>
                            <SelectItem value="public_limited">Public Limited Company</SelectItem>
                            <SelectItem value="opc">One Person Company (OPC)</SelectItem>
                        </SelectContent>
                    </Select>
                </div>

                {/* Industry */}
                <div className="space-y-2">
                    <Label htmlFor="industry">Industry / Sector *</Label>
                    <Select
                        value={formData.industry}
                        onValueChange={(v) => updateField("industry", v)}
                        required
                    >
                        <SelectTrigger id="industry">
                            <SelectValue placeholder="Select industry" />
                        </SelectTrigger>
                        <SelectContent>
                            <SelectItem value="it_software">IT &amp; Software</SelectItem>
                            <SelectItem value="manufacturing">Manufacturing</SelectItem>
                            <SelectItem value="retail">Retail &amp; E-commerce</SelectItem>
                            <SelectItem value="services">Professional Services</SelectItem>
                            <SelectItem value="healthcare">Healthcare</SelectItem>
                            <SelectItem value="education">Education</SelectItem>
                            <SelectItem value="construction">Construction &amp; Real Estate</SelectItem>
                            <SelectItem value="energy_utilities">Energy &amp; Utilities</SelectItem>
                            <SelectItem value="finance">Finance &amp; Banking</SelectItem>
                            <SelectItem value="hospitality">Hospitality &amp; Tourism</SelectItem>
                            <SelectItem value="logistics">Logistics &amp; Supply Chain</SelectItem>
                            <SelectItem value="agriculture">Agriculture &amp; Food</SelectItem>
                            <SelectItem value="media">Media &amp; Entertainment</SelectItem>
                            <SelectItem value="telecom">Telecommunications</SelectItem>
                            <SelectItem value="aerospace">Aerospace &amp; Defence</SelectItem>
                            <SelectItem value="government">Government &amp; Public Sector</SelectItem>
                            <SelectItem value="other">Other</SelectItem>
                        </SelectContent>
                    </Select>
                </div>

                {/* Registration Date */}
                <div className="space-y-2">
                    <Label htmlFor="registrationDate">Registration Date *</Label>
                    <Input
                        id="registrationDate"
                        type="date"
                        value={formData.registrationDate}
                        onChange={(e) => updateField("registrationDate", e.target.value)}
                        required
                    />
                </div>

                {/* Annual Turnover */}
                <div className="space-y-2">
                    <Label htmlFor="annualTurnover">Annual Turnover (Optional)</Label>
                    <Select
                        value={formData.annualTurnover}
                        onValueChange={(v) => updateField("annualTurnover", v)}
                    >
                        <SelectTrigger id="annualTurnover">
                            <SelectValue placeholder="Select range" />
                        </SelectTrigger>
                        <SelectContent>
                            <SelectItem value="below_10l">Below ₹10 Lakhs</SelectItem>
                            <SelectItem value="10l_to_1cr">₹10 Lakhs – ₹1 Crore</SelectItem>
                            <SelectItem value="1cr_to_10cr">₹1 Crore – ₹10 Crores</SelectItem>
                            <SelectItem value="above_10cr">Above ₹10 Crores</SelectItem>
                        </SelectContent>
                    </Select>
                </div>
            </div>

            {/* Contact */}
            <div className="grid gap-4 md:grid-cols-2">
                <div className="space-y-2">
                    <Label htmlFor="primaryEmail">Primary Contact Email *</Label>
                    <Input
                        id="primaryEmail"
                        type="email"
                        value={formData.primaryEmail}
                        onChange={(e) => updateField("primaryEmail", e.target.value)}
                        required
                        placeholder="contact@abc.com"
                    />
                </div>

                <div className="space-y-2">
                    <Label htmlFor="primaryPhone">Primary Contact Phone *</Label>
                    <Input
                        id="primaryPhone"
                        type="tel"
                        value={formData.primaryPhone}
                        onChange={(e) => updateField("primaryPhone", e.target.value)}
                        required
                        placeholder="+91 9876543210"
                    />
                </div>
            </div>

            {/* Address */}
            <div className="space-y-2">
                <Label htmlFor="registeredAddress">Registered Address (Optional)</Label>
                <Textarea
                    id="registeredAddress"
                    value={formData.registeredAddress}
                    onChange={(e) => updateField("registeredAddress", e.target.value)}
                    placeholder="123 Business Street, City, State – 123456"
                    rows={3}
                />
            </div>

            <div className="flex justify-end">
                <Button type="submit" disabled={loading}>
                    {loading ? (
                        <>
                            <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                            Processing…
                        </>
                    ) : (
                        "Next: Regulatory Information →"
                    )}
                </Button>
            </div>
        </form>
    );
}
