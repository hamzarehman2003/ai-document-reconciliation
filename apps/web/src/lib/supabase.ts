import { createBrowserClient } from "@supabase/ssr";

/** Supabase in the browser: sign up, log in, log out. The session lives in cookies,
 * which `proxy.ts` reads on the server. */
export function getSupabase() {
  return createBrowserClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY!,
  );
}

/** The ready-made demo account behind "Try the demo" (only shown when set). */
export const DEMO_ACCOUNT =
  process.env.NEXT_PUBLIC_DEMO_EMAIL && process.env.NEXT_PUBLIC_DEMO_PASSWORD
    ? {
        email: process.env.NEXT_PUBLIC_DEMO_EMAIL,
        password: process.env.NEXT_PUBLIC_DEMO_PASSWORD,
      }
    : null;

/** Only go back to pages of this app after logging in (no "//evil.com"). */
export function safeNext(next: string | null): string {
  return next?.startsWith("/") && !next.startsWith("//") ? next : "/";
}
