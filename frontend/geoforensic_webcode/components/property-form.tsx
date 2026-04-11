"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { toast } from "sonner";

import { PreviewResult } from "@/components/preview-result";
import { createReport, previewReport, type PreviewResponse } from "@/lib/api";
import { useAuth } from "@/lib/auth-context";
import { Button } from "./ui/button";

export function PropertyForm() {
  const [street, setStreet] = useState("");
  const [postalCity, setPostalCity] = useState("");
  const [preview, setPreview] = useState<PreviewResponse | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const { user, token } = useAuth();
  const router = useRouter();

  const buildAddress = () => `${street.trim()} ${postalCity.trim()}`.trim();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const address = buildAddress();
    if (!address || address.length < 5) {
      toast.error("Bitte vollständige Adresse eingeben.");
      return;
    }

    setIsSubmitting(true);
    try {
      const result = await previewReport({ address });
      setPreview(result);
      toast.success("Preview erfolgreich geladen.");
    } catch (error) {
      const message = error instanceof Error ? error.message : "Preview fehlgeschlagen.";
      toast.error(message);
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleCreateReport = async () => {
    const address = buildAddress();
    if (!address) return;
    if (!token) {
      router.push("/login");
      return;
    }

    setIsSubmitting(true);
    try {
      const created = await createReport({ address, radius_m: 500 }, token);
      toast.success("Report wurde erstellt.");
      router.push(`/reports/${created.id}`);
    } catch (error) {
      const message = error instanceof Error ? error.message : "Report-Erstellung fehlgeschlagen.";
      toast.error(message);
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <section
      id="contact"
      className="min-h-svh flex items-center justify-center px-6 py-24 bg-background relative z-10"
    >
      <div className="w-full max-w-md">
        <h2 className="text-3xl sm:text-4xl font-sentient text-center mb-12">
          Check your <i className="font-light">property</i>
        </h2>

        <form onSubmit={handleSubmit} className="space-y-6">
          <div>
            <input
              type="text"
              placeholder="Street + house number"
              value={street}
              onChange={(e) => setStreet(e.target.value)}
              className="w-full bg-transparent border border-border px-4 py-4 font-mono text-sm text-foreground placeholder:text-foreground/40 focus:outline-none focus:border-primary transition-colors"
            />
          </div>

          <div>
            <input
              type="text"
              placeholder="Postal code + city"
              value={postalCity}
              onChange={(e) => setPostalCity(e.target.value)}
              className="w-full bg-transparent border border-border px-4 py-4 font-mono text-sm text-foreground placeholder:text-foreground/40 focus:outline-none focus:border-primary transition-colors"
            />
          </div>

          <Button type="submit" className="w-full mt-8" disabled={isSubmitting}>
            {isSubmitting ? "Loading..." : "Preview berechnen"}
          </Button>
        </form>

        {preview ? (
          <PreviewResult data={preview} isAuthenticated={Boolean(user)} onCreateReport={handleCreateReport} />
        ) : null}
      </div>
    </section>
  );
}
