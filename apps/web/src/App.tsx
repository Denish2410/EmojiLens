import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useState } from "react";
import { Link, Route, Routes } from "react-router";
import { AppShell } from "./components/AppShell";
import { ToastProvider } from "./components/Toast";
import { ThemeProvider } from "./lib/theme";
import { AnnotationStudio } from "./pages/AnnotationStudio";
import { CRSCAnalytics } from "./pages/CRSCAnalytics";
import { DatasetExplorer } from "./pages/DatasetExplorer";
import { ExperimentStudio } from "./pages/ExperimentStudio";
import { EvaluationDashboard } from "./pages/EvaluationDashboard";
import { GuardConsole } from "./pages/GuardConsole";
import { ModelArena } from "./pages/ModelArena";
import { MultimodalLab } from "./pages/MultimodalLab";
import { MultilingualLab } from "./pages/MultilingualLab";
import { Overview } from "./pages/Overview";
import { Settings } from "./pages/Settings";
import { TransformLab } from "./pages/TransformLab";
import { UnicodeInspector } from "./pages/UnicodeInspector";

function NotFound() {
  return (
    <div className="mx-auto max-w-md py-16 text-center">
      <h1 className="text-lg font-semibold">Page not found</h1>
      <Link to="/" className="mt-3 inline-block text-sm text-violet-500 hover:underline">
        Back to overview
      </Link>
    </div>
  );
}

export function AppRoutes() {
  return (
    <Routes>
      <Route element={<AppShell />}>
        <Route index element={<Overview />} />
        <Route path="inspector" element={<UnicodeInspector />} />
        <Route path="transforms" element={<TransformLab />} />
        <Route path="multilingual" element={<MultilingualLab />} />
        <Route path="datasets" element={<DatasetExplorer />} />
        <Route path="annotation" element={<AnnotationStudio />} />
        <Route path="models" element={<ModelArena />} />
        <Route path="experiments" element={<ExperimentStudio />} />
        <Route path="crsc" element={<CRSCAnalytics />} />
        <Route path="multimodal" element={<MultimodalLab />} />
        <Route path="guard" element={<GuardConsole />} />
        <Route path="evaluation" element={<EvaluationDashboard />} />
        <Route path="settings" element={<Settings />} />
        <Route path="datasets/:slug" element={<DatasetExplorer />} />
        <Route path="*" element={<NotFound />} />
      </Route>
    </Routes>
  );
}

export function Providers({ children }: { children: React.ReactNode }) {
  const [client] = useState(
    () => new QueryClient({ defaultOptions: { queries: { refetchOnWindowFocus: false } } }),
  );
  return (
    <QueryClientProvider client={client}>
      <ThemeProvider>
        <ToastProvider>{children}</ToastProvider>
      </ThemeProvider>
    </QueryClientProvider>
  );
}
