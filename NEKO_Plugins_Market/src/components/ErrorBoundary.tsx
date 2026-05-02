import { Component, type ErrorInfo, type ReactNode } from "react";
import { AlertTriangle, RotateCcw } from "lucide-react";
import { Button } from "@/components/ui/button";
import { reportError } from "@/lib/error-reporting";

interface Props {
  children: ReactNode;
}

interface State {
  hasError: boolean;
  errorId?: string;
}

export class ErrorBoundary extends Component<Props, State> {
  state: State = { hasError: false };

  static getDerivedStateFromError() {
    return { hasError: true };
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    const report = reportError(error, {
      severity: "fatal",
      title: "页面渲染失败",
      userMessage: "当前页面渲染失败，请刷新后重试。",
      context: {
        componentStack: errorInfo.componentStack
      }
    });
    this.setState({ errorId: report.id });
  }

  render() {
    if (!this.state.hasError) {
      return this.props.children;
    }

    return (
      <div className="flex min-h-screen items-center justify-center bg-background px-4">
        <div className="max-w-md rounded-lg border bg-card p-6 text-center shadow-lg">
          <div className="mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-full bg-destructive/10">
            <AlertTriangle className="h-6 w-6 text-destructive" />
          </div>
          <h1 className="text-xl font-semibold">页面出现错误</h1>
          <p className="mt-2 text-sm text-muted-foreground">
            请刷新页面后重试。错误编号：{this.state.errorId ?? "UNKNOWN"}
          </p>
          <Button className="mt-6" onClick={() => window.location.reload()}>
            <RotateCcw className="mr-2 h-4 w-4" />
            刷新页面
          </Button>
        </div>
      </div>
    );
  }
}
