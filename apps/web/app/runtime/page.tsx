import { Suspense } from "react";
import { RuntimeScreen } from "@/components/runtime/runtime-screen";

export default function RuntimePage() {
  return (
    <Suspense fallback={null}>
      <RuntimeScreen />
    </Suspense>
  );
}
