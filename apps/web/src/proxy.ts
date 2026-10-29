import { createServerClient } from "@supabase/ssr";
import { NextResponse, type NextRequest } from "next/server";

// Where the FastAPI backend runs. Browser requests to /api/* are forwarded there.
const API_URL = process.env.API_URL ?? "http://localhost:8001";
const PUBLIC_PAGES = ["/login", "/signup"];

type Cookie = { name: string; value: string; options: Record<string, unknown> };

/**
 * Runs before every page and API request:
 * - keeps the Supabase login fresh (an expired token is renewed and saved in cookies),
 * - sends visitors who are not logged in to /login,
 * - forwards /api/* to FastAPI with the login token, which the API checks itself.
 */
export async function proxy(request: NextRequest) {
  const renewed: Cookie[] = [];
  const noCache: Record<string, string> = {};
  const supabase = createServerClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY!,
    {
      cookies: {
        getAll: () => request.cookies.getAll(),
        setAll(cookies, headers) {
          for (const cookie of cookies) {
            request.cookies.set(cookie.name, cookie.value);
            renewed.push(cookie);
          }
          Object.assign(noCache, headers);
        },
      },
    },
  );

  const response = request.nextUrl.pathname.startsWith("/api/")
    ? await forwardToApi(request, supabase)
    : await guardPage(request, supabase);

  for (const { name, value, options } of renewed) response.cookies.set(name, value, options);
  for (const [key, value] of Object.entries(noCache)) response.headers.set(key, value);
  return response;
}

type Supabase = ReturnType<typeof createServerClient>;

async function forwardToApi(request: NextRequest, supabase: Supabase) {
  // Not verified here (that's the API's job); this renews the token if it expired.
  const { data } = await supabase.auth.getSession();
  const headers = new Headers(request.headers);
  headers.delete("authorization"); // only the proxy decides who is calling
  if (data.session) headers.set("authorization", `Bearer ${data.session.access_token}`);

  const { pathname, search } = request.nextUrl;
  return NextResponse.rewrite(new URL(pathname + search, API_URL), { request: { headers } });
}

async function guardPage(request: NextRequest, supabase: Supabase) {
  // getClaims verifies the token's signature, so a made-up cookie doesn't count.
  const { data } = await supabase.auth.getClaims();
  const signedIn = Boolean(data?.claims);
  const { pathname, search } = request.nextUrl;
  const isPublic = PUBLIC_PAGES.includes(pathname);

  if (!signedIn && !isPublic) {
    const login = new URL("/login", request.url);
    if (pathname !== "/") login.searchParams.set("next", pathname + search);
    return NextResponse.redirect(login);
  }
  if (signedIn && isPublic) {
    return NextResponse.redirect(new URL("/", request.url));
  }
  return NextResponse.next({ request });
}

export const config = {
  // Everything except Next.js files and static images.
  matcher: ["/((?!_next/static|_next/image|favicon.ico|.*\\.(?:svg|png|jpg|jpeg|gif|webp)$).*)"],
};
