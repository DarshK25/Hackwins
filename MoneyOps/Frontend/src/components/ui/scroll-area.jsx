import * as React from "react";
import * as ScrollAreaPrimitive from "@radix-ui/react-scroll-area";
import { cn } from "@/lib/utils";

const ScrollArea = React.forwardRef(({ className, children, ...props }, ref) => (
    <ScrollAreaPrimitive.Root
        ref={ref}
        className={cn("relative overflow-hidden", className)}
        {...props}
    >
        <ScrollAreaPrimitive.Viewport className="h-full w-full rounded-[inherit] before:absolute before:inset-0 before:bg-gradient-to-b before:from-white before:to-transparent before:h-4 before:pointer-events-none before:opacity-0 hover:before:opacity-100 dark:before:from-slate-900 transition-opacity">
            {children}
        </ScrollAreaPrimitive.Viewport>
        <ScrollBar />
        <ScrollAreaPrimitive.Corner />
    </ScrollAreaPrimitive.Root>
));
ScrollArea.displayName = ScrollAreaPrimitive.Root.displayName;

const ScrollBar = React.forwardRef(
    ({ className, orientation = "vertical", ...props }, ref) => (
        <ScrollAreaPrimitive.Scrollbar
            ref={ref}
            orientation={orientation}
            className={cn(
                "flex touch-none select-none transition-colors",
                orientation === "vertical" &&
                "h-full w-2.5 border-l border-l-transparent p-[1px]",
                orientation === "horizontal" &&
                "h-2.5 flex-col border-t border-t-transparent p-[1px]",
                className
            )}
            {...props}
        >
            <ScrollAreaPrimitive.Thumb className="relative flex-1 rounded-full bg-slate-200 hover:bg-slate-300 active:bg-slate-400 transition-colors" />
        </ScrollAreaPrimitive.Scrollbar>
    )
);
ScrollBar.displayName = ScrollAreaPrimitive.Scrollbar.displayName;

export { ScrollArea, ScrollBar };
