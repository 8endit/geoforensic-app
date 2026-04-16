"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { toast } from "sonner";

import { PreviewResult } from "@/components/preview-result";
import { ApiError, createReport, previewReport, type PreviewResponse } from "@/lib/api";
import { useAuth } from "@/lib/auth-context";
import { Button } from "./ui/button";

const REPORT_MODULES = [
  { id: "classic", label: "Report klassisch", hint: "Ampel + GeoScore + Basisanalyse (Pflichtmodul)", locked: true },
  { id: "timeseries", label: "Zeitreihe", hint: "Velocity-Histogramm + Verschiebungstrend", locked: false },
  { id: "rawdata", label: "Rohdaten", hint: "Messpunkt-Tabelle mit Koordinaten + Geschwindigkeit", locked: false },
  { id: "compliance", label: "Compliance", hint: "Disclaimer + geprüfte Datenquellen + Attribution", locked: false },
] as const;

export function PropertyForm() {
  const [street, setStreet] = useState("");
  const [houseNumber, setHouseNumber] = useState("");
  const [postalCode, setPostalCode] = useState("");
  const [city, setCity] = useState("");
  const [country, setCountry] = useState("DE");
  const [freeAddress, setFreeAddress] = useState("");
  const [aktenzeichen, setAktenzeichen] = useState("");
  const [selectedModules, setSelectedModules] = useState<string[]>(["classic"]);
  const [preview, setPreview] = useState<PreviewResponse | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const { user, token } = useAuth();
  const router = useRouter();

  const toggleModule = (moduleId: string) => {
    if (moduleId === "classic") return; // Pflichtmodul, immer aktiv
    setSelectedModules((prev) =>
      prev.includes(moduleId) ? prev.filter((id) => id !== moduleId) : [...prev, moduleId],
    );
  };

  const buildAddress = () => {
    const free = freeAddress.trim();
    if (free.length >= 5) return free;

    return [street.trim(), houseNumber.trim(), postalCode.trim(), city.trim(), country.trim()]
      .filter(Boolean)
      .join(" ");
  };

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
      toast.success("Vorschau erfolgreich geladen.");
    } catch (error) {
      if (error instanceof ApiError && error.status === 429) {
        toast.error("Zu viele Anfragen. Bitte warten Sie einige Minuten.");
        return;
      }
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
      const created = await createReport(
        {
          address,
          radius_m: 500,
          aktenzeichen: aktenzeichen.trim() || undefined,
          selected_modules: selectedModules,
        },
        token
      );
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
          Grundstück <i className="font-light">prüfen</i>
        </h2>

        <form onSubmit={handleSubmit} className="space-y-6">
          <div>
            <label className="block mb-2 font-mono text-xs uppercase text-foreground/60">Freie Adresse (optional)</label>
            <input
              type="text"
              placeholder="z.B. Musterstr. 12, 45127 Essen, DE"
              value={freeAddress}
              onChange={(e) => setFreeAddress(e.target.value)}
              className="w-full bg-transparent border border-border px-4 py-4 font-mono text-sm text-foreground placeholder:text-foreground/40 focus:outline-none focus:border-primary transition-colors"
            />
            <p className="mt-2 font-mono text-xs text-foreground/50">
              Du kannst frei schreiben oder die Felder darunter in beliebiger Reihenfolge fuellen.
            </p>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <input
                type="text"
                placeholder="Straße"
                value={street}
                onChange={(e) => setStreet(e.target.value)}
                className="w-full bg-transparent border border-border px-4 py-4 font-mono text-sm text-foreground placeholder:text-foreground/40 focus:outline-none focus:border-primary transition-colors"
              />
            </div>
            <div>
              <input
                type="text"
                placeholder="Hausnummer"
                value={houseNumber}
                onChange={(e) => setHouseNumber(e.target.value)}
                className="w-full bg-transparent border border-border px-4 py-4 font-mono text-sm text-foreground placeholder:text-foreground/40 focus:outline-none focus:border-primary transition-colors"
              />
            </div>
            <div>
              <input
                type="text"
                placeholder="PLZ"
                value={postalCode}
                onChange={(e) => setPostalCode(e.target.value)}
                className="w-full bg-transparent border border-border px-4 py-4 font-mono text-sm text-foreground placeholder:text-foreground/40 focus:outline-none focus:border-primary transition-colors"
              />
            </div>
            <div>
              <input
                type="text"
                placeholder="Stadt"
                value={city}
                onChange={(e) => setCity(e.target.value)}
                className="w-full bg-transparent border border-border px-4 py-4 font-mono text-sm text-foreground placeholder:text-foreground/40 focus:outline-none focus:border-primary transition-colors"
              />
            </div>
            <div className="sm:col-span-2">
              <input
                type="text"
                placeholder="Land (z.B. DE oder NL)"
                value={country}
                onChange={(e) => setCountry(e.target.value)}
                className="w-full bg-transparent border border-border px-4 py-4 font-mono text-sm text-foreground placeholder:text-foreground/40 focus:outline-none focus:border-primary transition-colors"
              />
            </div>
          </div>

          <div className="border border-border p-4 space-y-3 bg-black/30">
            <p className="font-mono text-xs uppercase text-foreground/60">Module vor Generierung</p>
            <div className="space-y-2">
              {REPORT_MODULES.map((module) => {
                const checked = selectedModules.includes(module.id);
                return (
                  <label key={module.id} className={`flex items-start gap-3 ${module.locked ? "opacity-70" : "cursor-pointer"}`}>
                    <input
                      type="checkbox"
                      checked={checked}
                      disabled={module.locked}
                      onChange={() => toggleModule(module.id)}
                      className="mt-1 accent-lime-500 disabled:opacity-50"
                    />
                    <span className="font-mono text-sm text-foreground/80">
                      {module.label}
                      <span className="block text-xs text-foreground/50 mt-1">{module.hint}</span>
                    </span>
                  </label>
                );
              })}
            </div>
          </div>

          <div>
            <input
              type="text"
              placeholder="Aktenzeichen (optional)"
              value={aktenzeichen}
              onChange={(e) => setAktenzeichen(e.target.value)}
              className="w-full bg-transparent border border-border px-4 py-4 font-mono text-sm text-foreground placeholder:text-foreground/40 focus:outline-none focus:border-primary transition-colors"
            />
          </div>

          <Button type="submit" className="w-full mt-8" disabled={isSubmitting}>
            {isSubmitting ? "Lädt..." : "Vorschau berechnen"}
          </Button>
        </form>

        {preview ? (
          <PreviewResult data={preview} isAuthenticated={Boolean(user)} onCreateReport={handleCreateReport} />
        ) : null}
      </div>
    </section>
  );
}
