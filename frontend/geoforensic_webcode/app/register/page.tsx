"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { toast } from "sonner";

import { useAuth } from "@/lib/auth-context";

export default function RegisterPage() {
  const router = useRouter();
  const { register } = useAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [companyName, setCompanyName] = useState("");
  const [gutachterType, setGutachterType] = useState("");
  const [loading, setLoading] = useState(false);

  const passwordStrength = (() => {
    let score = 0;
    if (password.length >= 8) score += 1;
    if (/[A-Z]/.test(password) && /[a-z]/.test(password)) score += 1;
    if (/\d/.test(password) || /[^A-Za-z0-9]/.test(password)) score += 1;
    if (score <= 1) return { label: "schwach", color: "text-red-400" };
    if (score === 2) return { label: "mittel", color: "text-yellow-300" };
    return { label: "stark", color: "text-green-400" };
  })();

  const onSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (password !== confirmPassword) {
      toast.error("Passwörter stimmen nicht überein.");
      return;
    }
    if (password.length < 8) {
      toast.error("Passwort muss mindestens 8 Zeichen haben.");
      return;
    }

    setLoading(true);
    try {
      await register({
        email,
        password,
        company_name: companyName || undefined,
        gutachter_type: gutachterType || undefined,
      });
      toast.success("Registrierung erfolgreich.");
      router.push("/dashboard");
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "Registrierung fehlgeschlagen.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <main className="min-h-screen pt-40 px-6">
      <div className="mx-auto max-w-md border border-border p-6 bg-black/40">
        <h1 className="text-2xl font-sentient mb-6">Registrieren</h1>
        <form onSubmit={onSubmit} className="space-y-4">
          <input
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="E-Mail-Adresse"
            className="w-full bg-transparent border border-border px-4 py-3 font-mono text-sm"
            required
          />
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            placeholder="Passwort"
            className="w-full bg-transparent border border-border px-4 py-3 font-mono text-sm"
            required
          />
          <div className="space-y-1">
            <p className="font-mono text-xs text-foreground/60">Mindestens 8 Zeichen</p>
            {password.length > 0 ? (
              <p className={`font-mono text-xs uppercase ${passwordStrength.color}`}>Sicherheit: {passwordStrength.label}</p>
            ) : null}
          </div>
          <input
            type="password"
            value={confirmPassword}
            onChange={(e) => setConfirmPassword(e.target.value)}
            placeholder="Passwort bestätigen"
            className="w-full bg-transparent border border-border px-4 py-3 font-mono text-sm"
            required
          />
          <input
            type="text"
            value={companyName}
            onChange={(e) => setCompanyName(e.target.value)}
            placeholder="Firma (optional)"
            className="w-full bg-transparent border border-border px-4 py-3 font-mono text-sm"
          />
          <input
            type="text"
            value={gutachterType}
            onChange={(e) => setGutachterType(e.target.value)}
            placeholder="Gutachtertyp (optional)"
            className="w-full bg-transparent border border-border px-4 py-3 font-mono text-sm"
          />
          <button type="submit" disabled={loading} className="w-full border border-primary py-3 font-mono uppercase">
            {loading ? "..." : "Konto erstellen"}
          </button>
        </form>
        <p className="mt-4 text-sm text-foreground/70">
          Bereits registriert?{" "}
          <Link href="/login" className="text-primary">
            Anmelden
          </Link>
        </p>
      </div>
    </main>
  );
}

