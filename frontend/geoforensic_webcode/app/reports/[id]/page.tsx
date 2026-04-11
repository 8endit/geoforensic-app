"use client";

import { useParams, useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { toast } from "sonner";

import { API_URL, checkout, getReport, type ReportDetail } from "@/lib/api";
import { useAuth } from "@/lib/auth-context";

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

  return (
    <main className="min-h-screen pt-36 px-6 pb-14">
      <div className="container max-w-4xl mx-auto border border-border p-6 bg-black/40 space-y-4">
        <h1 className="text-3xl font-sentient">Report Detail</h1>
        <p className="font-mono text-sm">{report.address_input}</p>
        <p className="font-mono text-sm text-foreground/70">
          Ampel: {report.ampel ?? "n/a"} | Score: {report.geo_score ?? "n/a"} | Status: {report.status}
        </p>
        <p className="font-mono text-sm text-foreground/70">
          Koordinaten: {report.latitude.toFixed(5)}, {report.longitude.toFixed(5)} | Radius: {report.radius_m}m
        </p>

        <div className="border border-border p-4 font-mono text-sm text-foreground/80">
          <pre className="whitespace-pre-wrap">
            {JSON.stringify(report.report_data ?? { hint: "Noch keine Analysedaten vorhanden." }, null, 2)}
          </pre>
        </div>

        {report.paid ? (
          <div className="flex gap-3">
            <button
              type="button"
              className="border border-primary px-4 py-2 font-mono text-sm uppercase"
              onClick={() => downloadFile(`/api/reports/${report.id}/pdf`, `report-${report.id}.pdf`)}
            >
              PDF Download
            </button>
            <button
              type="button"
              className="border border-primary px-4 py-2 font-mono text-sm uppercase"
              onClick={() => downloadFile(`/api/reports/${report.id}/raw.csv`, `report-${report.id}.csv`)}
            >
              CSV Download
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

