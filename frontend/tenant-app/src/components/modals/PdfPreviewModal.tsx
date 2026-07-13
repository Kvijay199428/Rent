import { useState, useEffect } from "react";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { FileText, Download, Loader2, X } from "lucide-react";
import { toast } from "sonner";
import { TENANTROUTES } from "@/lib/routes";

interface PdfPreviewModalProps {
  billNo: string;
  viewToken: string;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export default function PdfPreviewModal({
  billNo,
  viewToken,
  open,
  onOpenChange,
}: PdfPreviewModalProps) {
  const [loading, setLoading] = useState(true);
  const [pdfUrl, setPdfUrl] = useState<string>("");
  const [error, setError] = useState("");

  const pdfViewUrl = TENANTROUTES.TENANTAPIPDFVIEW(viewToken, billNo);
  const pdfDownloadUrl = TENANTROUTES.TENANTAPIPDFDOWNLOAD(viewToken, billNo);

  useEffect(() => {
    if (!open || !billNo || !viewToken) return;

    setLoading(true);
    setError("");

    fetch(pdfViewUrl, {
      method: "GET",
      credentials: "include",
    })
      .then((res) => {
        if (!res.ok) throw new Error("Failed to load PDF");
        return res.blob();
      })
      .then((blob) => {
        const url = URL.createObjectURL(blob);
        setPdfUrl(url);
        setLoading(false);
      })
      .catch((err) => {
        setError(err.message || "Could not load PDF preview");
        setLoading(false);
      });

    return () => {
      if (pdfUrl) URL.revokeObjectURL(pdfUrl);
    };
  }, [open, billNo, viewToken]);

  const handleDownload = async () => {
    try {
      const res = await fetch(pdfDownloadUrl, {
        credentials: "include",
      });
      if (!res.ok) throw new Error("Download failed");

      const blob = await res.blob();
      const url = window.URL.createObjectURL(blob);

      const disposition = res.headers.get("content-disposition");
      let filename = `receipt_${billNo}.pdf`;
      if (disposition) {
        const match = disposition.match(/filename="?([^"]+)"?/);
        if (match) filename = match[1];
      }

      const a = document.createElement("a");
      a.href = url;
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.URL.revokeObjectURL(url);

      toast.success("PDF downloaded successfully");
    } catch {
      toast.error("Failed to download PDF");
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent showCloseButton={false} className="max-w-[95vw] xl:max-w-[1400px] h-[92vh] p-0 flex flex-col gap-0 overflow-hidden">
        <DialogHeader className="px-6 pt-5 pb-3 shrink-0 border-b flex flex-row items-center justify-between space-y-0">
          <div className="flex items-center gap-3">
            <FileText className="h-6 w-6 text-red-500 shrink-0" />
            <div>
              <DialogTitle className="text-xl">Receipt Preview</DialogTitle>
              <DialogDescription className="mt-1 text-sm">
                {billNo && (
                  <>
                    Bill Number:{" "}
                    <span className="font-medium text-foreground">
                      #{billNo}
                    </span>
                  </>
                )}
              </DialogDescription>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={handleDownload}
              className="gap-1.5"
            >
              <Download className="h-4 w-4" />
              Download
            </Button>
            <Button
              variant="ghost"
              size="icon"
              className="h-8 w-8"
              onClick={() => onOpenChange(false)}
            >
              <X className="h-4 w-4" />
            </Button>
          </div>
        </DialogHeader>

        <div className="flex-1 min-h-0 bg-muted relative">
          {loading && (
            <div className="absolute inset-0 flex flex-col items-center justify-center gap-3">
              <Loader2 className="h-8 w-8 animate-spin text-primary" />
              <p className="text-sm text-muted-foreground">Loading PDF preview...</p>
            </div>
          )}

          {error && (
            <div className="absolute inset-0 flex flex-col items-center justify-center gap-3 p-6 text-center">
              <FileText className="h-12 w-12 text-muted-foreground/50" />
              <div>
                <p className="text-destructive font-medium">{error}</p>
                <p className="text-sm text-muted-foreground mt-1">
                  The receipt PDF may not be available yet.
                </p>
              </div>
              <Button variant="outline" onClick={handleDownload} className="gap-1.5 mt-2">
                <Download className="h-4 w-4" />
                Try Download
              </Button>
            </div>
          )}

          {pdfUrl && !loading && !error && (
            <iframe
              src={pdfUrl}
              className="w-full h-full border-0"
              title={`Receipt ${billNo}`}
            />
          )}
        </div>
      </DialogContent>
    </Dialog>
  );
}
