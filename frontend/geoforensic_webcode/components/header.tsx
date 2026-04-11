"use client";

import Link from "next/link";

import { useAuth } from "@/lib/auth-context";
import { Logo } from "./logo";
import { MobileMenu } from "./mobile-menu";

export const Header = () => {
  const { user, logout } = useAuth();

  return (
    <div className="fixed z-50 pt-8 md:pt-14 top-0 left-0 w-full">
      <header className="flex items-center justify-between container">
        <Link href="/">
          <Logo className="w-[100px] md:w-[120px]" />
        </Link>
        <nav className="flex max-lg:hidden absolute left-1/2 -translate-x-1/2 items-center justify-center gap-x-10">
          {[
            { name: "About", href: "#about" },
            { name: "Insights", href: "#insights" },
            { name: "Check My Property", href: "#contact" },
          ].map((item) => (
            <Link
              className="uppercase inline-block font-mono text-foreground/60 hover:text-foreground/100 duration-150 transition-colors ease-out"
              href={item.href}
              key={item.name}
            >
              {item.name}
            </Link>
          ))}
        </nav>
        {user ? (
          <div className="hidden lg:flex items-center gap-4">
            <Link
              className="uppercase transition-colors ease-out duration-150 font-mono text-primary hover:text-primary/80"
              href="/dashboard"
            >
              Dashboard
            </Link>
            <button
              type="button"
              onClick={logout}
              className="uppercase transition-colors ease-out duration-150 font-mono text-foreground/70 hover:text-foreground"
            >
              Logout
            </button>
          </div>
        ) : (
          <Link
            className="uppercase max-lg:hidden transition-colors ease-out duration-150 font-mono text-primary hover:text-primary/80"
            href="/login"
          >
            Sign In
          </Link>
        )}
        <MobileMenu />
      </header>
    </div>
  );
};
