"use client";

import { useParams, useRouter } from "next/navigation";
import { useEffect, useMemo, useState } from "react";
import { toast } from "sonner";

import { API_URL, checkout, getReport, type ReportDetail } from "@/lib/api";
import { useAuth } from "@/lib/auth-context";

const AMPEL_STYLE: Record<"gruen" | "gelb" | "rot", string> = {
  gruen: "text-green-400 border-green-400/40",
  gelb: "text-yellow-300 border-yellow-300/40",
  rot: "text-red-400 border-red-400/40",
};

const DATA_SOURCES: { status: "aktiv" | "geplant"; name: string; desc: string }[] = [
  { status: "aktiv", name: "EGMS Ortho L3 (Copernicus)", desc: "Vertikale + Ost-West Bodenbewegung, 2015–2022" },
  { status: "aktiv", name: "Nominatim / OpenStreetMap", desc: "Geocodierung der Eingabeadresse" },
  { status: "geplant", name: "BGR Bodenbewegungsdienst", desc: "Hochauflösende nationale InSAR-Daten (DE)" },
  { status: "geplant", name: "Hochwasser-Gefahrenkarten", desc: "EU-HWRL Fluss-/Küstenhochwasser" },
  { status: "geplant", name: "Altlastenkataster", desc: "Kontaminierte Standorte (DE/NL)" },
];

export default function ReportDetailPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const { token, isLoading } = useAuth();
  const [report, setReport] = useState<ReportDetail | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (isLoading) return;
    if (!token) {
      router.push("/login");
      return;
    }
    getReport(id, token)
      .then(setReport)
      .catch((error) => toast.error(error instanceof Error ? error.message : "Report nicht gefunden."))
      .finally(() => setLoading(false));
  }, [id, token, isLoading, router]);

  const downloadFile = async (path: string, filename: string) => {
    if (!token) return;
    try {
      const res = await fetch(`${API_URL}${path}`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!res.ok) throw new Error(`Download fehlgeschlagen (${res.status})`);
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = filename;
      a.click();
      URL.revokeObjectURL(url);
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "Download fehlgeschlagen.");
    }
  };

  const startCheckout = async () => {
    if (!token || !report) return;
    try {
      const response = await checkout(report.id, token);
      window.location.href = response.checkout_url;
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "Checkout fehlgeschlagen.");
    }
  };

  if (loading) {
    return <main className="min-h-screen pt-40 px-6 font-mono">Lade Report...</main>;
  }

  if (!report) {
    return <main className="min-h-screen pt-40 px-6 font-mono">Report nicht gefunden.</main>;
  }

  const reportData = (report.report_data ?? {}) as {
    selected_modules?: string[];
    analysis?: {
      summary?: string;
      point_count?: number;
      max_abs_velocity_mm_yr?: number;
      weighted_velocity_mm_yr?: number;
    };
    velocity_histogram?: Record<string, number>;
    raw_points?: { lat: number; lon: number; velocity_mm_yr: number; distance_m: number; coherence: number }[];
  };
  const analysis = reportData.analysis ?? {};
  const selectedModules = reportData.selected_modules ?? ["classic"];
  const modules = new Set(selectedModules);
  const histogram = reportData.velocity_histogram ?? {};
  const histogramEntries = Object.entries(histogram);
  const histogramMax = histogramEntries.length > 0 ? Math.max(...histogramEntries.map(([, v]) => v)) : 0;
  const rawPoints = reportData.raw_points ?? [];
  const hasNoData = (analysis.point_count ?? 0) === 0;

  return (
    <main className="min-h-screen pt-36 px-6 pb-14">
      <div className="container max-w-4xl mx-auto border border-border p-6 bg-black/40 space-y-4">
        <h1 className="text-3xl font-sentient">Report-Details</h1>
        <p className="font-mono text-sm">{report.address_input}</p>
        <div className="flex flex-wrap gap-3 items-center">
          {hasNoData || !report.ampel ? (
            <div className="inline-flex border px-3 py-1 text-sm uppercase font-mono text-foreground/40 border-foreground/20">
              Keine Daten
            </div>
          ) : (
            <div className={`inline-flex border px-3 py-1 text-sm uppercase font-mono ${AMPEL_STYLE[report.ampel]}`}>{report.ampel}</div>
          )}
          <p className="font-mono text-sm text-foreground/70">Score: {typeof report.geo_score === "number" ? report.geo_score : "k. A."}</p>
          <p className="font-mono text-sm text-foreground/70">Status: {report.status}</p>
        </div>
        <p className="font-mono text-sm text-foreground/70">
          Koordinaten: {report.latitude.toFixed(5)}, {report.longitude.toFixed(5)} | Radius: {report.radius_m}m
        </p>
        <p className="font-mono text-xs text-foreground/60">
          Module: {selectedModules.join(", ")}
        </p>
        {hasNoData ? (
          <p className="font-mono text-sm text-foreground/50">Für diesen Standort liegen aktuell keine Messpunkte vor.</p>
        ) : null}

        {/* ── classic: KPI grid + summary ── */}
        {modules.has("classic") ? (
          <>
            <div className="grid grid-cols-2 gap-4">
              <div className="border border-border p-4 text-center">
                <div className="text-2xl font-bold">{analysis.point_count ?? 0}</div>
                <div className="text-xs text-foreground/60 uppercase font-mono">Messpunkte</div>
              </div>
              <div className="border border-border p-4 text-center">
                <div className="text-2xl font-bold">
                  {typeof analysis.max_abs_velocity_mm_yr === "number" ? analysis.max_abs_velocity_mm_yr.toFixed(1) : "—"}
                </div>
                <div className="text-xs text-foreground/60 uppercase font-mono">Max. Geschwindigkeit (mm/a)</div>
              </div>
              <div className="border border-border p-4 text-center">
                <div className="text-2xl font-bold">
                  {typeof analysis.weighted_velocity_mm_yr === "number" ? analysis.weighted_velocity_mm_yr.toFixed(1) : "—"}
                </div>
                <div className="text-xs text-foreground/60 uppercase font-mono">Gewichtet (mm/a)</div>
              </div>
              <div className="border border-border p-4 text-center">
                <div className="text-2xl font-bold">{typeof report.geo_score === "number" ? report.geo_score : "k. A."}</div>
                <div className="text-xs text-foreground/60 uppercase font-mono">GeoScore</div>
              </div>
            </div>

            {analysis.summary ? (
              <p className="font-mono text-sm text-foreground/80 border border-border p-4">{analysis.summary}</p>
            ) : null}
          </>
        ) : null}

        {/* ── timeseries: velocity histogram ── */}
        {modules.has("timeseries") && histogramEntries.length > 0 ? (
          <div className="border border-border p-4 space-y-3">
            <p className="font-mono text-xs uppercase tracking-wide text-foreground/60">Velocity-Histogramm</p>
            <div className="space-y-2">
              {histogramEntries.map(([bin, value]) => {
                const pct = histogramMax > 0 ? Math.round((value / histogramMax) * 100) : 0;
                return (
                  <div key={bin} className="grid grid-cols-[70px_1fr_40px] items-center gap-3">
                    <span className="font-mono text-xs text-foreground/70">{bin}</span>
                    <div className="h-6 bg-foreground/10 border border-border/60 overflow-hidden">
                      <div className="h-full bg-primary/70" style={{ width: `${pct}%`, minWidth: "2px" }} />
                    </div>
                    <span className="font-mono text-xs text-foreground/70 text-right">{value}</span>
                  </div>
                );
              })}
            </div>
          </div>
        ) : modules.has("timeseries") ? (
          <div className="border border-border p-4">
            <p className="font-mono text-xs uppercase tracking-wide text-foreground/60">Velocity-Histogramm</p>
            <p className="font-mono text-sm text-foreground/40 mt-2">Keine Messdaten im Radius verfügbar.</p>
          </div>
        ) : null}

        {/* ── rawdata: measurement point table ── */}
        {modules.has("rawdata") && rawPoints.length > 0 ? (
          <div className="border border-border p-4 space-y-3">
            <p className="font-mono text-xs uppercase tracking-wide text-foreground/60">
              Messpunkte ({Math.min(rawPoints.length, 30)} von {analysis.point_count ?? rawPoints.length})
            </p>
            <div className="overflow-x-auto">
              <table className="w-full font-mono text-xs">
                <thead>
                  <tr className="border-b border-border text-foreground/60 uppercase">
                    <th className="py-2 px-2 text-left">Nr.</th>
                    <th className="py-2 px-2 text-right">Breitengrad</th>
                    <th className="py-2 px-2 text-right">Längengrad</th>
                    <th className="py-2 px-2 text-right">mm/a</th>
                    <th className="py-2 px-2 text-right">Entf. (m)</th>
                    <th className="py-2 px-2 text-right">Kohärenz</th>
                  </tr>
                </thead>
                <tbody>
                  {rawPoints.slice(0, 30).map((pt, idx) => (
                    <tr key={idx} className="border-b border-border/40 text-foreground/80">
                      <td className="py-1 px-2">{idx + 1}</td>
                      <td className="py-1 px-2 text-right">{pt.lat.toFixed(6)}</td>
                      <td className="py-1 px-2 text-right">{pt.lon.toFixed(6)}</td>
                      <td className="py-1 px-2 text-right">{pt.velocity_mm_yr.toFixed(2)}</td>
                      <td className="py-1 px-2 text-right">{pt.distance_m.toFixed(0)}</td>
                      <td className="py-1 px-2 text-right">{pt.coherence.toFixed(2)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        ) : modules.has("rawdata") ? (
          <div className="border border-border p-4">
            <p className="font-mono text-xs uppercase tracking-wide text-foreground/60">Messpunkte</p>
            <p className="font-mono text-sm text-foreground/40 mt-2">Keine Messpunkte im Radius gefunden.</p>
          </div>
        ) : null}

        {/* ── compliance: disclaimer + data sources ── */}
        {modules.has("compliance") ? (
          <div className="border border-border p-4 space-y-4">
            <div>
              <p className="font-mono text-xs uppercase tracking-wide text-foreground/60">Hinweis</p>
              <p className="font-mono text-xs text-foreground/70 mt-2 leading-relaxed">
                Diese Standortauskunft ist ein automatisiertes Datenscreening auf Basis von InSAR-Satellitendaten
                und ersetzt keine Ortsbesichtigung oder fachliche Einzelfallbewertung durch einen zugelassenen Sachverständigen.
              </p>
            </div>
            <div>
              <p className="font-mono text-xs uppercase tracking-wide text-foreground/60">Geprüfte Datenquellen</p>
              <div className="mt-2 space-y-1">
                {DATA_SOURCES.map((src) => (
                  <div key={src.name} className="flex items-start gap-2">
                    <span className={`font-mono text-sm ${src.status === "aktiv" ? "text-primary" : "text-foreground/30"}`}>
                      {src.status === "aktiv" ? "✓" : "○"}
                    </span>
                    <div>
                      <span className="font-mono text-xs text-foreground/80">{src.name}</span>
                      <span className="font-mono text-xs text-foreground/40 ml-2">— {src.desc}</span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        ) : null}

        {/* ── download / purchase ── */}
        {report.paid ? (
          <div className="flex gap-3">
            <button
              type="button"
              className="border border-primary px-4 py-2 font-mono text-sm uppercase"
              onClick={() => downloadFile(`/api/reports/${report.id}/pdf`, `report-${report.id}.pdf`)}
            >
              PDF herunterladen
            </button>
            <button
              type="button"
              className="border border-primary px-4 py-2 font-mono text-sm uppercase"
              onClick={() => downloadFile(`/api/reports/${report.id}/raw.csv`, `report-${report.id}.csv`)}
            >
              CSV herunterladen
            </button>
          </div>
        ) : (
          <button type="button" className="border border-primary px-4 py-2 font-mono text-sm uppercase" onClick={startCheckout}>
            Report kaufen
          </button>
        )}
      </div>
    </main>
  );
}
