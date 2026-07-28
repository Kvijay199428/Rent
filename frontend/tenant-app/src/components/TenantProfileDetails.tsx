import { User, Phone, Mail, MapPin, DoorOpen, Briefcase, Building2 } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Separator } from "@/components/ui/separator";
import { useTenant } from "@/context/TenantContext";

interface DetailRow {
  icon: React.ComponentType<{ className?: string }>;
  label: string;
  value: string | undefined;
}

function DetailItem({ icon: Icon, label, value }: DetailRow) {
  return (
    <div className="flex items-start gap-3 py-2">
      <Icon className="h-4 w-4 mt-0.5 text-muted-foreground shrink-0" />
      <div className="min-w-0 flex-1">
        <p className="text-xs font-medium text-muted-foreground">{label}</p>
        <p className="text-sm text-foreground break-words">
          {value || <span className="text-muted-foreground/50">—</span>}
        </p>
      </div>
    </div>
  );
}

export default function TenantProfileDetails() {
  const { profile } = useTenant();
  const tenant = profile?.tenant;

  if (!tenant) return null;

  const identityRows: DetailRow[] = [
    { icon: User, label: "Full Name", value: tenant.name },
  ];

  const contactRows: DetailRow[] = [
    { icon: Phone, label: "Phone", value: tenant.phone },
    { icon: Mail, label: "Email", value: tenant.email },
  ];

  const locationRows: DetailRow[] = [
    { icon: MapPin, label: "Address", value: tenant.address },
    { icon: DoorOpen, label: "Room", value: tenant.roomNumber },
    { icon: Briefcase, label: "Occupation", value: tenant.occupation },
    { icon: Building2, label: "Company", value: tenant.company },
  ];

  const hasAnyData = [...identityRows, ...contactRows, ...locationRows].some(
    (r) => r.value
  );

  return (
    <Card className="rounded-2xl border shadow-sm">
      <CardHeader className="pb-3">
        <CardTitle className="text-lg flex items-center gap-2">
          <User className="h-5 w-5 text-muted-foreground" />
          My Details
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-1">
        {!hasAnyData && (
          <p className="text-sm text-muted-foreground text-center py-4">
            No profile details available.
          </p>
        )}

        {identityRows.some((r) => r.value) && (
          <div>
            {identityRows
              .filter((r) => r.value)
              .map((row) => (
                <DetailItem key={row.label} {...row} />
              ))}
          </div>
        )}

        {identityRows.some((r) => r.value) &&
          contactRows.some((r) => r.value) && <Separator />}

        {contactRows.some((r) => r.value) && (
          <div>
            {contactRows
              .filter((r) => r.value)
              .map((row) => (
                <DetailItem key={row.label} {...row} />
              ))}
          </div>
        )}

        {(identityRows.some((r) => r.value) || contactRows.some((r) => r.value)) &&
          locationRows.some((r) => r.value) && <Separator />}

        {locationRows.some((r) => r.value) && (
          <div>
            {locationRows
              .filter((r) => r.value)
              .map((row) => (
                <DetailItem key={row.label} {...row} />
              ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
