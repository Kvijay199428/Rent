import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Eye, MapPin, Calendar, Clock } from "lucide-react";
import { cn } from "@/lib/utils";
import { daysResided, formatResidentSince } from "@/lib/utils";
import type { Occupant } from "@/types";

export default function OccupantCard({
  occupant,
  onView,
}: {
  occupant: Occupant;
  onView: (occupant: Occupant) => void;
}) {
  const isActive = (occupant.status || "Active").toUpperCase() === "ACTIVE";
  const days = occupant.residentSince ? daysResided(occupant.residentSince) : null;
  const hasDocs =
    occupant.aadhaarfront || occupant.aadhaarback || occupant.aadhaarcombined;

  return (
    <Card
      className="rounded-2xl border shadow-sm cursor-pointer hover:shadow-md hover:border-border/80 transition-all"
      onClick={() => onView(occupant)}
    >
      <CardContent className="p-4">
        <div className="flex items-start justify-between gap-3 mb-3">
          <div className="flex items-center gap-3 min-w-0">
            <div
              className={cn(
                "h-9 w-9 rounded-full flex items-center justify-center text-sm font-bold shrink-0",
                isActive
                  ? "bg-emerald-500/10 text-emerald-600"
                  : "bg-muted text-muted-foreground"
              )}
            >
              {(occupant.name || "?").charAt(0).toUpperCase()}
            </div>
            <div className="min-w-0">
              <span className="font-semibold truncate block">{occupant.name}</span>
              <Badge
                variant="outline"
                className={cn(
                  "mt-0.5",
                  isActive
                    ? "bg-emerald-500/10 text-emerald-600 hover:bg-emerald-500/20"
                    : "bg-slate-100 text-slate-600 hover:bg-slate-100"
                )}
              >
                {isActive ? "Active" : "Inactive"}
              </Badge>
            </div>
          </div>
          <Button
            variant="ghost"
            size="icon"
            className="h-8 w-8 shrink-0"
            onClick={(e) => {
              e.stopPropagation();
              onView(occupant);
            }}
            title="View documents"
          >
            <Eye className="h-4 w-4" />
          </Button>
        </div>

        <div className="space-y-1.5 text-sm text-muted-foreground">
          {occupant.mobile && (
            <p>{occupant.mobile}</p>
          )}
          {occupant.address && (
            <div className="flex items-start gap-1.5">
              <MapPin className="h-3.5 w-3.5 mt-0.5 shrink-0" />
              <span className="truncate">{occupant.address}</span>
            </div>
          )}
          {occupant.residentSince && (
            <div className="flex items-center gap-1.5">
              <Calendar className="h-3.5 w-3.5 shrink-0" />
              <span>Since {formatResidentSince(occupant.residentSince)}</span>
            </div>
          )}
          {days !== null && (
            <div className="flex items-center gap-1.5">
              <Clock className="h-3.5 w-3.5 shrink-0" />
              <span>{days} days resided</span>
            </div>
          )}
          {hasDocs && (
            <p className="text-xs text-muted-foreground/70 pt-1">Documents uploaded</p>
          )}
        </div>
      </CardContent>
    </Card>
  );
}
