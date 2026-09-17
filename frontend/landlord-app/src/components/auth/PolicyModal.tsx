// components/auth/PolicyModal.tsx
import type { ReactNode } from "react";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from "@/components/ui/dialog";
import { ScrollArea } from "@/components/ui/scroll-area";

interface PolicyModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  title: string;
  description?: string;
  content?: ReactNode;
}

const DEFAULT_PLACEHOLDER = (
  <p className="text-sm text-muted-foreground leading-relaxed">
    Replace this with your real policy text — pass it in via the{" "}
    <code className="rounded bg-muted px-1 py-0.5 text-xs">termsContent</code> or{" "}
    <code className="rounded bg-muted px-1 py-0.5 text-xs">privacyContent</code> prop on{" "}
    <code className="rounded bg-muted px-1 py-0.5 text-xs">AuthFlow</code>.
  </p>
);

/** Shared Dialog used for both the Terms and Privacy popups — no routing required. */
export function PolicyModal({ open, onOpenChange, title, description, content }: PolicyModalProps) {
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-lg">
        <DialogHeader>
          <DialogTitle>{title}</DialogTitle>
          {description && <DialogDescription>{description}</DialogDescription>}
        </DialogHeader>
        <ScrollArea className="max-h-[60vh] pr-4">
          {content ?? DEFAULT_PLACEHOLDER}
        </ScrollArea>
      </DialogContent>
    </Dialog>
  );
}
