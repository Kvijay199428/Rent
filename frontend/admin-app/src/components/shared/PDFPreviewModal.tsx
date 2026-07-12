import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from '@/components/ui/dialog';
import { api } from '@/services/api';
import { FileText } from 'lucide-react';

interface PDFPreviewModalProps {
  billno: string | null;
  onClose: () => void;
}

export default function PDFPreviewModal({ billno, onClose }: PDFPreviewModalProps) {
  const open = !!billno;

  return (
    <Dialog open={open} onOpenChange={(v) => !v && onClose()}>
      {/* Match PreviewDialog sizing pattern exactly */}
      <DialogContent className="max-w-[95vw] xl:max-w-[1400px] h-[92vh] p-0 flex flex-col gap-0 overflow-hidden">
        {/* Match PreviewDialog header styling */}
        <DialogHeader className="px-6 pt-5 pb-3 shrink-0 border-b">
          <div className="flex items-center gap-3">
            <FileText className="h-6 w-6 text-red-500 shrink-0" />
            <div>
              <DialogTitle className="text-xl">Receipt Preview</DialogTitle>
              <DialogDescription className="mt-1 text-sm">
                {billno && (
                  <>
                    Bill Number:{" "}
                    <span className="font-medium text-foreground">
                      #{billno}
                    </span>
                  </>
                )}
              </DialogDescription>
            </div>
          </div>
        </DialogHeader>
        <div className="flex-1 min-h-0 bg-muted">
          {billno && (
            <iframe
              src={api.getPDFViewUrl(billno)}
              className="w-full h-full border-0"
              title={`Receipt ${billno}`}
            />
          )}
        </div>
      </DialogContent>
    </Dialog>
  );
}