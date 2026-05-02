import { useEffect } from "react";
import { installGlobalErrorHandlers } from "@/lib/error-reporting";

export function AppDiagnostics() {
  useEffect(() => {
    installGlobalErrorHandlers();
  }, []);

  return null;
}
