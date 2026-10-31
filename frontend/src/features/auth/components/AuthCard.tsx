import type { ReactNode } from "react";

interface AuthCardProps {
  title: string;
  subtitle?: string;
  children: ReactNode;
  footer?: ReactNode;
}

export function AuthCard({ title, subtitle, children, footer }: AuthCardProps) {
  return (
    <section className="container-page grid place-items-center py-12 md:py-20">
      <div className="w-full max-w-md rounded-3xl bg-linear-to-br from-primary/60 via-white/10 to-electric/40 p-px shadow-[0_30px_80px_-40px_rgb(255_100_45/0.7)]">
        <div className="rounded-[calc(1.5rem-1px)] bg-[#131519] p-6 md:p-8">
          <h1 className="text-4xl font-extrabold">{title}</h1>
          {subtitle && <p className="mt-2 text-sm text-muted-foreground">{subtitle}</p>}
          <div className="mt-6">{children}</div>
          {footer && <div className="mt-6 text-center text-sm text-muted-foreground">{footer}</div>}
        </div>
      </div>
    </section>
  );
}

export function FormAlert({ message }: { message: string | null }) {
  if (!message) return null;
  return (
    <p role="alert" className="rounded-md border border-destructive/40 bg-destructive/10 px-3 py-2 text-sm text-destructive">
      {message}
    </p>
  );
}
