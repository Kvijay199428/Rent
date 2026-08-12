import {
  createContext,
  useCallback,
  useContext,
  useMemo,
  type ReactNode,
} from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { tenantApi } from "@/lib/api";
import { getTenantRuntime } from "@/lib/tenant-runtime";
import type { PortalResponse, Receipt, Occupant } from "@/types";

type TenantContextType = {
  landlordUuid: string;
  propertyId: string;
  tenantId: string;
  viewToken: string;
  profile: PortalResponse | undefined;
  receipts: Receipt[];
  occupants: Occupant[];
  isUnlocked: boolean;
  readOnly: boolean;
  isLoading: boolean;
  login: (pin: string, rememberMe?: boolean) => Promise<void>;
  logout: () => Promise<void>;
  refetch: () => void;
};

const TenantContext = createContext<TenantContextType | undefined>(undefined);

export function TenantProvider({ children }: { children: ReactNode }) {
  const { landlordUuid, propertyId, tenantId, viewToken } = getTenantRuntime();
  const queryClient = useQueryClient();

  const { data, isLoading, refetch } = useQuery<PortalResponse>({
    queryKey: ["tenant-profile", viewToken],
    queryFn: async () => {
      const res = await tenantApi.profile.get();
      return res.data as PortalResponse;
    },
    enabled: !!viewToken,
    retry: false,
  });

  const isUnlocked = Boolean(data?.tenant?.unlocked);
  const readOnly = Boolean(data?.tenant?.readOnly);
  const receipts = useMemo(() => data?.receipts ?? [], [data]);
  const occupants = useMemo(() => data?.occupants ?? [], [data]);

  const login = useCallback(
    async (pin: string, rememberMe = false) => {
      await tenantApi.auth.login(pin, rememberMe);
      await refetch();
    },
    [refetch]
  );

  const logout = useCallback(async () => {
    try {
      await tenantApi.auth.logout();
    } finally {
      window.location.reload();
    }
  }, []);

  const value = useMemo(
    () => ({
      landlordUuid: landlordUuid!,
      propertyId: propertyId!,
      tenantId: tenantId!,
      viewToken: viewToken!,
      profile: data,
      receipts,
      occupants,
      isUnlocked,
      readOnly,
      isLoading,
      login,
      logout,
      refetch,
    }),
    [
      landlordUuid,
      propertyId,
      tenantId,
      viewToken,
      data,
      receipts,
      occupants,
      isUnlocked,
      readOnly,
      isLoading,
      login,
      logout,
      refetch,
    ]
  );

  return (
    <TenantContext.Provider value={value}>{children}</TenantContext.Provider>
  );
}

export function useTenant() {
  const ctx = useContext(TenantContext);
  if (!ctx) throw new Error("useTenant must be used within TenantProvider");
  return ctx;
}
