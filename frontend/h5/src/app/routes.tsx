import type { RouteObject } from "react-router-dom";
import { DashboardPage } from "../features/dashboard/DashboardPage";
import { FundsPage } from "../features/funds/FundsPage";
import { PlanningPage } from "../features/planning/PlanningPage";
import { AlertsPage } from "../features/alerts/AlertsPage";
import { ReportPage } from "../features/report/ReportPage";

export const routes: RouteObject[] = [
  { path: "/", element: <DashboardPage /> },
  { path: "/funds", element: <FundsPage /> },
  { path: "/planning", element: <PlanningPage /> },
  { path: "/alerts", element: <AlertsPage /> },
  { path: "/me", element: <ReportPage /> },
];
