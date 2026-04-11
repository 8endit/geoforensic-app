"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { toast } from "sonner";

import { useAuth } from "@/lib/auth-context";

export default function LoginPage() {
  const router = useRouter();
  const { login } = useAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);

  const onSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    try {
      await login(email, password);
      toast.success("Login erfolgreich.");
      router.push("/dashboard");
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "Login fehlgeschlagen.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <main className="min-h-screen pt-40 px-6">
      <div className="mx-auto max-w-md border border-border p-6 bg-black/40">
        <h1 className="text-2xl font-sentient mb-6">Sign In</h1>
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
          <button type="submit" disabled={loading} className="w-full border border-primary py-3 font-mono uppercase">
            {loading ? "..." : "Login"}
          </button>
        </form>
        <p className="mt-4 text-sm text-foreground/70">
          Kein Konto?{" "}
          <Link href="/register" className="text-primary">
            Registrieren
          </Link>
        </p>
      </div>
    </main>
  );
}

