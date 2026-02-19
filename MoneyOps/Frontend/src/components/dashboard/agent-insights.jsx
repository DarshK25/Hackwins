import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { ScrollArea } from "@/components/ui/scroll-area";
import { BrainCircuit, Clock } from "lucide-react";

export function AgentInsights({ agentName, insights }) {
    return (
        <Card>
            <CardHeader>
                <div className="flex items-center gap-2">
                    <BrainCircuit className="h-5 w-5 text-primary" />
                    <CardTitle>{agentName} Insights</CardTitle>
                </div>
            </CardHeader>
            <CardContent>
                <ScrollArea className="h-[300px] pr-4">
                    {!insights || insights.length === 0 ? (
                        <p className="text-muted-foreground text-sm">
                            No insights generated yet.
                        </p>
                    ) : (
                        <div className="space-y-4">
                            {insights.map((insight) => (
                                <div
                                    key={insight.id}
                                    className="border-l-4 border-primary pl-4 py-2 bg-muted/30 rounded-r-md"
                                >
                                    <div className="flex justify-between items-start mb-1">
                                        <Badge variant="secondary" className="text-xs">
                                            {insight.taskDescription}
                                        </Badge>
                                        <span className="text-[10px] text-muted-foreground flex items-center gap-1">
                                            <Clock className="h-3 w-3" />
                                            {new Date(insight.completedAt).toLocaleTimeString()}
                                        </span>
                                    </div>
                                    <p className="text-sm mt-2">
                                        {insight.output?.message || JSON.stringify(insight.output)}
                                    </p>
                                </div>
                            ))}
                        </div>
                    )}
                </ScrollArea>
            </CardContent>
        </Card>
    );
}
