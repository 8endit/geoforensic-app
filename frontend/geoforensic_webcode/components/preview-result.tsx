"use client";

import { Button } from "@/components/ui/button";
import type { PreviewResponse } from "@/lib/api";

type PreviewResultProps = {
  data: PreviewResponse;
  isAuthenticated: boolean;
  onCreateReport: () => void;
};

const AMPEL_STYLE: Record<PreviewResponse["ampel"], string> = {
  gruen: "text-green-400 border-green-400/40",
  gelb: "text-yellow-300 border-yellow-300/40",
  rot: "text-red-400 border-red-400/40",
};

export function PreviewResult({ data, isAuthenticated, onCreateReport }: PreviewResultProps) {
  return (
    <div className="mt-8 border border-border p-5 space-y-3 bg-black/40">
      <div className={`inline-flex border px-2 py-1 text-xs uppercase font-mono ${AMPEL_STYLE[data.ampel]}`}>
        {data.ampel}
      </div>
      <p className="font-mono text-sm text-foreground/80">Adresse: {data.address_resolved}</p>
      <p className="font-mono text-sm text-foreground/80">Punkte im Umfeld: {data.point_count}</p>
      <p className="font-mono text-sm text-foreground/80">
        Koordinaten: {data.latitude.toFixed(5)}, {data.longitude.toFixed(5)}
      </p>
      <Button onClick={onCreateReport} className="w-full mt-2">
        {isAuthenticated ? "Vollständigen Report erstellen" : "Login/Register für vollständigen Report"}
      </Button>
    </div>
  );
}

