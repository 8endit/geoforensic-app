"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useMemo, useState } from "react";
import { toast } from "sonner";

import { getReports, type ReportListItem } from "@/lib/api";
import { useAuth } from "@/lib/auth-context";

export default function DashboardPage() {
  const router = useRouter();
  const { token, user, isLoading } = useAuth();
  const [reports, setReports] = useState<ReportListItem[]>([]);
  const [loadingReports, setLoadingReports] = useState(true);

  const stats = useMemo(() => {
    let scoredReports = 0;
    let noDataReports = 0;
    let processingReports = 0;
    let failedReports = 0;
    let totalScore = 0;

    for (const report of reports) {
      if (report.status === "processing") {
        processingReports += 1;
      } else if (report.status === "failed") {
        failedReports += 1;
      }

      if (typeof report.geo_score === "number") {
        scoredReports += 1;
        totalScore += report.geo_score;
      } else if (report.status === "completed") {
        // Completed without score means "no EGMS data in radius".
        noDataReports += 1;
      }
    }

    return {
      totalReports: reports.length,
      scoredReports,
      noDataReports,
      processingReports,
      failedReports,
      avgScore: scoredReports > 0 ? Math.round((totalScore / scoredReports) * 10) / 10 : null,
    };
  }, [reports]);

  useEffect(() => {
    if (isLoading) return;
    if (!token) {
      router.push("/login");
      return;
    }
    getReports(token)
      .then(setReports)
      .catch((error) => toast.error(error instanceof Error ? error.message : "Reports konnten nicht geladen werden."))
      .finally(() => setLoadingReports(false));
  }, [token, isLoading, router]);

  return (
    <main className="min-h-screen pt-36 px-6 pb-14">
      <div className="container max-w-4xl mx-auto">
        <div className="flex justify-between items-center mb-8">
          <div>
            <h1 className="text-3xl font-sentient">Dashboard</h1>
            <p className="font-mono text-sm text-foreground/70">{user?.email}</p>
          </div>
          <Link href="/#contact" className="border border-primary px-4 py-2 font-mono uppercase text-sm">
            Neuer Report
          </Link>
        </div>

        {loadingReports ? (
          <p className="font-mono text-sm">Lade Reports...</p>
        ) : reports.length === 0 ? (
          <p className="font-mono text-sm text-foreground/70">Noch keine Reports vorhanden.</p>
        ) : (
          <div className="space-y-5">
            <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
              <div className="border border-border p-3">
                <p className="font-mono text-[11px] uppercase text-foreground/60">Reports</p>
                <p className="font-mono text-lg mt-1">{stats.totalReports}</p>
              </div>
              <div className="border border-border p-3">
                <p className="font-mono text-[11px] uppercase text-foreground/60">Avg Score</p>
                <p className="font-mono text-lg mt-1">{stats.avgScore ?? "k. A."}</p>
              </div>
              <div className="border border-border p-3">
                <p className="font-mono text-[11px] uppercase text-foreground/60">Mit Score</p>
                <p className="font-mono text-lg mt-1">{stats.scoredReports}</p>
              </div>
              <div className="border border-border p-3">
                <p className="font-mono text-[11px] uppercase text-foreground/60">Ohne Daten</p>
                <p className="font-mono text-lg mt-1">{stats.noDataReports}</p>
              </div>
              <div className="border border-border p-3">
                <p className="font-mono text-[11px] uppercase text-foreground/60">Processing</p>
                <p className="font-mono text-lg mt-1">{stats.processingReports}</p>
              </div>
              <div className="border border-border p-3">
                <p className="font-mono text-[11px] uppercase text-foreground/60">Failed</p>
                <p className="font-mono text-lg mt-1">{stats.failedReports}</p>
              </div>
            </div>

            <div className="space-y-3">
              {reports.map((report) => (
                <Link
                  key={report.id}
                  href={`/reports/${report.id}`}
                  className="block border border-border p-4 hover:border-primary/60 transition-colors"
                >
                  <p className="font-mono text-xs text-foreground/60">{new Date(report.created_at).toLocaleString()}</p>
                  <p className="font-mono text-sm mt-1">{report.address_input}</p>
                  <p className="font-mono text-xs mt-2 text-foreground/70">
                    Status: {report.status} | Ampel: {report.ampel ?? "k. A."} | Score: {report.geo_score ?? "k. A."} |{" "}
                    {report.paid ? "Bezahlt" : "Offen"}
                  </p>
                </Link>
              ))}
            </div>
          </div>
        )}
      </div>
    </main>
  );
}

