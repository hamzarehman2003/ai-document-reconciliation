import { Suspense } from "react";
import type { Metadata } from "next";

import { AuthForm } from "@/components/auth/auth-form";
import { Skeleton } from "@/components/ui/skeleton";

export const metadata: Metadata = { title: "Log in" };

// The form reads ?next= from the URL, so it sits inside <Suspense>.
export default function LoginPage() {
  return (
    <Suspense fallback={<Skeleton className="h-[30rem]" />}>
      <AuthForm mode="login" />
    </Suspense>
  );
}
