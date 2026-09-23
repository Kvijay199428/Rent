import { useState, useCallback, useEffect } from "react";
import { apiGet } from "@/hooks/useApi";
import { ROUTES } from "@/lib/routes";

export type NotificationAction = { label: string; href: string };
export type NotificationItem = {
  slug: string;
  title: string;
  message: string;
  action?: NotificationAction;
};

function dismissedKey(landlordUuid: string, slug: string): string {
  return `landlord:notifications:dismissed:${landlordUuid}:${slug}`;
}

export function useNotifications(landlordUuid: string | null) {
  const [notifications, setNotifications] = useState<NotificationItem[]>([]);
  const [loaded, setLoaded] = useState(false);

  const refresh = useCallback(async () => {
    if (!landlordUuid) return;
    try {
      const res = (await apiGet(ROUTES.LANDLORDAPINOTIFICATIONS(landlordUuid))) as any;
      const items: NotificationItem[] = Array.isArray(res?.notifications)
        ? res.notifications
        : [];
      setNotifications(
        items.filter(
          (n) => !sessionStorage.getItem(dismissedKey(landlordUuid, n.slug))
        )
      );
    } finally {
      setLoaded(true);
    }
  }, [landlordUuid]);

  useEffect(() => {
    setLoaded(false);
    refresh();
  }, [refresh]);

  const dismiss = useCallback(
    (slug: string) => {
      if (landlordUuid) {
        sessionStorage.setItem(dismissedKey(landlordUuid, slug), "1");
      }
      setNotifications((prev) => prev.filter((n) => n.slug !== slug));
    },
    [landlordUuid]
  );

  return { notifications, loaded, refresh, dismiss };
}