export const Logo = ({ className }: { className?: string }) => {
  return (
    <span className={`font-mono text-xl md:text-2xl font-bold tracking-tight text-foreground ${className || ""}`}>
      geoforensic
    </span>
  );
};
