import { LoginForm } from "@/components/login/login-form";

export default async function LoginPage({
  searchParams,
}: {
  searchParams: Promise<{ next?: string }>;
}) {
  const { next } = await searchParams;

  return (
    <div className="flex min-h-screen items-center justify-center bg-graphite px-6 py-10">
      <LoginForm next={next} />
    </div>
  );
}
