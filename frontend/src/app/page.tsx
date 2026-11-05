import { Button } from "@/components/ui/button";
import { BookOpen, Users, BarChart3, ShieldCheck } from "lucide-react";

const features = [
  {
    title: "Student records",
    description: "Centralise enrolment, profiles and academic history for every learner.",
    icon: Users,
  },
  {
    title: "Academics",
    description: "Manage classes, subjects, timetables and examinations in one place.",
    icon: BookOpen,
  },
  {
    title: "Reporting",
    description: "Gain clear insights into attendance, performance and institutional health.",
    icon: BarChart3,
  },
  {
    title: "Secure by design",
    description: "Multi-tenant isolation with role-based access for staff and families.",
    icon: ShieldCheck,
  },
];

export default function Home() {
  return (
    <div className="flex min-h-screen flex-col">
      <header className="border-b border-border">
        <div className="mx-auto flex w-full max-w-6xl items-center justify-between px-6 py-4">
          <div className="text-lg font-semibold">Student Management SaaS</div>
          <nav className="hidden items-center gap-6 text-sm text-muted-foreground md:flex">
            <a href="#features" className="hover:text-foreground">
              Features
            </a>
            <a href="#benefits" className="hover:text-foreground">
              Benefits
            </a>
            <a href="#contact" className="hover:text-foreground">
              Contact
            </a>
          </nav>
          <div className="flex items-center gap-2">
            <Button variant="ghost" size="sm">
              Sign in
            </Button>
            <Button size="sm">Get started</Button>
          </div>
        </div>
      </header>

      <main className="flex-1">
        <section className="mx-auto w-full max-w-6xl px-6 py-20">
          <div className="max-w-2xl">
            <h1 className="text-4xl font-bold tracking-tight sm:text-5xl">
              A modern education management platform for schools, colleges and
              educational institutions.
            </h1>
            <p className="mt-6 text-lg text-muted-foreground">
              Student Management SaaS helps institutions streamline admissions,
              student records, academics, attendance and reporting from a single,
              secure platform.
            </p>
            <div className="mt-8 flex flex-wrap gap-3">
              <Button size="lg">Request a demo</Button>
              <Button variant="outline" size="lg">
                Learn more
              </Button>
            </div>
          </div>
        </section>

        <section id="features" className="border-t border-border bg-muted/40">
          <div className="mx-auto w-full max-w-6xl px-6 py-16">
            <h2 className="text-2xl font-semibold">Core capabilities</h2>
            <div className="mt-8 grid gap-6 sm:grid-cols-2 lg:grid-cols-4">
              {features.map((feature) => (
                <div
                  key={feature.title}
                  className="rounded-lg border border-border bg-background p-5"
                >
                  <feature.icon className="h-6 w-6 text-primary" />
                  <h3 className="mt-3 font-medium">{feature.title}</h3>
                  <p className="mt-1 text-sm text-muted-foreground">
                    {feature.description}
                  </p>
                </div>
              ))}
            </div>
          </div>
        </section>

        <section id="benefits" className="mx-auto w-full max-w-6xl px-6 py-16">
          <h2 className="text-2xl font-semibold">Why institutions choose us</h2>
          <ul className="mt-6 grid gap-4 text-muted-foreground sm:grid-cols-2">
            <li>Reduce administrative workload across departments.</li>
            <li>Improve data accuracy with a single source of truth.</li>
            <li>Give staff, students and parents the right access.</li>
            <li>Scale from a single campus to a multi-site organisation.</li>
          </ul>
        </section>

        <section id="contact" className="border-t border-border bg-muted/40">
          <div className="mx-auto w-full max-w-6xl px-6 py-16 text-center">
            <h2 className="text-2xl font-semibold">Ready to get started?</h2>
            <p className="mt-2 text-muted-foreground">
              Contact us to schedule a personalised walkthrough.
            </p>
            <div className="mt-6">
              <Button size="lg">Contact sales</Button>
            </div>
          </div>
        </section>
      </main>

      <footer className="border-t border-border">
        <div className="mx-auto w-full max-w-6xl px-6 py-6 text-sm text-muted-foreground">
          © {new Date().getFullYear()} Student Management SaaS. All rights
          reserved.
        </div>
      </footer>
    </div>
  );
}
