import { cn } from "@/lib/utils";

const Textarea = ({ className, ...props }) => {
    return (
        <textarea
            className={cn(
                "flex min-h-[80px] w-full rounded-md border border-slate-200 bg-white px-3 py-2 text-sm ring-offset-white placeholder:text-slate-400 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50 resize-none",
                className
            )}
            {...props}
        />
    );
};

export { Textarea };
