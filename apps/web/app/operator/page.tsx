import { Suspense } from "react";
import { OperatorScreen } from "@/components/operator/operator-screen";

export default function OperatorPage() {
  return (
    <Suspense fallback={null}>
      <OperatorScreen />
    </Suspense>
  );
}
