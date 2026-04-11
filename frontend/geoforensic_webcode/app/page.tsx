'use client'

import { Hero } from "@/components/hero";
import { PropertyForm } from "@/components/property-form";
import { Leva } from "leva";

export default function Home() {
  return (
    <>
      <Hero />
      <PropertyForm />
      <Leva hidden />
    </>
  );
}
