import { Card, CardContent } from "@/components/ui/card";

export function ReceiptSkeleton() {
  return (
    <Card className="rounded-2xl border shadow-sm">
      <CardContent className="p-4 flex items-center justify-between gap-4">
        <div className="space-y-2 flex-1">
          <div className="h-5 w-32 bg-muted animate-pulse rounded" />
          <div className="h-3 w-48 bg-muted animate-pulse rounded" />
        </div>
        <div className="flex items-center gap-3">
          <div className="h-6 w-20 bg-muted animate-pulse rounded" />
          <div className="flex gap-1">
            <div className="h-8 w-8 bg-muted animate-pulse rounded" />
            <div className="h-8 w-8 bg-muted animate-pulse rounded" />
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

export function OccupantSkeleton() {
  return (
    <Card className="rounded-2xl border shadow-sm">
      <CardContent className="p-4 space-y-3">
        <div className="flex items-center gap-3">
          <div className="h-9 w-9 bg-muted animate-pulse rounded-full" />
          <div className="space-y-1.5 flex-1">
            <div className="h-4 w-28 bg-muted animate-pulse rounded" />
            <div className="h-3 w-16 bg-muted animate-pulse rounded" />
          </div>
          <div className="h-8 w-8 bg-muted animate-pulse rounded" />
        </div>
        <div className="space-y-1.5">
          <div className="h-3 w-24 bg-muted animate-pulse rounded" />
          <div className="h-3 w-40 bg-muted animate-pulse rounded" />
          <div className="h-3 w-32 bg-muted animate-pulse rounded" />
          <div className="h-3 w-20 bg-muted animate-pulse rounded" />
        </div>
      </CardContent>
    </Card>
  );
}

export function PaymentStatusCardSkeleton() {
  return (
    <Card className="rounded-2xl border shadow-sm">
      <CardContent className="p-5 space-y-4">
        <div className="flex items-start justify-between">
          <div className="space-y-2">
            <div className="h-3 w-36 bg-muted animate-pulse rounded" />
            <div className="h-6 w-24 bg-muted animate-pulse rounded" />
          </div>
          <div className="h-3 w-16 bg-muted animate-pulse rounded" />
        </div>
        <div className="space-y-2">
          <div className="flex justify-between">
            <div className="h-4 w-32 bg-muted animate-pulse rounded" />
            <div className="h-4 w-8 bg-muted animate-pulse rounded" />
          </div>
          <div className="h-2 w-full bg-muted animate-pulse rounded-full" />
          <div className="flex justify-between">
            <div className="h-3 w-20 bg-muted animate-pulse rounded" />
            <div className="h-3 w-20 bg-muted animate-pulse rounded" />
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

export function DashboardSkeleton() {
  return (
    <div className="min-h-screen bg-muted/30">
      <header className="sticky top-0 z-10 border-b bg-background/90 backdrop-blur">
        <div className="max-w-5xl mx-auto px-4 py-4 flex items-center justify-between">
          <div className="space-y-2">
            <div className="h-6 w-48 bg-muted animate-pulse rounded" />
            <div className="h-3 w-24 bg-muted animate-pulse rounded" />
          </div>
        </div>
      </header>
      <main className="max-w-5xl mx-auto p-4 md:p-6 space-y-6">
        <div className="flex gap-2 border rounded-xl p-1 bg-background w-fit">
          <div className="h-8 w-24 bg-muted animate-pulse rounded-md" />
          <div className="h-8 w-24 bg-muted animate-pulse rounded-md" />
          <div className="h-8 w-20 bg-muted animate-pulse rounded-md" />
        </div>
        <div className="space-y-6">
          <PaymentStatusCardSkeleton />
          <div className="space-y-3">
            <div className="h-5 w-32 bg-muted animate-pulse rounded" />
            <ReceiptSkeleton />
            <ReceiptSkeleton />
          </div>
        </div>
      </main>
    </div>
  );
}
