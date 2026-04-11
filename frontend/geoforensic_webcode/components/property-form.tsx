"use client";

import { Button } from "./ui/button";
import { useState } from "react";

export function PropertyForm() {
  const [street, setStreet] = useState("");
  const [postalCity, setPostalCity] = useState("");

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    // Handle form submission
    console.log({ street, postalCity });
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

          <Button type="submit" className="w-full mt-8">
            [Generate Report]
          </Button>
        </form>
      </div>
    </section>
  );
}
