"use client";

import { useState, type FormEvent } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { ArrowRight, Eye, EyeOff, Loader2, Sparkles } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { DEMO_ACCOUNT, getSupabase, safeNext } from "@/lib/supabase";

type Mode = "login" | "signup";

const TEXT = {
  login: {
    eyebrow: "Log in",
    title: "Welcome back",
    description: "Log in to review, correct and approve invoices.",
    submit: "Log in",
    switchText: "New to InvoiceIQ?",
    switchLink: { href: "/signup", label: "Create an account" },
  },
  signup: {
    eyebrow: "Sign up",
    title: "Create your account",
    description: "Your name goes on everything you upload, correct and approve.",
    submit: "Create account",
    switchText: "Already have an account?",
    switchLink: { href: "/login", label: "Log in" },
  },
} as const;

/** Email + password form for logging in or signing up, plus "Try the demo". */
export function AuthForm({ mode }: { mode: Mode }) {
  const router = useRouter();
  const next = safeNext(useSearchParams().get("next"));
  const [busy, setBusy] = useState<"form" | "demo" | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const text = TEXT[mode];

  function enterApp() {
    router.replace(next);
    router.refresh(); // the server now sees the login cookie
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const email = String(form.get("email")).trim();
    const password = String(form.get("password"));
    setBusy("form");
    setError(null);

    const supabase = getSupabase();
    if (mode === "login") {
      const { error: loginError } = await supabase.auth.signInWithPassword({ email, password });
      if (loginError) return fail(loginError.message);
      return enterApp();
    }

    const { data, error: signupError } = await supabase.auth.signUp({
      email,
      password,
      options: { data: { full_name: String(form.get("name")).trim() } },
    });
    if (signupError) return fail(signupError.message);
    if (!data.session) {
      // The project asks new users to confirm their email first.
      setBusy(null);
      return setNotice(`We sent a confirmation link to ${email}. Open it, then log in.`);
    }
    enterApp();
  }

  async function tryDemo() {
    if (!DEMO_ACCOUNT) return;
    setBusy("demo");
    setError(null);
    const { error: demoError } = await getSupabase().auth.signInWithPassword(DEMO_ACCOUNT);
    if (demoError) return fail(`The demo account isn't available: ${demoError.message}`);
    enterApp();
  }

  function fail(message: string) {
    setBusy(null);
    setError(message);
  }

  return (
    <div>
      <p className="eyebrow">{text.eyebrow}</p>
      <h2 className="mt-2 font-heading text-[2rem] leading-tight font-medium tracking-[-0.02em]">
        {text.title}
      </h2>
      <p className="mt-2 text-sm leading-relaxed text-muted-foreground">{text.description}</p>

      {notice ? (
        <p className="mt-8 rounded-md border border-primary/25 bg-primary/8 p-4 text-sm leading-relaxed">
          {notice}
        </p>
      ) : (
        <form onSubmit={handleSubmit} className="mt-8 flex flex-col gap-5">
          {mode === "signup" && (
            <Field label="Your name">
              <Input
                name="name"
                required
                maxLength={100}
                autoComplete="name"
                placeholder="Sara Ahmed"
                className="h-10"
              />
            </Field>
          )}
          <Field label="Work email">
            <Input
              name="email"
              type="email"
              required
              autoComplete="email"
              placeholder="you@company.com"
              className="h-10"
            />
          </Field>
          <Field label="Password">
            <PasswordInput mode={mode} />
          </Field>
          {error && (
            <p role="alert" className="rounded-md border border-destructive/30 bg-destructive/8 px-3 py-2 text-sm text-destructive">
              {error}
            </p>
          )}
          <Button type="submit" size="lg" disabled={busy !== null} className="mt-1 w-full">
            {busy === "form" ? <Loader2 className="animate-spin" /> : null}
            {text.submit}
            {busy !== "form" && <ArrowRight />}
          </Button>
        </form>
      )}

      {DEMO_ACCOUNT && (
        <div className="mt-8">
          <div className="flex items-center gap-3 text-xs text-muted-foreground">
            <span className="h-px flex-1 bg-border" />
            just looking?
            <span className="h-px flex-1 bg-border" />
          </div>
          <Button
            variant="outline"
            size="lg"
            onClick={tryDemo}
            disabled={busy !== null}
            className="mt-5 w-full"
          >
            {busy === "demo" ? <Loader2 className="animate-spin" /> : <Sparkles />}
            Try the demo
          </Button>
          <p className="mt-2 text-center text-xs text-muted-foreground">
            Opens a shared account with sample invoices. No sign-up needed.
          </p>
        </div>
      )}

      <p className="mt-10 text-sm text-muted-foreground">
        {text.switchText}{" "}
        <Link href={text.switchLink.href} className="font-medium text-primary hover:underline">
          {text.switchLink.label}
        </Link>
      </p>
    </div>
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <label className="flex flex-col gap-2">
      <span className="text-sm font-medium">{label}</span>
      {children}
    </label>
  );
}

function PasswordInput({ mode }: { mode: Mode }) {
  const [visible, setVisible] = useState(false);
  return (
    <span className="relative block">
      <Input
        name="password"
        type={visible ? "text" : "password"}
        required
        minLength={mode === "signup" ? 8 : undefined}
        autoComplete={mode === "signup" ? "new-password" : "current-password"}
        placeholder={mode === "signup" ? "At least 8 characters" : undefined}
        className="h-10 pr-10"
      />
      <Button
        type="button"
        variant="ghost"
        size="icon-sm"
        onClick={() => setVisible((current) => !current)}
        aria-label={visible ? "Hide password" : "Show password"}
        className="absolute top-1 right-1 text-muted-foreground"
      >
        {visible ? <EyeOff /> : <Eye />}
      </Button>
    </span>
  );
}
