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
import { Checkbox } from "@/components/ui/checkbox";
import { Loader2 } from "lucide-react";

const CHALLENGES = [
    "Cash Flow Management",
    "Tax Compliance",
    "Growth & Scaling",
    "Client Acquisition",
    "Expense Tracking",
    "Inventory Management",
    "Team Management",
    "Market Research",
];

export function BusinessContextStep({ initialData = {}, onNext, onBack, loading }) {
    const [formData, setFormData] = useState({
        primaryActivity: initialData.primaryActivity || "",
        targetMarket: initialData.targetMarket || "",
        keyProducts: initialData.keyProducts?.length ? initialData.keyProducts : [""],
        currentChallenges: initialData.currentChallenges || [],
        accountingMethod: initialData.accountingMethod || "accrual",
        fyStartMonth: initialData.fyStartMonth || 4,
        preferredLanguage: initialData.preferredLanguage || "en",
    });

    const handleSubmit = (e) => {
        e.preventDefault();
        const cleanedData = {
            ...formData,
            keyProducts: formData.keyProducts.filter((p) => p.trim() !== ""),
        };
        onNext(cleanedData);
    };

    const updateField = (field, value) =>
        setFormData((prev) => ({ ...prev, [field]: value }));

    const updateProduct = (index, value) => {
        const products = [...formData.keyProducts];
        products[index] = value;
        setFormData((prev) => ({ ...prev, keyProducts: products }));
    };

    const addProduct = () => {
        if (formData.keyProducts.length < 5) {
            setFormData((prev) => ({ ...prev, keyProducts: [...prev.keyProducts, ""] }));
        }
    };

    const toggleChallenge = (challenge) => {
        const challenges = formData.currentChallenges.includes(challenge)
            ? formData.currentChallenges.filter((c) => c !== challenge)
            : [...formData.currentChallenges, challenge];
        updateField("currentChallenges", challenges);
    };

    return (
        <form onSubmit={handleSubmit} className="space-y-6">
            <div className="space-y-1">
                <h3 className="text-lg font-semibold">Business Context & Preferences</h3>
                <p className="text-sm text-muted-foreground">
                    Help our AI agents understand your business better.
                </p>
            </div>

            {/* Primary Activity */}
            <div className="space-y-2">
                <Label htmlFor="primaryActivity">Primary Business Activity *</Label>
                <Textarea
                    id="primaryActivity"
                    value={formData.primaryActivity}
                    onChange={(e) => updateField("primaryActivity", e.target.value)}
                    required
                    placeholder="Describe what your business does…"
                    rows={3}
                />
            </div>

            {/* Target Market */}
            <div className="grid gap-4 md:grid-cols-2">
                <div className="space-y-2">
                    <Label htmlFor="targetMarket">Target Market *</Label>
                    <Select
                        value={formData.targetMarket}
                        onValueChange={(v) => updateField("targetMarket", v)}
                        required
                    >
                        <SelectTrigger id="targetMarket">
                            <SelectValue placeholder="Select market" />
                        </SelectTrigger>
                        <SelectContent>
                            <SelectItem value="B2B">B2B (Business to Business)</SelectItem>
                            <SelectItem value="B2C">B2C (Business to Consumer)</SelectItem>
                            <SelectItem value="B2G">B2G (Business to Government)</SelectItem>
                        </SelectContent>
                    </Select>
                </div>
            </div>

            {/* Key Products / Services */}
            <div className="space-y-3">
                <Label>Key Products / Services (up to 5)</Label>
                {formData.keyProducts.map((product, index) => (
                    <Input
                        key={index}
                        value={product}
                        onChange={(e) => updateProduct(index, e.target.value)}
                        placeholder={`Product / Service ${index + 1}`}
                    />
                ))}
                {formData.keyProducts.length < 5 && (
                    <Button type="button" variant="outline" size="sm" onClick={addProduct}>
                        + Add Another
                    </Button>
                )}
            </div>

            {/* Current Challenges */}
            <div className="space-y-3">
                <Label>Current Challenges (select all that apply)</Label>
                <div className="grid gap-3 md:grid-cols-2">
                    {CHALLENGES.map((challenge) => (
                        <div key={challenge} className="flex items-center space-x-2">
                            <Checkbox
                                id={`challenge-${challenge}`}
                                checked={formData.currentChallenges.includes(challenge)}
                                onCheckedChange={() => toggleChallenge(challenge)}
                            />
                            <label
                                htmlFor={`challenge-${challenge}`}
                                className="text-sm cursor-pointer leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70"
                            >
                                {challenge}
                            </label>
                        </div>
                    ))}
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
                        "Complete Setup →"
                    )}
                </Button>
            </div>
        </form>
    );
}
