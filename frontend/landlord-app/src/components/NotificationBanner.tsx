import { useNavigate } from "react-router";
import { X, Info } from "lucide-react";
import { Button } from "@/components/ui/button";
import { useAuth } from "@/contexts/AuthContext";
import { useNotifications, type NotificationItem } from "@/hooks/useNotifications";
import { ROUTES } from "@/lib/routes";

function toRoutePath(href: string): string {
  const base = ROUTES.basePath;
  if (base && href.startsWith(base)) {
    return href.slice(base.length) || "/";
  }
  return href;
}

export function NotificationBanner() {
  const { landlordUuid } = useAuth();
  const { notifications, dismiss } = useNotifications(landlordUuid);
  const navigate = useNavigate();

  if (notifications.length === 0) return null;

  return (
    <div className="border-b bg-card">
      {notifications.map((n: NotificationItem) => (
        <div
          key={n.slug}
          className="flex items-start gap-3 px-4 lg:px-6 py-3 border-b last:border-b-0"
        >
          <Info className="h-4 w-4 mt-0.5 shrink-0 text-primary" />
          <div className="flex-1 min-w-0">
            <p className="text-sm font-medium">{n.title}</p>
            {n.message && (
              <p className="text-sm text-muted-foreground">{n.message}</p>
            )}
          </div>
          {n.action && (
            <Button
              size="sm"
              className="shrink-0"
              onClick={() => navigate(toRoutePath(n.action!.href))}
            >
              {n.action.label}
            </Button>
          )}
          <button
            className="shrink-0 text-muted-foreground hover:text-foreground"
            onClick={() => dismiss(n.slug)}
            aria-label="Dismiss"
          >
            <X className="h-4 w-4" />
          </button>
        </div>
      ))}
    </div>
  );
}

export default NotificationBanner;