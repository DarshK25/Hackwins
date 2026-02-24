import * as React from "react";
import * as ScrollAreaPrimitive from "@radix-ui/react-scroll-area";
import { cn } from "@/lib/utils";

const ScrollArea = React.forwardRef(({ className, children, ...props }, ref) => (
    <ScrollAreaPrimitive.Root
        ref={ref}
        className={cn("relative overflow-hidden", className)}
        {...props}
    >
        {/* No white gradient — clean dark viewport */}
        <ScrollAreaPrimitive.Viewport className="h-full w-full rounded-[inherit]">
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
                "h-full w-1.5 border-l border-l-transparent p-[1px]",
                orientation === "horizontal" &&
                "h-1.5 flex-col border-t border-t-transparent p-[1px]",
                className
            )}
            {...props}
        >
            <ScrollAreaPrimitive.Thumb className="relative flex-1 rounded-full bg-[#2A2A2A] hover:bg-[#4CBB17] transition-colors" />
        </ScrollAreaPrimitive.Scrollbar>
    )
);
ScrollBar.displayName = ScrollAreaPrimitive.Scrollbar.displayName;

export { ScrollArea, ScrollBar };
