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
  const [companyName, setCompanyName] = useState("");
  const [gutachterType, setGutachterType] = useState("");
  const [loading, setLoading] = useState(false);

  const onSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
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
        <h1 className="text-2xl font-sentient mb-6">Register</h1>
        <form onSubmit={onSubmit} className="space-y-4">
          <input
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="Email"
            className="w-full bg-transparent border border-border px-4 py-3 font-mono text-sm"
            required
          />
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            placeholder="Password"
            className="w-full bg-transparent border border-border px-4 py-3 font-mono text-sm"
            required
          />
          <input
            type="text"
            value={companyName}
            onChange={(e) => setCompanyName(e.target.value)}
            placeholder="Company (optional)"
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
            {loading ? "..." : "Account erstellen"}
          </button>
        </form>
        <p className="mt-4 text-sm text-foreground/70">
          Bereits registriert?{" "}
          <Link href="/login" className="text-primary">
            Login
          </Link>
        </p>
      </div>
    </main>
  );
}

