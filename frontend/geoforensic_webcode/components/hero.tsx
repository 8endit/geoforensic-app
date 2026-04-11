"use client";

import { GL } from "./gl";
import { Pill } from "./pill";
import { Button } from "./ui/button";
import { useState } from "react";

export function Hero() {
  const [hovering, setHovering] = useState(false);

  const scrollToForm = () => {
    const element = document.getElementById("contact");
    if (element) {
      element.scrollIntoView({ behavior: "smooth" });
    }
  };

  return (
    <div className="flex flex-col h-svh justify-between">
      <GL hovering={hovering} />

      <div className="pb-16 mt-auto text-center relative">
        <Pill className="mb-6">BETA RELEASE</Pill>
        <h1 className="text-5xl sm:text-6xl md:text-7xl font-sentient">
          Every <i className="font-light">address</i>
          <br />
          has a story.
        </h1>
        <p className="font-mono text-sm sm:text-base text-foreground/60 text-balance mt-8 max-w-[540px] mx-auto">
          Discover what&apos;s happening above and below your property — ground movement, flood risk, and nearby construction in one report.
        </p>

        <Button
          className="mt-14 max-sm:hidden"
          onMouseEnter={() => setHovering(true)}
          onMouseLeave={() => setHovering(false)}
          onClick={scrollToForm}
        >
          [Check My Property]
        </Button>
        <Button
          size="sm"
          className="mt-14 sm:hidden"
          onMouseEnter={() => setHovering(true)}
          onMouseLeave={() => setHovering(false)}
          onClick={scrollToForm}
        >
          [Check My Property]
        </Button>
      </div>
    </div>
  );
}
