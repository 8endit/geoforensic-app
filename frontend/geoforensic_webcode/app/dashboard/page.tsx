"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { toast } from "sonner";

import { getReports, type ReportListItem } from "@/lib/api";
import { useAuth } from "@/lib/auth-context";

export default function DashboardPage() {
  const router = useRouter();
  const { token, user, isLoading } = useAuth();
  const [reports, setReports] = useState<ReportListItem[]>([]);
  const [loadingReports, setLoadingReports] = useState(true);

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
                  Status: {report.status} | Ampel: {report.ampel ?? "n/a"} | Score: {report.geo_score ?? "n/a"} |{" "}
                  {report.paid ? "paid" : "unpaid"}
                </p>
              </Link>
            ))}
          </div>
        )}
      </div>
    </main>
  );
}

