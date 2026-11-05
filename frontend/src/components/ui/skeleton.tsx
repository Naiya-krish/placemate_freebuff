import { cn } from "@/lib/utils";

export function Skeleton({ className }: { className?: string }) {
  return <div className={cn("skeleton", className)} aria-hidden />;
}

export function CardSkeleton({ className }: { className?: string }) {
  return (
    <div className={cn("surface-card space-y-4 p-5", className)}>
      <Skeleton className="h-4 w-1/3" />
      <Skeleton className="h-9 w-2/3" />
      <Skeleton className="h-3 w-full" />
      <Skeleton className="h-3 w-5/6" />
    </div>
  );
}

export function DashboardSkeleton() {
  return (
    <div className="grid grid-cols-1 gap-4 md:grid-cols-6 xl:grid-cols-12">
      <CardSkeleton className="md:col-span-4 xl:col-span-5 xl:row-span-2" />
      <CardSkeleton className="md:col-span-2 xl:col-span-4" />
      <CardSkeleton className="md:col-span-3 xl:col-span-3" />
      <CardSkeleton className="md:col-span-3 xl:col-span-4" />
      <CardSkeleton className="md:col-span-3 xl:col-span-4" />
      <CardSkeleton className="md:col-span-3 xl:col-span-4" />
    </div>
  );
}
